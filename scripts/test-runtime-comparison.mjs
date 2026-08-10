#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const directory = mkdtempSync(join(tmpdir(), "amu-runtime-comparison-test-"));
const reportPath = join(directory, "report.json");

try {
  const run = spawnSync(process.execPath,
    [join(root, "scripts", "runtime-comparison.mjs"),
      "--runs", "1", "--calls", "20", "--warmup", "5", "--n", "5",
      "--output", reportPath],
    { cwd: root, encoding: "utf8", timeout: 600_000, maxBuffer: 32 * 1024 * 1024 });
  if (run.error) throw run.error;
  if (run.status !== 0) throw new Error(`runtime comparison failed\n${run.stdout}${run.stderr}`);
  const report = JSON.parse(readFileSync(reportPath, "utf8"));
  if (report.format !== "kotoba.runtime-comparison/v1") throw new Error("wrong report format");
  if (report.contract.expectedResult !== 516860764) throw new Error("wrong common-kernel result");
  if (!report.contract.nativeBoundary.includes("no production supervisor"))
    throw new Error("native benchmark boundary is not explicit");
  const names = ["rust", "clojure", "clojurescript", "amu-wasm32", "amu-native"];
  if (JSON.stringify(Object.keys(report.engines)) !== JSON.stringify(names))
    throw new Error("runtime engine matrix changed");
  for (const name of names) {
    const engine = report.engines[name];
    if (engine.runs !== 1 || engine.samples.length !== 1)
      throw new Error(`${name} did not produce one real sample`);
    if (!(engine.steadyStateNanosecondsPerKernel.median > 0)
        || !(engine.processWallMilliseconds.median > 0)
        || !(engine.slowdownVsRust > 0))
      throw new Error(`${name} emitted an invalid timing`);
    if (engine.maxRssBytes === null || !(engine.maxRssBytes.median > 0))
      throw new Error(`${name} omitted measured RSS`);
  }
  for (const artifact of Object.values(report.artifacts))
    if (!Number.isSafeInteger(artifact.bytes) || artifact.bytes < 1)
      throw new Error("artifact size evidence is invalid");
  process.stdout.write("runtime-comparison: 5 real engines, shared result, timing, RSS, and artifacts OK\n");
} finally {
  rmSync(directory, { recursive: true, force: true });
}
