#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import {
  chmodSync, mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const directory = mkdtempSync(join(tmpdir(), "amu-runtime-batch-test-"));
const bundle = join(directory, "prepared");
const preparedReport = join(directory, "prepared.json");
const measuredReport = join(directory, "measured.json");
const iterations = 1_000;
const n = 5;

function run(args, options = {}) {
  const result = spawnSync(process.execPath,
    [join(root, "scripts", "runtime-comparison.mjs"), ...args], {
      cwd: root, encoding: "utf8", timeout: 600_000, maxBuffer: 32 * 1024 * 1024,
      env: { ...process.env, ...(options.env ?? {}) },
    });
  if (result.error) throw result.error;
  if (options.failure) {
    if (result.status === 0) throw new Error("command unexpectedly succeeded");
  } else if (result.status !== 0) {
    throw new Error(`batch comparison failed\n${result.stdout}${result.stderr}`);
  }
  return result;
}

function fixtureArgs() {
  return ["--suite", "competitive", "--fixture", "kernel_batch",
    "--iterations", String(iterations), "--n", String(n)];
}

try {
  run([...fixtureArgs(), "--prepare", bundle, "--output", preparedReport]);
  const prepared = JSON.parse(readFileSync(preparedReport, "utf8"));
  if (prepared.format !== "kotoba.runtime-prepare-report/v1"
      || !/^[0-9a-f]{64}$/.test(prepared.bundleSha256))
    throw new Error("prepared batch bundle is not caller-bindable");

  const trapDirectory = join(directory, "compiler-traps");
  const marker = join(directory, "compiler-invoked");
  mkdirSync(trapDirectory);
  for (const command of ["clojure", "rustc", "cc"]) {
    const path = join(trapDirectory, command);
    writeFileSync(path, `#!/bin/sh\nprintf '${command}' > '${marker}'\nexit 97\n`, { mode: 0o755 });
    chmodSync(path, 0o755);
  }
  run([...fixtureArgs(), "--measure", bundle, "--bundle-sha256", prepared.bundleSha256,
    "--runs", "1", "--output", measuredReport], {
    env: { PATH: `${trapDirectory}:${process.env.PATH ?? ""}` },
  });
  const report = JSON.parse(readFileSync(measuredReport, "utf8"));
  if (report.metric !== "artifact-batch-nanoseconds-per-iteration"
      || report.contract.hostCallsPerSample !== 1
      || report.contract.iterations !== iterations
      || report.contract.fuelPerInstance !== iterations + 2
      || report.environment.preparedBundle?.buildPhaseEnteredDuringMeasure !== false)
    throw new Error("artifact-batch contract is incomplete");
  for (const engine of ["amu-native", "rust"]) {
    const measured = report.engines[engine];
    if (!measured || !(measured.nanosecondsPerIteration.median > 0)
        || measured.samples.some(sample => sample.hostCalls !== 1
          || sample.iterations !== iterations || sample.result !== 1794418855))
      throw new Error(`${engine} did not execute the sealed known-answer batch`);
  }
  const amu = report.engines["amu-native"].samples;
  if (amu.some(sample => sample.fuelInitial !== iterations + 2
      || sample.fuelConsumed !== iterations + 2 || sample.fuelRemaining !== 0))
    throw new Error("Amu batch fuel is not sufficient and exact");
  try {
    readFileSync(marker);
    throw new Error("measure re-entered a compiler tool");
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }

  const rustAssembly = join(directory, "kernel-batch.s");
  const assembly = spawnSync("rustc", ["--edition", "2021", "-C", "opt-level=3",
    "-C", "codegen-units=1", "--emit", "asm",
    join(root, "bench", "runtime-comparison", "kernel_batch.rs"), "-o", rustAssembly],
  { cwd: root, encoding: "utf8", timeout: 120_000 });
  if (assembly.status !== 0) throw new Error(`Rust assembly build failed\n${assembly.stderr}`);
  const text = readFileSync(rustAssembly, "utf8");
  if (!/kotoba_bench_batch:/.test(text)
      || !/(?:callq?|bl)\s+_?kotoba_bench_batch\b/.test(text))
    throw new Error("Rust artifact batch lost its opaque exported call boundary");

  const tampered = join(bundle, "kernel.bin");
  const bytes = readFileSync(tampered);
  writeFileSync(tampered, Buffer.concat([bytes, Buffer.from([0])]));
  const rejected = run([...fixtureArgs(), "--measure", bundle,
    "--bundle-sha256", prepared.bundleSha256, "--runs", "1"], { failure: true });
  if (!rejected.stderr.includes("prepared bundle hash mismatch"))
    throw new Error("tampered prepared artifact did not fail closed");

  process.stdout.write(
    "runtime-batch-comparison: one boundary, checksum, exact fuel, sealed measure, anti-DCE and tamper rejection OK\n");
} finally {
  rmSync(directory, { recursive: true, force: true });
}
