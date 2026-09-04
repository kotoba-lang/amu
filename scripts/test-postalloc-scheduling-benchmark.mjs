#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import {
  fileSha256,
  filesByteIdentical,
  hostLoadQualified,
} from "./postalloc-scheduling-benchmark.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const directory = mkdtempSync(join(tmpdir(), "amu-postalloc-scheduling-test-"));
const output = join(directory, "report.json");

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

try {
  const benchmarkModule = join(root, "scripts", "postalloc-scheduling-benchmark.mjs");
  const imported = spawnSync(process.execPath,
    ["--input-type=module", "--eval", `await import(${JSON.stringify(pathToFileURL(benchmarkModule).href)})`],
    { cwd: root, encoding: "utf8", timeout: 30_000 });
  assert(imported.status === 0, `benchmark helper import failed\n${imported.stdout}${imported.stderr}`);
  assert(imported.stdout === "", "importing benchmark helpers must not execute the benchmark");

  const left = join(directory, "left.bin");
  const right = join(directory, "right.bin");
  const sameSize = join(directory, "same-size.bin");
  writeFileSync(left, Buffer.from([1, 2, 3, 4]));
  writeFileSync(right, Buffer.from([1, 2, 3, 4]));
  writeFileSync(sameSize, Buffer.from([9, 2, 3, 4]));
  assert(filesByteIdentical(left, right), "identical bytes must compare equal");
  assert(!filesByteIdentical(left, sameSize), "same-size different bytes must not compare equal");
  assert(fileSha256(left) !== fileSha256(sameSize), "same-size different bytes must differ by sha256");
  assert(!hostLoadQualified(10, [31.385, 24.040, 21.063]), "reported overload must fail host gate");
  assert(hostLoadQualified(10, [9.5, 8.0, 7.0]), "sub-CPU load must pass host gate");

  const run = spawnSync(process.execPath,
    [join(root, "scripts", "postalloc-scheduling-benchmark.mjs"),
      "--runs", "1", "--calls", "1000", "--warmup", "100", "--n", "5",
      "--fixture", "kernel_cfg_call", "--compile", "false",
      "--baseline-root", root, "--candidate-root", root,
      "--output", output],
    { cwd: root, encoding: "utf8", timeout: 600_000, maxBuffer: 32 * 1024 * 1024 });
  if (run.status !== 0) throw new Error(`benchmark failed\n${run.stdout}${run.stderr}`);
  const report = JSON.parse(readFileSync(output, "utf8"));
  if (report.format !== "amu.postalloc-scheduling-benchmark/v1") throw new Error("wrong report format");
  if (report.runtime.baseline.samples.length !== 2) throw new Error("expected two rotated baseline samples");
  if (report.runtime.candidate.samples.length !== 2) throw new Error("expected two rotated candidate samples");
  if (report.compile !== null) throw new Error("expected compile section to be omitted with --compile false");
  if (!(report.runtime.baseline.nanosecondsPerKernel.median > 0)) throw new Error("invalid baseline timing");
  for (const arm of ["baseline", "candidate"]) {
    for (const field of ["kexeSha256", "codeSha256"]) {
      const digest = report.artifacts[arm][field];
      if (!/^[0-9a-f]{64}$/.test(digest)) throw new Error(`${arm} missing ${field}`);
    }
  }
  if (!report.artifacts.byteIdentical) throw new Error("same-root rerun must be byte-identical");
  if (!report.artifacts.kexeByteIdentical || !report.artifacts.codeByteIdentical) {
    throw new Error("same-root rerun must match both kexe and extracted code bytes");
  }
  if (!report.qualification?.performance?.verdict) throw new Error("missing performance verdict");
  if (!report.qualification?.fixture?.verdict) throw new Error("missing fixture verdict");
  if (report.qualification.fixture.verdict !== "non-sensitive") {
    throw new Error("same-root rerun must be fixture non-sensitive");
  }

  const bridgeInput = join(directory, "perfgate-unqualified.json");
  writeFileSync(bridgeInput, `${JSON.stringify({
    ...report,
    environment: { ...report.environment, hostLoadQualified: false },
    qualification: {
      ...report.qualification,
      hostLoad: { ...report.qualification.hostLoad, qualified: false },
      performance: { verdict: "unqualified-host-load" },
    },
  })}\n`);
  const bridge = spawnSync("nbb", [join(root, "scripts", "perfgate-qualify.cljs"), bridgeInput],
    { cwd: root, encoding: "utf8", timeout: 300_000, maxBuffer: 32 * 1024 * 1024 });
  if (bridge.status !== 0) throw new Error(`perfgate bridge failed\n${bridge.stdout}${bridge.stderr}`);
  const qualified = JSON.parse(bridge.stdout);
  if (qualified["plan-id"] !== `postalloc-scheduling/kernel_cfg_call.${report.target}`) {
    throw new Error(`perfgate bridge lost namespaced plan id: ${qualified["plan-id"]}`);
  }
  if (qualified["host-load-qualified?"] || qualified["any-qualified?"]
      || qualified.runtime.verdict["qualified?"]) {
    throw new Error("perfgate bridge must fail closed for an overloaded host");
  }
  console.log("postalloc-scheduling-benchmark: ok");
} finally {
  rmSync(directory, { recursive: true, force: true });
}
