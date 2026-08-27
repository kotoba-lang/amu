#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import {
  chmodSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const directory = mkdtempSync(join(tmpdir(), "amu-runtime-comparison-test-"));
const calls = 1_000;
const warmupCalls = 50;

function runComparison(outputPath, extraArgs, env = {}) {
  const run = spawnSync(process.execPath,
    [join(root, "scripts", "runtime-comparison.mjs"),
      "--runs", "1", "--calls", String(calls),
      "--warmup", String(warmupCalls), "--n", "5",
      "--output", outputPath, ...extraArgs],
    {
      cwd: root, encoding: "utf8", timeout: 600_000, maxBuffer: 32 * 1024 * 1024,
      env: { ...process.env, ...env },
    });
  if (run.error) throw run.error;
  if (run.status !== 0) throw new Error(`runtime comparison failed\n${run.stdout}${run.stderr}`);
  return JSON.parse(readFileSync(outputPath, "utf8"));
}

function validateReport(report, { suite, required, optional, expectedResult }) {
  if (report.format !== "kotoba.runtime-comparison/v2") throw new Error("wrong report format");
  if (report.suite !== suite) throw new Error(`wrong report suite ${report.suite}`);
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
        || !(engine.processWallMilliseconds.median > 0))
      throw new Error(`${name} emitted an invalid timing`);
    if (engine.maxRssBytes === null || !(engine.maxRssBytes.median > 0))
      throw new Error(`${name} omitted measured RSS`);
  }
  const rustMeasured = measured.includes("rust");
  if (rustMeasured !== (report.normalization.status === "measured"))
    throw new Error("Rust normalization status does not match measured engines");
  for (const name of measured) {
    const ratio = report.engines[name].slowdownVsRust;
    if (rustMeasured ? !(ratio > 0) : ratio !== null)
      throw new Error(`${name} emitted a ratio without a measured Rust adapter`);
  }
  for (const [name, artifact] of Object.entries(report.artifacts)) {
    if (artifact === null) continue;
    if (!Number.isSafeInteger(artifact.bytes) || artifact.bytes < 1)
      throw new Error(`artifact size evidence is invalid for ${name}`);
  }
  return { measured, skipped };
}

function validateCoreBoundary(report) {
  if (Object.keys(report.skippedEngines ?? {}).length !== 0)
    throw new Error("core suite must not probe or skip comparison adapters");
  if (report.normalization.status !== "not-requested")
    throw new Error("core suite requested an external normalization engine");
  if (report.environment.rustc !== null || "rust" in report.artifacts)
    throw new Error("core suite touched the Rust adapter boundary");
}

try {
  const coreEngines = ["amu-wasm32", "amu-native"];
  const rustMarker = join(directory, "rustc-invoked");
  const rustTrapDirectory = join(directory, "forbidden-rust");
  const rustTrap = join(rustTrapDirectory, "rustc");
  mkdirSync(rustTrapDirectory);
  writeFileSync(rustTrap,
    `#!/bin/sh\nprintf invoked > '${rustMarker}'\nexit 97\n`, { mode: 0o755 });
  chmodSync(rustTrap, 0o755);
  const noRustEnvironment = { PATH: `${rustTrapDirectory}:${process.env.PATH ?? ""}` };
  const kernelReport = runComparison(join(directory, "core-kernel.json"),
    ["--suite", "core"], noRustEnvironment);
  const kernel = validateReport(kernelReport, {
    suite: "core", required: coreEngines, optional: [],
    expectedResult: 516860764,
  });
  validateCoreBoundary(kernelReport);
  const loopReport = runComparison(join(directory, "core-loop-call.json"),
    ["--suite", "core", "--fixture", "kernel_loop_call", "--n", "200"],
    noRustEnvironment);
  if (loopReport.fixture !== "kernel_loop_call") throw new Error("loop-call fixture not recorded");
  if (loopReport.benchmark !== "loop-call-mix-v1") throw new Error("loop-call benchmark id missing");
  const loop = validateReport(loopReport, {
    suite: "core", required: coreEngines, optional: [],
    expectedResult: 200,
  });
  validateCoreBoundary(loopReport);
  if (loopReport.contract.wasmMaxCallsPerInstance !== calls)
    throw new Error("Wasm --fuel did not reach the emitted loop-call artifact");
  if (loopReport.engines["amu-wasm32"].samples[0].fuelPerInstance !== 1_048_576)
    throw new Error("Wasm sample omitted its sealed benchmark fuel");
  if (loopReport.engines["amu-native"].samples[0].fuelPerCall !== 1_048_576)
    throw new Error("native sample omitted its reset benchmark fuel");

  // Exercise the explicit-unavailability contract without executing or even
  // probing rustc. This is part of the core gate because it proves a missing
  // comparator cannot block Amu qualification or manufacture Rust ratios.
  const noRustReport = runComparison(join(directory, "competitive-no-rust.json"),
    ["--suite", "competitive", "--fixture", "kernel_loop_call", "--n", "200",
      "--disable-engines", "rust"], noRustEnvironment);
  validateReport(noRustReport, {
    suite: "competitive", required: coreEngines, optional: ["rust"],
    expectedResult: 200,
  });
  if (noRustReport.skippedEngines.rust !== "disabled by request"
      || noRustReport.environment.rustc !== null
      || noRustReport.normalization.status !== "unavailable")
    throw new Error("disabled Rust adapter leaked into competitive evidence");
  if (existsSync(rustMarker))
    throw new Error("Rust-independent suite invoked rustc");

  let competitive = "not requested";
  if (process.argv.includes("--competitive")) {
    const rustProbe = spawnSync("rustc", ["--version"], { cwd: root, encoding: "utf8" });
    if (rustProbe.status === 0) {
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
    }
    const competitiveReport = runComparison(join(directory, "competitive-loop-call.json"),
      ["--suite", "competitive", "--fixture", "kernel_loop_call", "--n", "200"]);
    const result = validateReport(competitiveReport, {
      suite: "competitive", required: coreEngines, optional: ["rust"],
      expectedResult: 200,
    });
    competitive = result.measured.includes("rust") ? "Rust measured" : "Rust skipped";
  }
  process.stdout.write(
    `runtime-comparison: Rust-independent core kernel ${kernel.measured.length} engines; `
    + `loop-call ${loop.measured.length}; no-Rust competitive boundary OK; `
    + `${competitive}; timing, RSS, artifacts OK\n`);
} finally {
  rmSync(directory, { recursive: true, force: true });
}
