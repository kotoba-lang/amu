#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import {
  mkdtempSync, readFileSync, rmSync, statSync, writeFileSync,
} from "node:fs";
import { tmpdir, cpus, totalmem } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const benchRoot = join(root, "bench", "runtime-comparison");

function option(name, fallback) {
  const index = process.argv.indexOf(name);
  return index < 0 ? fallback : process.argv[index + 1];
}

function boundedInteger(value, name, maximum) {
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed) || parsed < 1 || parsed > maximum)
    throw new Error(`${name} must be an integer from 1 through ${maximum}`);
  return parsed;
}

function percentile(values, fraction) {
  const ordered = [...values].sort((left, right) => left - right);
  return ordered[Math.ceil(ordered.length * fraction) - 1];
}

function summary(values) {
  return {
    minimum: Math.min(...values),
    median: percentile(values, 0.5),
    p95: percentile(values, 0.95),
    maximum: Math.max(...values),
  };
}

function execute(command, args, options = {}) {
  const started = process.hrtime.bigint();
  const result = spawnSync(command, args, {
    cwd: options.cwd ?? root,
    encoding: "utf8",
    env: { ...process.env, ...(options.env ?? {}) },
    maxBuffer: 32 * 1024 * 1024,
    timeout: options.timeout ?? 180_000,
  });
  const wallMilliseconds = Number(process.hrtime.bigint() - started) / 1e6;
  if (result.error) throw result.error;
  if (result.status !== 0) {
    throw new Error(`${command} ${args.join(" ")} failed (${result.status})\n${result.stdout}${result.stderr}`);
  }
  return { stdout: result.stdout, stderr: result.stderr, wallMilliseconds };
}

function output(command, args) {
  try { return execute(command, args, { timeout: 30_000 }).stdout.trim(); }
  catch (_) { return null; }
}

function hostNativeTarget() {
  if (process.arch === "arm64") return "aarch64";
  if (process.arch === "x64") return "x86_64";
  throw new Error(`unsupported native benchmark architecture ${process.arch}`);
}

function maximumRss(stderr) {
  if (process.platform === "darwin") {
    const match = stderr.match(/^\s*([0-9]+)\s+maximum resident set size\s*$/m);
    return match ? Number(match[1]) : null;
  }
  if (process.platform === "linux") {
    const match = stderr.match(/^\s*Maximum resident set size \(kbytes\):\s*([0-9]+)\s*$/m);
    return match ? Number(match[1]) * 1024 : null;
  }
  return null;
}

function parseSample(stdout, engine, expected) {
  const line = stdout.split(/\r?\n/).map(value => value.trim())
    .filter(value => value.startsWith("{")).at(-1);
  if (!line) throw new Error(`${engine} emitted no JSON sample`);
  const sample = JSON.parse(line);
  if (sample.format !== "kotoba.runtime-sample/v1")
    throw new Error(`${engine} emitted unexpected sample format`);
  for (const field of ["calls", "warmupCalls", "elapsedNanoseconds", "result"])
    if (!Number.isSafeInteger(sample[field]) || sample[field] < 0)
      throw new Error(`${engine} emitted invalid ${field}`);
  if (sample.result !== expected)
    throw new Error(`${engine} result ${sample.result} != ${expected}`);
  if (sample.elapsedNanoseconds < 1)
    throw new Error(`${engine} elapsedNanoseconds must be positive`);
  return sample;
}

function timedSample(engine, command, args, expected, env = {}) {
  let executable = command;
  let timedArgs = args;
  if (process.platform === "darwin") {
    executable = "/usr/bin/time";
    timedArgs = ["-l", command, ...args];
  } else if (process.platform === "linux") {
    executable = "/usr/bin/time";
    timedArgs = ["-v", command, ...args];
  }
  const run = execute(executable, timedArgs, { env });
  const sample = parseSample(run.stdout, engine, expected);
  return {
    calls: sample.calls,
    warmupCalls: sample.warmupCalls,
    elapsedNanoseconds: sample.elapsedNanoseconds,
    nanosecondsPerKernel: sample.elapsedNanoseconds / sample.calls,
    processWallMilliseconds: run.wallMilliseconds,
    maxRssBytes: maximumRss(run.stderr) ?? sample.maxRssBytes ?? null,
  };
}

function build(directory, target) {
  const fixture = join(benchRoot, "kernel.kotoba");
  const wasm = join(directory, "kernel.wasm");
  const native = join(directory, "kernel.kexe");
  const rawNative = join(directory, "kernel.bin");
  const nativeRunner = join(directory, "kexe-benchmark");
  const rustO0 = join(directory, "kernel-rust-o0");
  const rustO2 = join(directory, "kernel-rust-o2");
  const rust = join(directory, "kernel-rust-o3");
  const cljs = join(directory, "kernel-cljs.cjs");
  const cljsOutputDir = join(directory, "cljs-out");
  const durations = {};
  const step = (name, command, args, options) => {
    const result = execute(command, args, options);
    durations[name] = result.wallMilliseconds;
    return result;
  };

  step("amuWasm", join(root, "bin", "kotoba"),
    ["-M", "compile", fixture, "--target", "wasm32", "--output", wasm]);
  step("amuNative", join(root, "bin", "kotoba"),
    ["-M", "compile", fixture, "--target", target, "--output", native]);
  const extracted = step("amuNativeExtract", join(root, "bin", "kotoba"),
    ["-M", "extract-native", native, "--symbol", "kernel", "--output", rawNative]);
  const offsetMatch = extracted.stdout.match(/:offset\s+([0-9]+)/);
  if (!offsetMatch) throw new Error("native extraction omitted kernel offset");
  const nativeOffset = offsetMatch[1];
  step("nativeBenchmarkRunner", "cc",
    ["-std=c11", "-O3", "-Wall", "-Wextra", "-Werror",
      join(benchRoot, "kexe-benchmark.c"), "-o", nativeRunner]);
  for (const [name, level, outputPath] of [
    ["rustLlvmO0", "0", rustO0],
    ["rustLlvmO2", "2", rustO2],
    ["rust", "3", rust],
  ]) {
    step(name, "rustc",
      ["--edition", "2021", "-C", `opt-level=${level}`, "-C", "codegen-units=1",
        "-C", "strip=symbols", join(benchRoot, "kernel.rs"), "-o", outputPath]);
  }
  step("clojurescript", "clojure",
    ["-M:runtime-bench", "-m", "cljs.main", "-O", "advanced", "-t", "node",
      "-d", cljsOutputDir, "-o", cljs, "-c", "bench.runtime-kernel"],
    { timeout: 300_000 });
  return {
    paths: { fixture, wasm, native, rawNative, nativeRunner, rustO0, rustO2, rust, cljs },
    nativeOffset,
    durations,
  };
}

function artifact(path) {
  return { bytes: statSync(path).size };
}

const runs = boundedInteger(option("--runs", "5"), "--runs", 30);
const calls = boundedInteger(option("--calls", "100000"), "--calls", 1_000_000);
const warmup = boundedInteger(option("--warmup", "10000"), "--warmup", 1_000_000);
const n = boundedInteger(option("--n", "200"), "--n", 2_147_483_646);
const outputPath = option("--output", null);
let expected = n;
for (let round = 0; round < 8; round += 1) {
  const value = (expected * 48_271) + 1;
  expected = value - (Math.trunc(value / 2_147_483_647) * 2_147_483_647);
}
const directory = mkdtempSync(join(tmpdir(), "amu-runtime-comparison-"));

try {
  const target = hostNativeTarget();
  const built = build(directory, target);
  const common = [String(n), String(calls), String(warmup)];
  const definitions = {
    "rust-llvm-o0": [built.paths.rustO0, common, {}],
    "rust-llvm-o2": [built.paths.rustO2, common, {}],
    rust: [built.paths.rust, common, {}],
    clojure: ["clojure", ["-M", join(benchRoot, "kernel.clj"), ...common], {}],
    clojurescript: [process.execPath, [built.paths.cljs, ...common], {}],
    "amu-wasm32": [process.execPath,
      [join(benchRoot, "wasm-runner.mjs"), built.paths.wasm, ...common], {}],
    "amu-native": [built.paths.nativeRunner,
      [built.paths.rawNative, built.nativeOffset, target, String(n),
        String(calls), String(warmup)], {}],
  };
  const names = Object.keys(definitions);
  const raw = Object.fromEntries(names.map(name => [name, []]));
  // Rotate order per sample so a fixed engine is not always hottest or coldest.
  for (let run = 0; run < runs; run += 1) {
    for (let index = 0; index < names.length; index += 1) {
      const name = names[(run + index) % names.length];
      const [command, args, env] = definitions[name];
      raw[name].push(timedSample(name, command, args, expected, env));
    }
  }
  const engines = Object.fromEntries(names.map(name => {
    const samples = raw[name];
    return [name, {
      runs,
      steadyStateNanosecondsPerKernel: summary(samples.map(sample => sample.nanosecondsPerKernel)),
      processWallMilliseconds: summary(samples.map(sample => sample.processWallMilliseconds)),
      maxRssBytes: samples.every(sample => sample.maxRssBytes !== null)
        ? summary(samples.map(sample => sample.maxRssBytes)) : null,
      samples,
    }];
  }));
  const rustMedian = engines.rust.steadyStateNanosecondsPerKernel.median;
  for (const value of Object.values(engines))
    value.slowdownVsRust = value.steadyStateNanosecondsPerKernel.median / rustMedian;

  const report = {
    format: "kotoba.runtime-comparison/v1",
    benchmark: "unrolled-modular-mix-v1",
    contract: {
      n, calls, warmupCalls: warmup, runs, expectedResult: expected,
      arithmetic: "8 identical quotient/remainder mix rounds stay within exact i64 and JavaScript safe integers",
      timing: "in-process steady state after explicit warmup; process wall and RSS are separate",
      wasmFuel: "Wasm warmup and measurement are split into fresh admitted instances of at most 400 calls; only call intervals are accumulated",
      nativeBoundary: "benchmark-only direct W^X invocation; no production supervisor or sandbox claim",
      optimization: "each compiler/JIT may optimize the same observable algorithm",
      rustProfiles: "rust-llvm-o0 and rust-llvm-o2 expose LLVM optimization stages; rust remains the backward-compatible LLVM O3 baseline",
    },
    environment: {
      platform: process.platform,
      architecture: process.arch,
      cpu: cpus()[0]?.model ?? null,
      logicalCpus: cpus().length,
      totalMemoryBytes: totalmem(),
      node: process.version,
      rustc: output("rustc", ["--version"]),
      rustcVerbose: output("rustc", ["-vV"]),
      clojure: output("clojure", ["-Sdescribe"]),
      compilerCommit: output("git", ["rev-parse", "HEAD"]),
      compilerDirty: Boolean(output("git", ["-c", "core.fsmonitor=false", "status", "--porcelain"])),
    },
    buildMilliseconds: built.durations,
    artifacts: {
      rustLlvmO0: artifact(built.paths.rustO0),
      rustLlvmO2: artifact(built.paths.rustO2),
      rust: artifact(built.paths.rust),
      clojureSource: artifact(join(benchRoot, "kernel.clj")),
      clojurescript: artifact(built.paths.cljs),
      amuWasm32: artifact(built.paths.wasm),
      amuNativeKexe: artifact(built.paths.native),
      amuNativeCode: artifact(built.paths.rawNative),
      amuNativeProvenance: artifact(`${built.paths.native}.provenance.edn`),
    },
    engines,
  };
  const encoded = `${JSON.stringify(report, null, 2)}\n`;
  if (outputPath) writeFileSync(resolve(outputPath), encoded);
  process.stdout.write(encoded);
} finally {
  rmSync(directory, { recursive: true, force: true });
}
