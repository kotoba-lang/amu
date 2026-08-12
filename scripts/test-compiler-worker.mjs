#!/usr/bin/env node

import { spawn } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { createInterface } from "node:readline";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const directory = mkdtempSync(join(tmpdir(), "kotoba-worker-test-"));
const worker = spawn(join(root, "bin", "kotoba"), ["-M", "worker", "--target", "wasm32"], {
  cwd: root,
  stdio: ["pipe", "pipe", "pipe"],
  env: { ...process.env, KOTOBA_COMPILER_TIMING: "1", KOTOBA_WORKER_MAX_REQUESTS: "10" },
});
const lines = createInterface({ input: worker.stdout, crlfDelay: Infinity });
const iterator = lines[Symbol.asyncIterator]();
let stderr = "";
worker.stderr.on("data", (chunk) => { stderr += chunk.toString(); });

async function next() {
  let timeoutId;
  try {
    const result = await Promise.race([
      iterator.next(),
      new Promise((_, reject) => {
        timeoutId = setTimeout(() => reject(new Error(`worker timeout\n${stderr}`)), 120_000);
      }),
    ]);
    if (result.done) throw new Error(`worker exited early\n${stderr}`);
    return JSON.parse(result.value);
  } finally {
    clearTimeout(timeoutId);
  }
}

function send(value) {
  worker.stdin.write(typeof value === "string" ? `${value}\n` : `${JSON.stringify(value)}\n`);
}

try {
  const ready = await next();
  if (ready.type !== "ready" || ready.target !== "wasm32-kotoba-v1") {
    throw new Error("worker ready contract mismatch");
  }

  send("{malformed");
  const malformed = await next();
  if (malformed.status !== 64 || malformed.id !== null) {
    throw new Error("malformed request did not fail closed");
  }

  send({ id: "wrong-target",
    args: ["compile", "examples/i64-semantics.kotoba", "--target", "aarch64",
      "--output", join(directory, "wrong.kexe")] });
  const wrongTarget = await next();
  if (wrongTarget.status !== 64 || !wrongTarget.stderr.includes("does not cover target")) {
    throw new Error("worker accepted a target outside its locked backend");
  }

  send({ id: "valid",
    args: ["compile", "examples/i64-semantics.kotoba", "--target", "wasm32",
      "--output", join(directory, "valid.wasm")] });
  const valid = await next();
  if (valid.status !== 0 || valid.type !== "result"
      || !valid.stdout.includes(":wasm32-kotoba-v1")
      || !valid.stdout.includes(":cache :miss")
      || !valid.timing?.phases?.some(({ phase }) => phase === "command")) {
    throw new Error(`valid worker request failed: ${valid.stderr}`);
  }

  send({ id: "cached",
    args: ["compile", "examples/i64-semantics.kotoba", "--target", "wasm32",
      "--output", join(directory, "cached.wasm")] });
  const cached = await next();
  if (cached.status !== 0 || !cached.stdout.includes(":cache :hit")
      || !readFileSync(join(directory, "valid.wasm"))
        .equals(readFileSync(join(directory, "cached.wasm")))) {
    throw new Error("content-addressed cache hit changed Wasm bytes");
  }

  const editedSource = join(directory, "i64-semantics-whitespace.kotoba");
  writeFileSync(editedSource,
    `${readFileSync(join(root, "examples/i64-semantics.kotoba"), "utf8")}\n`);
  send({ id: "semantic-edit",
    args: ["compile", editedSource, "--target", "wasm32",
      "--output", join(directory, "semantic-edit.wasm")] });
  const semanticEdit = await next();
  if (semanticEdit.status !== 0 || !semanticEdit.stdout.includes(":cache :miss")
      || !semanticEdit.stdout.includes(":stage-cache {:hir :miss, :kir :hit}")
      || !readFileSync(join(directory, "valid.wasm"))
        .equals(readFileSync(join(directory, "semantic-edit.wasm")))) {
    throw new Error("frontend-equivalent source edit did not reuse verified KIR");
  }

  const policy = join(directory, "policy.edn");
  writeFileSync(policy, "{}\n");
  send({ id: "policy-miss",
    args: ["compile", "examples/i64-semantics.kotoba", "--target", "wasm32",
      "--policy", policy, "--output", join(directory, "policy-miss.wasm")] });
  const policyMiss = await next();
  if (policyMiss.status !== 0 || !policyMiss.stdout.includes(":cache :miss")
      || !policyMiss.stdout.includes(":stage-cache {:hir :hit, :kir :hit}")) {
    throw new Error("policy change did not reuse policy-independent HIR/KIR stages");
  }

  send({ id: "policy-hit",
    args: ["compile", "examples/i64-semantics.kotoba", "--target", "wasm32",
      "--policy", policy, "--output", join(directory, "policy-hit.wasm")] });
  const policyHit = await next();
  if (policyHit.status !== 0 || !policyHit.stdout.includes(":cache :hit")) {
    throw new Error("identical explicit policy did not hit the cache");
  }

  send({ id: "capability-allowed",
    args: ["compile", "examples/capability.kotoba", "--target", "wasm32",
      "--policy", "examples/capability-policy.edn",
      "--output", join(directory, "capability-allowed.wasm")] });
  const capabilityAllowed = await next();
  if (capabilityAllowed.status !== 0 || !capabilityAllowed.stdout.includes(":cache :miss")) {
    throw new Error(`allowed capability fixture failed: ${capabilityAllowed.stderr}`);
  }

  send({ id: "capability-denied",
    args: ["compile", "examples/capability.kotoba", "--target", "wasm32",
      "--policy", policy, "--output", join(directory, "capability-denied.wasm")] });
  const capabilityDenied = await next();
  if (capabilityDenied.status === 0 || capabilityDenied.status !== 65
      || !capabilityDenied.stderr.includes("denies required effects")) {
    throw new Error(`stage cache bypassed admission after a policy change: ${JSON.stringify(capabilityDenied)}`);
  }

  send({ id: "shutdown", op: "shutdown", args: [] });
  const shutdown = await next();
  if (shutdown.type !== "shutdown" || shutdown.status !== 0) {
    throw new Error("worker shutdown contract mismatch");
  }
  console.log("compiler-worker: protocol, target lock, staged cache, admission, recovery, and shutdown passed");
} finally {
  lines.close();
  worker.stdin.end();
  if (worker.exitCode === null) worker.kill();
  rmSync(directory, { recursive: true, force: true });
}

// A line without a newline must be rejected while bytes are still arriving;
// otherwise a nominal post-read limit would permit unbounded buffering.
const oversizedWorker = spawn(join(root, "bin", "kotoba"),
  ["-M", "worker", "--target", "wasm32"],
  { cwd: root, stdio: ["pipe", "pipe", "pipe"] });
const oversizedLines = createInterface({ input: oversizedWorker.stdout, crlfDelay: Infinity });
const oversizedIterator = oversizedLines[Symbol.asyncIterator]();
try {
  const ready = await oversizedIterator.next();
  if (ready.done || JSON.parse(ready.value).type !== "ready") {
    throw new Error("oversized-line worker did not become ready");
  }
  oversizedWorker.stdin.write("x".repeat(65_537));
  const response = await oversizedIterator.next();
  if (response.done) throw new Error("oversized-line worker exited without a rejection");
  const rejection = JSON.parse(response.value);
  if (rejection.status !== 64 || !rejection.stderr.includes("exceeds byte limit")) {
    throw new Error("worker buffered an oversized unterminated request");
  }
} finally {
  oversizedLines.close();
  oversizedWorker.stdin.end();
  if (oversizedWorker.exitCode === null) oversizedWorker.kill();
}

console.log("compiler-worker: streaming byte limit passed");
