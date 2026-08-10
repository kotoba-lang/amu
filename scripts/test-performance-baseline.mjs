#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const result = spawnSync(process.execPath,
  ["scripts/performance-baseline.mjs", "--runs", "1"],
  { cwd: root, encoding: "utf8", timeout: 120_000, maxBuffer: 16 * 1024 * 1024 });

if (result.error) throw result.error;
if (result.status !== 0) {
  throw new Error(`performance harness failed (${result.status})\n${result.stdout}${result.stderr}`);
}

const report = JSON.parse(result.stdout);
if (report.format !== "kotoba.performance-baseline/v1") {
  throw new Error(`unexpected report format ${report.format}`);
}
if (report.benchmark !== "process-cold-compile" || report.targets.length !== 2) {
  throw new Error("performance report does not contain the Wasm/native compile matrix");
}
if (report.persistentWorkers.length !== 2) {
  throw new Error("performance report does not contain the Wasm/native worker matrix");
}
if (typeof report.environment.compilerDirty !== "boolean") {
  throw new Error("performance report does not disclose compiler dirty state");
}

for (const target of report.targets) {
  if (target.runs !== 1 || target.samples.length !== 1 || target.artifactBytes <= 0) {
    throw new Error(`invalid sample metadata for ${target.target}`);
  }
  const sample = target.samples[0];
  if (!(sample.wallMilliseconds >= sample.compilerMilliseconds)
      || sample.compilerMilliseconds <= 0
      || sample.entrypointMilliseconds < sample.compilerMilliseconds
      || sample.startupMilliseconds < 0) {
    throw new Error(`invalid timing decomposition for ${target.target}`);
  }
  const phases = new Set(sample.phases.map(({ phase }) => phase));
  for (const required of ["source-read", "frontend", "admission", "kir-lower", "command"]) {
    if (!phases.has(required)) throw new Error(`${target.target} omitted phase ${required}`);
  }
  const emission = target.target === "wasm32" ? "wasm-emit" : "native-emit";
  if (!phases.has(emission)) throw new Error(`${target.target} omitted phase ${emission}`);
}

for (const worker of report.persistentWorkers) {
  if (worker.runs !== 1 || worker.samples.length !== 1
      || worker.startupMilliseconds <= 0 || worker.artifactBytes <= 0
      || worker.warmRoundTrip.medianMilliseconds <= 0
      || worker.loadedCompiler.medianMilliseconds <= 0
      || worker.policyChangeIncremental.roundTripMilliseconds <= 0
      || worker.policyChangeIncremental.compilerMilliseconds <= 0
      || worker.policyChangeIncremental.stageCache.hir !== "hit"
      || worker.policyChangeIncremental.stageCache.kir !== "hit"
      || worker.semanticEditIncremental.roundTripMilliseconds <= 0
      || worker.semanticEditIncremental.compilerMilliseconds <= 0
      || worker.semanticEditIncremental.stageCache.hir !== "miss"
      || worker.semanticEditIncremental.stageCache.kir !== "hit") {
    throw new Error(`invalid persistent-worker measurement for ${worker.target}`);
  }
}

console.log("performance-baseline: valid Wasm/native process-cold report");
