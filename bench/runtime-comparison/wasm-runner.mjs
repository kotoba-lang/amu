#!/usr/bin/env node

import { readFileSync } from "node:fs";
import { instantiateKotoba } from "../../runtime/browser-host.mjs";

function positive(value, name) {
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed) || parsed < 1)
    throw new Error(`${name} must be a positive safe integer`);
  return parsed;
}

const [artifact, nText, callsText, warmupText, fuelText, batchText] = process.argv.slice(2);
if (!artifact) {
  throw new Error(
    "usage: wasm-runner.mjs <artifact> <n> <calls> <warmup> <fuel> <max-calls-per-instance>");
}
const n = positive(nText, "n");
const calls = positive(callsText, "calls");
const warmup = positive(warmupText, "warmup");
const fuel = positive(fuelText, "fuel");
const requestedMaxCallsPerInstance = positive(batchText, "max-calls-per-instance");
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
// Fuel is module-private and non-replenishable. Calibrate the largest safe
// batch against a fresh instance before timing; this follows the emitted code
// when its charge model changes instead of encoding a stale calls-per-kernel
// estimate in the harness.
const calibrationLimit = Math.min(requestedMaxCallsPerInstance, Math.max(calls, warmup));
const batchSucceeds = async count => {
  const kernel = await freshKernel();
  try {
    for (let index = 0; index < count; index += 1) kernel(BigInt(n));
    return true;
  } catch (error) {
    if (error instanceof WebAssembly.RuntimeError) return false;
    throw error;
  }
};
if (!(await batchSucceeds(1))) {
  throw new Error(`one Wasm kernel invocation exceeds the sealed fuel ${fuel}`);
}
let safe = 1;
let unsafe = calibrationLimit + 1;
if (calibrationLimit > 1 && await batchSucceeds(calibrationLimit)) {
  safe = calibrationLimit;
} else {
  while (safe + 1 < unsafe) {
    const candidate = safe + Math.floor((unsafe - safe) / 2);
    if (await batchSucceeds(candidate)) safe = candidate;
    else unsafe = candidate;
  }
}
const maxCallsPerInstance = safe;
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
  fuelPerInstance: fuel,
  maxCallsPerInstance,
})}\n`);
