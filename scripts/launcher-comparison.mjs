#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const nbb = join(root, "node_modules", "nbb", "cli.js");
const legacy = join(root, "bin", "kotoba");
const amu = join(root, "bin", "amu");

function option(name, fallback) {
  const index = process.argv.indexOf(name);
  return index < 0 ? fallback : process.argv[index + 1];
}

function positiveInteger(value, name) {
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed) || parsed < 1 || parsed > 30)
    throw new Error(`${name} must be an integer from 1 through 30`);
  return parsed;
}

function percentile(values, fraction) {
  const ordered = [...values].sort((left, right) => left - right);
  return ordered[Math.ceil(ordered.length * fraction) - 1];
}

function summary(values) {
  return { minimumMilliseconds: Math.min(...values),
    medianMilliseconds: percentile(values, 0.5),
    p95Milliseconds: percentile(values, 0.95),
    maximumMilliseconds: Math.max(...values) };
}

function digest(file) {
  return createHash("sha256").update(readFileSync(file)).digest("hex");
}

function compile(kind, fixture, target, output) {
  const launcherArgs = kind === "amu"
    ? [amu, "compile"]
    : [nbb, legacy, "-M", "compile"];
  const started = process.hrtime.bigint();
  const result = spawnSync(process.execPath,
    [...launcherArgs, fixture, "--target", target, "--output", output],
    { cwd: root, encoding: "utf8", timeout: 120_000, maxBuffer: 16 * 1024 * 1024 });
  const milliseconds = Number(process.hrtime.bigint() - started) / 1e6;
  if (result.error) throw result.error;
  if (result.status !== 0)
    throw new Error(`${kind} ${target} failed (${result.status})\n${result.stdout}${result.stderr}`);
  return { milliseconds, artifactSha256: digest(output), artifactBytes: statSync(output).size,
    provenanceSha256: target === "wasm32" ? null : digest(`${output}.provenance.edn`) };
}

const runs = positiveInteger(option("--runs", "5"), "--runs");
const fixture = resolve(root, option("--fixture", "examples/w1-pure.kotoba"));
const target = option("--target", process.arch === "arm64" ? "aarch64" : "x86_64");
const outputPath = option("--output", null);
const directory = mkdtempSync(join(tmpdir(), "amu-launcher-comparison-"));

try {
  const samples = { legacyNbbFront: [], amuNodeFront: [] };
  for (let run = 0; run < runs; run += 1) {
    for (const kind of run % 2 === 0 ? ["legacy", "amu"] : ["amu", "legacy"]) {
      const output = join(directory, `${kind}-${run}.kexe`);
      samples[kind === "amu" ? "amuNodeFront" : "legacyNbbFront"].push(
        compile(kind, fixture, target, output));
    }
  }
  const reference = samples.legacyNbbFront[0];
  for (const sample of [...samples.legacyNbbFront, ...samples.amuNodeFront]) {
    if (sample.artifactSha256 !== reference.artifactSha256
        || sample.provenanceSha256 !== reference.provenanceSha256)
      throw new Error("launcher choice changed artifact or provenance bytes");
  }
  const legacySummary = summary(samples.legacyNbbFront.map(({ milliseconds }) => milliseconds));
  const amuSummary = summary(samples.amuNodeFront.map(({ milliseconds }) => milliseconds));
  const report = { format: "amu.launcher-comparison/v1", fixture, target, runs,
    environment: { platform: process.platform, architecture: process.arch,
      node: process.version,
      commit: spawnSync("git", ["rev-parse", "HEAD"], { cwd: root, encoding: "utf8" }).stdout.trim(),
      dirty: spawnSync("git", ["status", "--porcelain"], { cwd: root, encoding: "utf8" }).stdout.trim() !== "" },
    boundary: "Each sample starts Node; legacy additionally loads NBB for bin/kotoba before starting the same compiler runtime.",
    legacyNbbFront: { ...legacySummary, samples: samples.legacyNbbFront },
    amuNodeFront: { ...amuSummary, samples: samples.amuNodeFront },
    medianMillisecondsSaved: legacySummary.medianMilliseconds - amuSummary.medianMilliseconds,
    medianSpeedup: legacySummary.medianMilliseconds / amuSummary.medianMilliseconds,
    parity: { artifactSha256: reference.artifactSha256,
      provenanceSha256: reference.provenanceSha256, artifactBytes: reference.artifactBytes } };
  const encoded = `${JSON.stringify(report, null, 2)}\n`;
  if (outputPath) writeFileSync(resolve(outputPath), encoded);
  else process.stdout.write(encoded);
} finally {
  rmSync(directory, { recursive: true, force: true });
}
