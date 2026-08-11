#!/usr/bin/env node

import { spawn, spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  mkdtempSync, readFileSync, realpathSync, rmSync, statSync, writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = realpathSync(resolve(dirname(fileURLToPath(import.meta.url)), ".."));
const kotoba = join(root, "bin", "kotoba");
const daemon = join(root, "scripts", "compiler-daemon.mjs");
const directory = mkdtempSync(join(tmpdir(), "kotoba-daemon-test-"));
const marker = join(root, "src", `.compiler-daemon-integrity-${process.pid}`);
const fixture = join(root, "bench", "runtime-comparison", "kernel.kotoba");
const baseEnv = { ...process.env, KOTOBA_COMPILER_DAEMON_TRACE: "1",
  KOTOBA_COMPILER_DAEMON_IDLE_MS: "30000",
  KOTOBA_COMPILER_DAEMON_NAMESPACE: `test-${process.pid}` };

function run(output, env = {}, source = fixture) {
  const started = process.hrtime.bigint();
  const result = spawnSync(process.execPath,
    [kotoba, "-M", "compile", source, "--target", "aarch64", "--output", output], {
      cwd: root, encoding: "utf8", timeout: 120_000,
      env: { ...baseEnv, ...env }, maxBuffer: 16 * 1024 * 1024,
    });
  return { ...result, milliseconds: Number(process.hrtime.bigint() - started) / 1e6 };
}

function ensureSuccess(result, label) {
  if (result.error || result.status !== 0)
    throw new Error(`${label} failed\n${result.stdout}${result.stderr}`);
  if (!result.stderr.includes("compiler daemon hit aarch64"))
    throw new Error(`${label} did not use the daemon`);
}

function concurrent(output) {
  return new Promise((resolveRun, reject) => {
    const processChild = spawn(process.execPath,
      [kotoba, "-M", "compile", fixture, "--target", "aarch64", "--output", output], {
        cwd: root, env: baseEnv, stdio: ["ignore", "pipe", "pipe"],
      });
    let stdout = "";
    let stderr = "";
    processChild.stdout.on("data", (chunk) => { stdout += chunk; });
    processChild.stderr.on("data", (chunk) => { stderr += chunk; });
    processChild.on("error", reject);
    processChild.on("close", (status) => resolveRun({ status, stdout, stderr }));
  });
}

function daemonEndpoint() {
  const protocol = "kotoba.compiler-daemon/v1";
  const instance = createHash("sha256").update(protocol).update("\0").update(root).update("\0")
    .update(baseEnv.KOTOBA_COMPILER_DAEMON_NAMESPACE).update("\0")
    .update(readFileSync(daemon)).update("\0").update(readFileSync(kotoba))
    .digest("hex").slice(0, 24);
  const uid = typeof process.getuid === "function" ? process.getuid() : "user";
  return join(tmpdir(), `kotoba-compiler-${uid}-${instance}.sock`);
}

try {
  const cold = run(join(directory, "cold.kexe"));
  ensureSuccess(cold, "cold daemon compile");
  if (!cold.stdout.includes(":cache :miss")) throw new Error("cold daemon compile was not a cache miss");

  const warm = run(join(directory, "warm.kexe"));
  ensureSuccess(warm, "warm daemon compile");
  if (!warm.stdout.includes(":cache :hit")) throw new Error("warm daemon compile was not a cache hit");
  if (!readFileSync(join(directory, "cold.kexe")).equals(readFileSync(join(directory, "warm.kexe"))))
    throw new Error("daemon cache hit changed artifact bytes");

  if (process.platform !== "win32" && (statSync(daemonEndpoint()).mode & 0o777) !== 0o600)
    throw new Error("compiler daemon socket is not owner-only");

  const oneShot = run(join(directory, "one-shot.kexe"), { KOTOBA_COMPILER_DAEMON: "0" });
  if (oneShot.error || oneShot.status !== 0
      || !readFileSync(join(directory, "warm.kexe")).equals(readFileSync(join(directory, "one-shot.kexe"))))
    throw new Error(`one-shot fallback changed artifact bytes\n${oneShot.stderr}`);

  const invalid = run(join(directory, "invalid.kexe"), {}, join(directory, "missing.kotoba"));
  if (invalid.status === 0 || !invalid.stderr.includes("compiler daemon hit aarch64"))
    throw new Error("compiler error was mistaken for a daemon transport failure");

  const parallel = await Promise.all([
    concurrent(join(directory, "parallel-a.kexe")),
    concurrent(join(directory, "parallel-b.kexe")),
  ]);
  if (parallel.some((result) => result.status !== 0
      || !result.stderr.includes("compiler daemon hit aarch64")))
    throw new Error(`concurrent daemon compile failed: ${JSON.stringify(parallel)}`);

  writeFileSync(marker, "integrity generation one\n");
  const changed = run(join(directory, "changed.kexe"));
  ensureSuccess(changed, "source-integrity rollover");
  if (!readFileSync(join(directory, "warm.kexe")).equals(readFileSync(join(directory, "changed.kexe"))))
    throw new Error("source-integrity rollover changed artifact bytes");

  process.stdout.write(`compiler-daemon: cold ${cold.milliseconds.toFixed(1)} ms, warm ${warm.milliseconds.toFixed(1)} ms; `
    + "cache, parity, owner-only socket, concurrency, errors, and source rollover passed\n");
} finally {
  rmSync(marker, { force: true });
  rmSync(directory, { recursive: true, force: true });
}
