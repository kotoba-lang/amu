#!/usr/bin/env node

import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import {
  chmodSync, closeSync, existsSync, lstatSync, openSync, readFileSync, readdirSync,
  realpathSync, statSync, unlinkSync, writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { basename, dirname, join, relative, resolve } from "node:path";
import { createConnection, createServer } from "node:net";
import { createInterface } from "node:readline";
import { fileURLToPath } from "node:url";

const protocol = "kotoba.compiler-daemon/v1";
const workerProtocol = "kotoba.compiler-worker/v1";
const maxLineBytes = 64 * 1024;
const configuredIdle = Number(process.env.KOTOBA_COMPILER_DAEMON_IDLE_MS || 300_000);
const idleMilliseconds = Number.isSafeInteger(configuredIdle)
  && configuredIdle >= 1000 && configuredIdle <= 3_600_000 ? configuredIdle : 300_000;
const scriptPath = realpathSync(fileURLToPath(import.meta.url));
const scriptRoot = realpathSync(resolve(dirname(scriptPath), ".."));
const targetNames = Object.freeze({ wasm: "wasm32", aarch64: "aarch64", x86_64: "x86_64" });

function filesBelow(path) {
  if (!lstatSync(path).isDirectory()) return [path];
  return readdirSync(path, { withFileTypes: true }).flatMap((entry) => {
    const child = join(path, entry.name);
    return entry.isDirectory() ? filesBelow(child) : [child];
  });
}

function compilerSnapshot(root, previous = new Map()) {
  const roots = ["deps.edn", "deps-lock.edn", "package-lock.json", "src", "resources"]
    .map((path) => join(root, path));
  const files = roots.flatMap(filesBelow).sort((left, right) => {
    const a = relative(root, left);
    const b = relative(root, right);
    return a < b ? -1 : a > b ? 1 : 0;
  });
  const entries = new Map();
  const tree = createHash("sha256");
  for (const path of files) {
    const name = relative(root, path);
    const stat = statSync(path, { bigint: true });
    const signature = `${stat.dev}:${stat.ino}:${stat.size}:${stat.mtimeNs}:${stat.ctimeNs}:${stat.mode}`;
    const prior = previous.get(name);
    const digest = prior?.signature === signature ? prior.digest
      : createHash("sha256").update(readFileSync(path)).digest("hex");
    entries.set(name, { signature, digest });
    tree.update(name).update("\0").update(digest).update("\0");
  }
  return { entries, digest: tree.digest("hex") };
}

function instanceFor(root) {
  const namespace = process.env.KOTOBA_COMPILER_DAEMON_NAMESPACE || "";
  if (!/^[A-Za-z0-9_-]{0,32}$/.test(namespace)) throw new Error("invalid compiler daemon namespace");
  return createHash("sha256")
    .update(protocol).update("\0")
    .update(root).update("\0").update(namespace).update("\0")
    .update(readFileSync(scriptPath)).update("\0")
    .update(readFileSync(join(root, "bin", "kotoba")))
    .digest("hex").slice(0, 24);
}

function endpointFor(instance) {
  if (process.platform === "win32") return `\\\\.\\pipe\\kotoba-compiler-${instance}`;
  const uid = typeof process.getuid === "function" ? process.getuid() : "user";
  return join(tmpdir(), `kotoba-compiler-${uid}-${instance}.sock`);
}

function validateRoot(value) {
  const root = realpathSync(resolve(value));
  if (root !== scriptRoot) throw new Error("compiler daemon root does not match its implementation");
  return root;
}

function boundedArgs(args) {
  return Array.isArray(args) && args.length <= 64
    && args.every((arg) => typeof arg === "string" && arg.length <= 4096);
}

function withTimeout(promise, milliseconds, message) {
  let timer;
  return Promise.race([
    promise,
    new Promise((_, reject) => { timer = setTimeout(() => reject(new Error(message)), milliseconds); }),
  ]).finally(() => clearTimeout(timer));
}

class CompilerWorker {
  constructor(root, target) {
    this.root = root;
    this.target = target;
    this.child = null;
    this.iterator = null;
    this.lines = null;
    this.sequence = 0;
    this.tail = Promise.resolve();
  }

  async start() {
    if (this.child && this.child.exitCode === null) return;
    const child = spawn(join(this.root, "bin", "kotoba"),
      ["-M", "worker", "--target", targetNames[this.target]], {
        cwd: this.root,
        stdio: ["pipe", "pipe", "ignore"],
        env: { ...process.env, KOTOBA_COMPILER_DAEMON: "0", KOTOBA_COMPILER_TIMING: "1" },
      });
    this.child = child;
    this.lines = createInterface({ input: child.stdout, crlfDelay: Infinity });
    this.iterator = this.lines[Symbol.asyncIterator]();
    const ready = await withTimeout(this.next(), 120_000, "compiler worker startup timeout");
    if (ready.format !== workerProtocol || ready.type !== "ready") {
      this.stop();
      throw new Error("compiler worker ready contract mismatch");
    }
  }

  async next() {
    const value = await this.iterator.next();
    if (value.done) throw new Error("compiler worker exited before responding");
    if (Buffer.byteLength(value.value, "utf8") > maxLineBytes) throw new Error("compiler worker response too large");
    return JSON.parse(value.value);
  }

  request(args) {
    const execute = async () => {
      await this.start();
      const id = ++this.sequence;
      this.child.stdin.write(`${JSON.stringify({ id, args })}\n`);
      const response = await withTimeout(this.next(), 120_000, "compiler worker request timeout");
      if (response.format !== workerProtocol || response.type !== "result" || response.id !== id
          || !Number.isInteger(response.status) || typeof response.stdout !== "string"
          || typeof response.stderr !== "string") {
        this.stop();
        throw new Error("compiler worker result contract mismatch");
      }
      if (response.status === 70) this.stop();
      return response;
    };
    const result = this.tail.then(execute, execute);
    this.tail = result.catch(() => {});
    return result;
  }

  stop() {
    if (this.lines) this.lines.close();
    if (this.child && this.child.exitCode === null) this.child.kill();
    this.child = null;
    this.lines = null;
    this.iterator = null;
  }
}

function ownedSocket(path) {
  const stat = lstatSync(path);
  const owned = typeof process.getuid !== "function" || stat.uid === process.getuid();
  return stat.isSocket() && owned;
}

function acquireLock(path) {
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const fd = openSync(path, "wx", 0o600);
      writeFileSync(fd, `${process.pid}\n`);
      closeSync(fd);
      return;
    } catch (error) {
      if (error.code !== "EEXIST") throw error;
      const stat = lstatSync(path);
      if (!stat.isFile() || (typeof process.getuid === "function" && stat.uid !== process.getuid())) throw error;
      const pid = Number(readFileSync(path, "utf8").trim());
      try {
        if (Number.isSafeInteger(pid) && pid > 1) process.kill(pid, 0);
        throw error;
      } catch (probe) {
        if (probe === error || probe.code !== "ESRCH") throw probe;
        unlinkSync(path);
      }
    }
  }
  throw new Error("unable to acquire compiler daemon lock");
}

async function serve(root) {
  const instance = instanceFor(root);
  const endpoint = endpointFor(instance);
  const lock = process.platform === "win32" ? null : `${endpoint}.lock`;
  if (lock) acquireLock(lock);
  if (process.platform !== "win32" && existsSync(endpoint)) {
    if (!ownedSocket(endpoint)) throw new Error("refusing to replace unowned compiler socket");
    unlinkSync(endpoint);
  }

  const workers = new Map();
  const source = compilerSnapshot(root);
  let active = 0;
  let idleTimer;
  const resetIdle = () => {
    clearTimeout(idleTimer);
    if (Number.isFinite(idleMilliseconds) && idleMilliseconds >= 1000) {
      idleTimer = setTimeout(() => {
        if (active === 0) server.close();
      }, idleMilliseconds);
      idleTimer.unref();
    }
  };
  const server = createServer((socket) => {
    active += 1;
    clearTimeout(idleTimer);
    let pending = Buffer.alloc(0);
    let handled = false;
    const fail = () => socket.destroy();
    socket.on("data", async (chunk) => {
      if (handled) return fail();
      pending = Buffer.concat([pending, chunk]);
      if (pending.length > maxLineBytes) return fail();
      const newline = pending.indexOf(10);
      if (newline < 0) return;
      if (pending.length !== newline + 1) return fail();
      handled = true;
      try {
        const request = JSON.parse(pending.subarray(0, newline).toString("utf8"));
        if (request.format !== protocol || request.op !== "compile"
            || !Object.hasOwn(targetNames, request.target) || !boundedArgs(request.args)) throw new Error();
        if (compilerSnapshot(root, source.entries).digest !== source.digest) {
          server.close();
          throw new Error();
        }
        let worker = workers.get(request.target);
        if (!worker) {
          worker = new CompilerWorker(root, request.target);
          workers.set(request.target, worker);
        }
        const response = await worker.request(request.args);
        socket.end(`${JSON.stringify(response)}\n`);
      } catch {
        fail();
      }
    });
    socket.on("error", () => {});
    socket.on("close", () => {
      active -= 1;
      resetIdle();
    });
  });
  server.on("close", () => {
    clearTimeout(idleTimer);
    for (const worker of workers.values()) worker.stop();
    if (process.platform !== "win32" && existsSync(endpoint) && ownedSocket(endpoint)) unlinkSync(endpoint);
    if (lock && existsSync(lock)) unlinkSync(lock);
  });
  server.on("error", () => process.exit(1));
  server.listen(endpoint, () => {
    if (process.platform !== "win32") chmodSync(endpoint, 0o600);
    resetIdle();
  });
}

function connect(endpoint, request) {
  return new Promise((resolveRequest, reject) => {
    const socket = createConnection(endpoint);
    let pending = Buffer.alloc(0);
    socket.on("connect", () => socket.write(`${JSON.stringify(request)}\n`));
    socket.on("data", (chunk) => {
      pending = Buffer.concat([pending, chunk]);
      if (pending.length > maxLineBytes) socket.destroy(new Error("compiler daemon response too large"));
    });
    socket.on("error", reject);
    socket.on("end", () => {
      try {
        const line = pending.toString("utf8");
        if (!line.endsWith("\n") || line.indexOf("\n") !== line.length - 1) throw new Error();
        const response = JSON.parse(line.slice(0, -1));
        if (response.format !== workerProtocol || response.type !== "result"
            || !Number.isInteger(response.status) || typeof response.stdout !== "string"
            || typeof response.stderr !== "string") throw new Error();
        resolveRequest(response);
      } catch {
        reject(new Error("compiler daemon response contract mismatch"));
      }
    });
  });
}

async function request(root, target, args) {
  if (!Object.hasOwn(targetNames, target) || !boundedArgs(args)) throw new Error("invalid daemon request");
  const instance = instanceFor(root);
  const endpoint = endpointFor(instance);
  const payload = { format: protocol, op: "compile", target, args };
  try {
    return await withTimeout(connect(endpoint, payload), 120_000, "compiler daemon request timeout");
  } catch {
    const daemon = spawn(process.execPath, [scriptPath, "serve", root], {
      cwd: root, detached: true, stdio: "ignore", env: process.env,
    });
    daemon.unref();
    let last;
    for (let attempt = 0; attempt < 200; attempt += 1) {
      await new Promise((resolveWait) => setTimeout(resolveWait, 25));
      try {
        return await withTimeout(connect(endpoint, payload), 120_000, "compiler daemon request timeout");
      } catch (error) {
        last = error;
      }
    }
    throw last || new Error("compiler daemon did not start");
  }
}

const [mode, rootArgument, target, ...args] = process.argv.slice(2);
try {
  const root = validateRoot(rootArgument);
  if (mode === "serve") {
    await serve(root);
  } else if (mode === "request") {
    const response = await request(root, target, args);
    process.stdout.write(`${JSON.stringify(response)}\n`);
  } else {
    throw new Error(`usage: ${basename(scriptPath)} request|serve <root> [target args...]`);
  }
} catch (error) {
  if (process.env.KOTOBA_COMPILER_DAEMON_TRACE === "1")
    process.stderr.write(`kotoba: compiler daemon unavailable (${error.message})\n`);
  process.exitCode = 75;
}
