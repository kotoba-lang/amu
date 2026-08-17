#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const directory = mkdtempSync(join(tmpdir(), "amu-runtime-comparison-test-"));
const reportPath = join(directory, "report.json");
const calls = 1_000;
const warmupCalls = 50;

try {
  const run = spawnSync(process.execPath,
    [join(root, "scripts", "runtime-comparison.mjs"),
      "--runs", "1", "--calls", String(calls),
      "--warmup", String(warmupCalls), "--n", "5",
      "--output", reportPath],
    { cwd: root, encoding: "utf8", timeout: 600_000, maxBuffer: 32 * 1024 * 1024 });
  if (run.error) throw run.error;
  if (run.status !== 0) throw new Error(`runtime comparison failed\n${run.stdout}${run.stderr}`);
  const report = JSON.parse(readFileSync(reportPath, "utf8"));
  if (report.format !== "kotoba.runtime-comparison/v1") throw new Error("wrong report format");
  if (report.contract.expectedResult !== 516860764) throw new Error("wrong common-kernel result");
  if (!report.contract.nativeBoundary.includes("no production supervisor"))
    throw new Error("native benchmark boundary is not explicit");
  // Required engines are the normalization baseline and the two reference
  // lowerings; they may never be absent. Optional engines depend on a
  // toolchain the host may not have, so each must be either measured or named
  // in skippedEngines with a reason — an engine that vanishes from the report
  // is indistinguishable from one that was measured and did fine.
  const required = ["rust", "clojure", "clojurescript", "amu-wasm32", "amu-native"];
  const optional = ["go", "mojo", "python", "typescript-node", "typescript-deno"];
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
  const names = measured;
  for (const name of names) {
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
  // A skipped engine contributes a null artifact rather than disappearing.
  for (const [name, artifact] of Object.entries(report.artifacts)) {
    if (artifact === null) continue;
    if (!Number.isSafeInteger(artifact.bytes) || artifact.bytes < 1)
      throw new Error(`artifact size evidence is invalid for ${name}`);
  }
  process.stdout.write(
    `runtime-comparison: ${names.length} real engines `
    + `(${Object.keys(skipped).length} skipped), shared result, timing, RSS, `
    + "and artifacts OK\n");
} finally {
  rmSync(directory, { recursive: true, force: true });
}
