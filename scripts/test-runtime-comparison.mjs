#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const directory = mkdtempSync(join(tmpdir(), "amu-runtime-comparison-test-"));
const calls = 1_000;
const warmupCalls = 50;

function runComparison(outputPath, extraArgs) {
  const run = spawnSync(process.execPath,
    [join(root, "scripts", "runtime-comparison.mjs"),
      "--runs", "1", "--calls", String(calls),
      "--warmup", String(warmupCalls), "--n", "5",
      "--output", outputPath, ...extraArgs],
    { cwd: root, encoding: "utf8", timeout: 600_000, maxBuffer: 32 * 1024 * 1024 });
  if (run.error) throw run.error;
  if (run.status !== 0) throw new Error(`runtime comparison failed\n${run.stdout}${run.stderr}`);
  return JSON.parse(readFileSync(outputPath, "utf8"));
}

function validateReport(report, { required, optional, expectedResult }) {
  if (report.format !== "kotoba.runtime-comparison/v1") throw new Error("wrong report format");
  if (report.contract.expectedResult !== expectedResult) throw new Error("wrong kernel result");
  if (!report.contract.nativeBoundary.includes("no production supervisor"))
    throw new Error("native benchmark boundary is not explicit");
  if (report.contract.fuelPerInstance !== 1_048_576)
    throw new Error("benchmark fuel contract is missing");
  if (!Number.isSafeInteger(report.contract.wasmMaxCallsPerInstance)
      || report.contract.wasmMaxCallsPerInstance < 1)
    throw new Error("Wasm batch contract is invalid");
  const measured = Object.keys(report.engines);
  for (const name of required)
    if (!measured.includes(name)) throw new Error(`required engine ${name} is missing`);
  const skipped = report.skippedEngines ?? {};
  for (const name of optional) {
    const isMeasured = measured.includes(name);
    const isSkipped = typeof skipped[name] === "string" && skipped[name].length > 0;
    if (isMeasured === isSkipped)
      throw new Error(`optional engine ${name} must be measured or skipped with a reason`);
  }
  for (const name of measured)
    if (!required.includes(name) && !optional.includes(name))
      throw new Error(`unknown engine ${name} in report`);
  for (const name of measured) {
    const engine = report.engines[name];
    if (engine.runs !== 1 || engine.samples.length !== 1)
      throw new Error(`${name} did not produce one real sample`);
    if (engine.samples[0].calls !== calls
        || engine.samples[0].warmupCalls !== warmupCalls)
      throw new Error(`${name} did not report the requested call counts`);
    if (!(engine.steadyStateNanosecondsPerKernel.median > 0)
        || !(engine.processWallMilliseconds.median > 0)
        || !(engine.slowdownVsRust > 0))
      throw new Error(`${name} emitted an invalid timing`);
    if (engine.maxRssBytes === null || !(engine.maxRssBytes.median > 0))
      throw new Error(`${name} omitted measured RSS`);
  }
  for (const [name, artifact] of Object.entries(report.artifacts)) {
    if (artifact === null) continue;
    if (!Number.isSafeInteger(artifact.bytes) || artifact.bytes < 1)
      throw new Error(`artifact size evidence is invalid for ${name}`);
  }
  return { measured, skipped };
}

try {
  const assemblyPath = join(directory, "kernel-loop-call.s");
  const assemblyBuild = spawnSync("rustc",
    ["--edition", "2021", "-C", "opt-level=3", "-C", "codegen-units=1",
      "--emit", "asm", join(root, "bench", "runtime-comparison", "kernel_loop_call.rs"),
      "-o", assemblyPath],
    { cwd: root, encoding: "utf8", timeout: 120_000 });
  if (assemblyBuild.error) throw assemblyBuild.error;
  if (assemblyBuild.status !== 0)
    throw new Error(`Rust loop-call assembly build failed\n${assemblyBuild.stderr}`);
  const assembly = readFileSync(assemblyPath, "utf8");
  if (!/(?:callq?|bl)\s+_?kotoba_bench_id\b/.test(assembly))
    throw new Error("Rust optimized away the loop-call comparison call");

  const kernelReport = runComparison(join(directory, "report.json"), []);
  const kernel = validateReport(kernelReport, {
    required: ["rust", "clojure", "clojurescript", "amu-wasm32", "amu-native"],
    optional: ["go", "mojo", "python", "typescript-node", "typescript-deno"],
    expectedResult: 516860764,
  });
  const loopReport = runComparison(join(directory, "loop-call.json"),
    ["--fixture", "kernel_loop_call", "--n", "200"]);
  if (loopReport.fixture !== "kernel_loop_call") throw new Error("loop-call fixture not recorded");
  if (loopReport.benchmark !== "loop-call-mix-v1") throw new Error("loop-call benchmark id missing");
  const loop = validateReport(loopReport, {
    required: ["rust", "amu-wasm32", "amu-native"],
    optional: [],
    expectedResult: 200,
  });
  if (loopReport.contract.wasmMaxCallsPerInstance !== calls)
    throw new Error("Wasm --fuel did not reach the emitted loop-call artifact");
  if (loopReport.engines["amu-wasm32"].samples[0].fuelPerInstance !== 1_048_576)
    throw new Error("Wasm sample omitted its sealed benchmark fuel");
  if (loopReport.engines["amu-native"].samples[0].fuelPerCall !== 1_048_576)
    throw new Error("native sample omitted its reset benchmark fuel");
  process.stdout.write(
    `runtime-comparison: kernel ${kernel.measured.length} engines `
    + `(${Object.keys(kernel.skipped).length} skipped); `
    + `loop-call ${loop.measured.length} engines; timing, RSS, artifacts OK\n`);
} finally {
  rmSync(directory, { recursive: true, force: true });
}
