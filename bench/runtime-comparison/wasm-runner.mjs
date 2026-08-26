#!/usr/bin/env node

import { readFileSync } from "node:fs";
import { instantiateKotoba } from "../../runtime/browser-host.mjs";

function positive(value, name) {
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed) || parsed < 1)
    throw new Error(`${name} must be a positive safe integer`);
  return parsed;
}

const [artifact, nText, callsText, warmupText] = process.argv.slice(2);
if (!artifact) throw new Error("usage: wasm-runner.mjs <artifact> <n> <calls> <warmup>");
const n = positive(nText, "n");
const calls = positive(callsText, "calls");
const warmup = positive(warmupText, "warmup");
// Fuel is sealed at 512 per instance. Loop+call kernels can exhaust it well
// before 400 invocations; 64 keeps measurement batches inside the contract.
const maxCallsPerInstance = 64;
const admitted = await instantiateKotoba(readFileSync(artifact));
if (WebAssembly.Module.imports(admitted.module).length !== 0)
  throw new Error("runtime benchmark fixture unexpectedly requires host imports");
if (calls > 1_000_000) throw new Error("calls exceeds the benchmark total limit");
const freshKernel = async () => {
  const instance = await WebAssembly.instantiate(admitted.module, {});
  const kernel = instance.exports.kernel;
  if (typeof kernel !== "function") throw new Error("Wasm artifact omitted kernel export");
  return kernel;
};
let result = 0n;
let remainingWarmup = warmup;
while (remainingWarmup > 0) {
  const warmKernel = await freshKernel();
  const batch = Math.min(maxCallsPerInstance, remainingWarmup);
  for (let index = 0; index < batch; index += 1) result = warmKernel(BigInt(n));
  remainingWarmup -= batch;
}
let elapsed = 0n;
let remainingCalls = calls;
while (remainingCalls > 0) {
  const kernel = await freshKernel();
  const batch = Math.min(maxCallsPerInstance, remainingCalls);
  const started = process.hrtime.bigint();
  for (let index = 0; index < batch; index += 1) result = kernel(BigInt(n));
  elapsed += process.hrtime.bigint() - started;
  remainingCalls -= batch;
}
process.stdout.write(`${JSON.stringify({
  format: "kotoba.runtime-sample/v1",
  calls,
  warmupCalls: warmup,
  elapsedNanoseconds: Number(elapsed),
  result: Number(result),
})}\n`);
