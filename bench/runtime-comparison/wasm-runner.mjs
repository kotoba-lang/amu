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
const admitted = await instantiateKotoba(readFileSync(artifact));
if (WebAssembly.Module.imports(admitted.module).length !== 0)
  throw new Error("runtime benchmark fixture unexpectedly requires host imports");
if (calls > 400) throw new Error("calls exceeds the fresh-instance fuel budget of 400");
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
  const batch = Math.min(400, remainingWarmup);
  for (let index = 0; index < batch; index += 1) result = warmKernel(BigInt(n));
  remainingWarmup -= batch;
}
const kernel = await freshKernel();
const started = process.hrtime.bigint();
for (let index = 0; index < calls; index += 1) result = kernel(BigInt(n));
const elapsed = process.hrtime.bigint() - started;
process.stdout.write(`${JSON.stringify({
  format: "kotoba.runtime-sample/v1",
  calls,
  warmupCalls: warmup,
  elapsedNanoseconds: Number(elapsed),
  result: Number(result),
})}\n`);
