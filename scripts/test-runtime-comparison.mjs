#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const oddIterations = spawnSync(process.execPath,
  ["scripts/runtime-comparison.mjs", "--runs", "1", "--iterations", "999"],
  { cwd: root, encoding: "utf8", timeout: 10_000 });
if (oddIterations.status === 0
    || !`${oddIterations.stdout}${oddIterations.stderr}`.includes("must be even")) {
  throw new Error("runtime comparison accepted an unbalanced branch iteration count");
}
const partialNativeCandidate = spawnSync(process.execPath,
  ["scripts/runtime-comparison.mjs", "--runs", "1", "--iterations", "2",
    "--native-kir-root", root],
  { cwd: root, encoding: "utf8", timeout: 10_000 });
if (partialNativeCandidate.status === 0
    || !`${partialNativeCandidate.stdout}${partialNativeCandidate.stderr}`
      .includes("requires --native-kir-root, --native-verifier-root, and --native-backend-root together")) {
  throw new Error("runtime comparison accepted a partial native candidate override");
}
const result = spawnSync(process.execPath,
  ["scripts/runtime-comparison.mjs", "--runs", "1", "--iterations", "1000"],
  { cwd: root, encoding: "utf8", timeout: 300_000, maxBuffer: 16 * 1024 * 1024 });
if (result.error) throw result.error;
if (result.status !== 0) {
  throw new Error(`runtime comparison failed (${result.status})\n${result.stdout}${result.stderr}`);
}
const report = JSON.parse(result.stdout);
if (report.format !== "kotoba.runtime-comparison/v7" || report.workloads.length !== 5) {
  throw new Error("runtime comparison schema or lane matrix mismatch");
}
const requiredLanes = ["kotoba-wasm-v8", "kotoba-wasm-wasmtime",
  "kotoba-native-supervised", "clojure-hotspot", "clojure-hotspot-boxed",
  "clojurescript-v8-advanced", "rust-native-release"];
const expectedWorkloads = new Set(["scalar-multiply", "balanced-branch", "integer-mix",
  "vector-allocate-scan", "vector-materialize-scan"]);
if (report.benchmark !== "runtime-workload-matrix"
    || report.environment.wasmBackend.source !== "compiler-dependency-pin"
    || report.environment.nativeBackend.source !== "compiler-dependency-pins"
    || !report.methodology.nativeSafety.includes("W^X")) {
  throw new Error("runtime comparison omitted its semantic or safety contract");
}
for (const workload of report.workloads) {
  if (!expectedWorkloads.delete(workload.benchmark)) {
    throw new Error(`unexpected workload ${workload.benchmark}`);
  }
  if (typeof workload.semantics.checksumRule !== "string"
      || !Number.isSafeInteger(workload.semantics.coldChecksum)
      || !Number.isSafeInteger(workload.semantics.steadyChecksum)
      || workload.semantics.steadyIterations
          !== (workload.benchmark.startsWith("vector-") ? 256 : 1000)
      || (workload.benchmark === "balanced-branch"
          && workload.semantics.coldIterations !== 2)) {
    throw new Error(`${workload.benchmark} semantic contract mismatch`);
  }
  const expectedLanes = new Set(requiredLanes);
  for (const lane of workload.results) {
    if (!expectedLanes.delete(lane.lane)) throw new Error(`unexpected lane ${lane.lane}`);
    if (workload.benchmark === "vector-materialize-scan"
        && lane.lane === "kotoba-native-supervised") {
      if (lane.support?.measured !== false
          || !lane.support.reason.includes("function boundaries")) {
        throw new Error("native vector function-boundary gap was not reported explicitly");
      }
      continue;
    }
    if (workload.benchmark.startsWith("vector-")
        && lane.lane === "kotoba-wasm-wasmtime") {
      if (lane.support?.measured !== false
          || !lane.support.reason.includes("typed externref host")) {
        throw new Error("vector Wasmtime support gap was not reported explicitly");
      }
      continue;
    }
    if (!(lane.coldProcessWallMilliseconds.median > 0)
        || !(lane.coldProcessRatioToRust > 0)
        || !(lane.peakResidentSetBytes > 0)) {
      throw new Error(`invalid cold measurement for ${workload.benchmark}/${lane.lane}`);
    }
    if (lane.lane === "kotoba-wasm-wasmtime") {
      if (lane.steadyState.measured !== false
          || !(lane.artifactBytes > 0)) {
        throw new Error(`${lane.lane} unmeasured steady-state contract mismatch`);
      }
    } else if (lane.lane === "kotoba-native-supervised") {
      if (!(lane.loaderBytes > 0) || !(lane.artifactBytes > 0)
          || !(lane.steadyNanosecondsPerIteration.median > 0)
          || !(lane.steadyRatioToRust > 0)
          || lane.supervisedSteady.invocationIterations > 256
          || lane.supervisedSteady.measuredInvocations !== 100
          || lane.supervisedSteady.warmupInvocations !== 10
          || lane.supervisedSteady.excludesProcessStartup !== true
          || !(lane.supervisedBatchIterations > 0)
          || lane.supervisedBatchIterations > 256
          || !(lane.supervisedBatchWallMilliseconds.median > 0)
          || !(lane.supervisedBatchNanosecondsPerIterationIncludingStartup.median > 0)) {
        throw new Error("native supervised batch evidence is missing");
      }
    } else if (!(lane.steadyNanosecondsPerIteration.median > 0)
               || !(lane.steadyRatioToRust > 0)) {
      throw new Error(`invalid steady measurement for ${workload.benchmark}/${lane.lane}`);
    }
  }
  if (expectedLanes.size !== 0) throw new Error(`${workload.benchmark} omitted a required lane`);
}
if (expectedWorkloads.size !== 0) throw new Error("runtime comparison omitted a required workload");
console.log("runtime-comparison: five-workload, seven-lane support/checksum/timing/RSS matrix passed");
