#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const directory = mkdtempSync(join(tmpdir(), "amu-a64-pressure-call-"));
const kotoba = join(root, "bin", "kotoba");

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: root, encoding: "utf8", timeout: 300_000,
    maxBuffer: 16 * 1024 * 1024, ...options,
  });
  if (result.error) throw result.error;
  if (result.status !== 0)
    throw new Error(`${command} ${args.join(" ")} failed\n${result.stdout}${result.stderr}`);
  return result.stdout;
}

const kernels = [
  ["add-one", 28, null],
  ["local-call-live-constant", 44, [5, 16]],
  ["register-pressure", 264, [5, 224]],
  ["sum-five", 56, null],
  ["tail-call-five", 100, [5, 19]],
];

try {
  const artifact = join(directory, "corpus.kexe");
  run(kotoba, ["-M", "compile",
    join(root, "bench", "runtime-comparison", "pressure-call-corpus.kotoba"),
    "--target", "aarch64", "--output", artifact],
  { env: { ...process.env, KOTOBA_COMPILER_DAEMON: "0" } });
  if (statSync(artifact).size > 4666)
    throw new Error("AArch64 pressure/call corpus KEXE exceeded its landed size");

  let runner = null;
  if (process.arch === "arm64") {
    runner = join(directory, "runner");
    run("cc", ["-std=c11", "-O3", "-Wall", "-Wextra", "-Werror",
      join(root, "bench", "runtime-comparison", "kexe-benchmark.c"), "-o", runner]);
  }

  for (const [symbol, expectedLength, execution] of kernels) {
    const binary = join(directory, `${symbol}.bin`);
    const extraction = run(kotoba,
      ["-M", "extract-native", artifact, "--symbol", symbol, "--output", binary]);
    const offset = extraction.match(/:offset\s+([0-9]+)/)?.[1];
    const length = Number(extraction.match(/:length\s+([0-9]+)/)?.[1]);
    if (offset === undefined || length !== expectedLength)
      throw new Error(`${symbol} expected ${expectedLength} bytes, got ${length}`);
    if (runner && execution) {
      const [input, expected] = execution;
      const sample = JSON.parse(run(runner,
        [binary, offset, "aarch64", String(input), "1", "1"]));
      if (sample.result !== expected)
        throw new Error(`${symbol} returned ${sample.result}, expected ${expected}`);
    }
  }
  process.stdout.write(
    `aarch64-pressure-call-corpus: ${kernels.length} size contracts` +
    `${process.arch === "arm64" ? " and 3 W^X executions" : ""} passed\n`);
} finally {
  rmSync(directory, { recursive: true, force: true });
}
