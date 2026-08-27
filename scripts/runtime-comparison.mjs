#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import {
  mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync,
} from "node:fs";
import { tmpdir, cpus, totalmem } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const benchRoot = join(root, "bench", "runtime-comparison");
const benchmarkFuel = 1_048_576;

const FIXTURES = {
  kernel: {
    kotoba: "kernel.kotoba",
    rust: "kernel.rs",
    benchmark: "unrolled-modular-mix-v1",
    engines: ["rust", "clojure", "clojurescript", "amu-wasm32", "amu-native"],
    arithmetic: "8 identical quotient/remainder mix rounds stay within exact i64 and JavaScript safe integers",
    expected(n) {
      let expected = n;
      for (let round = 0; round < 8; round += 1) {
        const value = (expected * 48_271) + 1;
        expected = value - (Math.trunc(value / 2_147_483_647) * 2_147_483_647);
      }
      return expected;
    },
  },
  kernel_loop_call: {
    kotoba: "kernel_loop_call.kotoba",
    rust: "kernel_loop_call.rs",
    benchmark: "loop-call-mix-v1",
    engines: ["rust", "amu-wasm32", "amu-native"],
    arithmetic: "n iterations; each calls id(1) and accumulates — acc and counter live across call and back edge",
    expected(n) {
      return n;
    },
  },
};

function option(name, fallback) {
  const index = process.argv.lastIndexOf(name);
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

// Engines whose toolchain is not installed are skipped by name and reason, not
// dropped. A comparison that silently omits an engine reads exactly like one
// where that engine was measured and did fine.
const optionalEngines = [
  { name: "go", probe: ["go", ["version"]] },
  { name: "mojo", probe: ["mojo", ["--version"]] },
  { name: "python", probe: ["python3", ["--version"]] },
  { name: "typescript-node", probe: ["tsc", ["--version"]] },
  { name: "typescript-deno", probe: ["deno", ["--version"]] },
];

function available(probe) {
  return output(probe[0], probe[1]) !== null;
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
    ...(sample.fuelPerInstance === undefined ? {}
      : { fuelPerInstance: sample.fuelPerInstance }),
    ...(sample.maxCallsPerInstance === undefined ? {}
      : { maxCallsPerInstance: sample.maxCallsPerInstance }),
    ...(sample.fuelPerCall === undefined ? {} : { fuelPerCall: sample.fuelPerCall }),
  };
}

function build(directory, target, fixtureSpec) {
  const fixture = join(benchRoot, fixtureSpec.kotoba);
  const enabled = new Set(fixtureSpec.engines);
  const wasm = join(directory, "kernel.wasm");
  const native = join(directory, "kernel.kexe");
  const rawNative = join(directory, "kernel.bin");
  const nativeRunner = join(directory, "kexe-benchmark");
  const rust = join(directory, "kernel-rust");
  const cljs = join(directory, "kernel-cljs.cjs");
  const cljsOutputDir = join(directory, "cljs-out");
  mkdirSync(cljsOutputDir, { recursive: true });
  const durations = {};
  const step = (name, command, args, options) => {
    const result = execute(command, args, options);
    durations[name] = result.wallMilliseconds;
    return result;
  };

  step("amuWasm", process.execPath,
    [join(root, "bin", "amu"), "compile", fixture, "--target", "wasm32",
      "--fuel", String(benchmarkFuel), "--output", wasm]);
  step("amuNative", process.execPath,
    [join(root, "bin", "amu"), "compile", fixture, "--target", target,
      "--fuel", String(benchmarkFuel), "--output", native]);
  const extracted =   step("amuNativeExtract", process.execPath,
    [join(root, "bin", "amu"), "extract-native", native, "--symbol", "kernel", "--output", rawNative]);
  const offsetMatch = extracted.stdout.match(/:offset\s+([0-9]+)/);
  if (!offsetMatch) throw new Error("native extraction omitted kernel offset");
  const nativeOffset = offsetMatch[1];
  step("nativeBenchmarkRunner", "cc",
    ["-std=c11", "-O3", "-Wall", "-Wextra", "-Werror",
      join(benchRoot, "kexe-benchmark.c"), "-o", nativeRunner]);
  if (enabled.has("rust")) {
    step("rust", "rustc",
      ["--edition", "2021", "-C", "opt-level=3", "-C", "codegen-units=1",
        "-C", "strip=symbols", join(benchRoot, fixtureSpec.rust), "-o", rust]);
  }
  if (enabled.has("clojurescript")) {
    step("clojurescript", "clojure",
      ["-M:runtime-bench", "-m", "cljs.main", "-O", "advanced", "-t", "node",
        "-d", cljsOutputDir, "-o", cljs, "-c", "bench.runtime-kernel"],
      { timeout: 300_000 });
  }

  const go = join(directory, "kernel-go");
  const mojo = join(directory, "kernel-mojo");
  // `--outDir`, not `--outFile`: TypeScript 6 removed the latter outright
  // (`error TS5102: Option 'outFile' has been removed`), which is why this
  // step failed on the Ubuntu runners while macOS, on tsc 5.x, still passed.
  // One input file plus an output directory emits `kernel.js` inside it.
  const typescriptDir = join(directory, "kernel-ts");
  const typescript = join(typescriptDir, "kernel.js");
  const skipped = {};
  for (const engine of optionalEngines) {
    if (!available(engine.probe)) skipped[engine.name] = `${engine.probe[0]} not on PATH`;
  }
  if (fixtureSpec === FIXTURES.kernel) {
    if (!skipped.go) {
      step("go", "go", ["build", "-o", go, join(benchRoot, "kernel.go")]);
    }
    if (!skipped.mojo) {
      step("mojo", "mojo", ["build", join(benchRoot, "kernel.mojo"), "-o", mojo]);
    }
    if (!skipped["typescript-node"]) {
      step("typescript", "tsc",
        [join(benchRoot, "kernel.ts"), "--outDir", typescriptDir,
          "--target", "es2022", "--lib", "es2022,dom"]);
    }
  }
  return {
    paths: { fixture, wasm, native, rawNative, nativeRunner, rust, cljs, go, mojo, typescript },
    nativeOffset,
    durations,
    skipped,
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
const fixtureName = option("--fixture", "kernel");
const fixtureSpec = FIXTURES[fixtureName];
if (!fixtureSpec) {
  throw new Error(`unknown --fixture ${fixtureName}; expected one of ${Object.keys(FIXTURES).join(", ")}`);
}
if (fixtureName === "kernel_loop_call" && n + 2 > benchmarkFuel) {
  throw new Error(`--n must be at most ${benchmarkFuel - 2} for the loop-call fuel contract`);
}
const expected = fixtureSpec.expected(n);
const directory = mkdtempSync(join(tmpdir(), "amu-runtime-comparison-"));

try {
  const target = hostNativeTarget();
  const built = build(directory, target, fixtureSpec);
  const common = [String(n), String(calls), String(warmup)];
  const wasmBatchCalibrationLimit = Math.max(calls, warmup);
  const enabled = new Set(fixtureSpec.engines);
  const definitions = {};
  if (enabled.has("rust")) definitions.rust = [built.paths.rust, common, {}];
  if (enabled.has("clojure")) {
    definitions.clojure = ["clojure", ["-M", join(benchRoot, "kernel.clj"), ...common], {}];
  }
  if (enabled.has("clojurescript")) {
    definitions.clojurescript = [process.execPath, [built.paths.cljs, ...common], {}];
  }
  if (enabled.has("amu-wasm32")) {
    definitions["amu-wasm32"] = [process.execPath,
      [join(benchRoot, "wasm-runner.mjs"), built.paths.wasm, ...common,
        String(benchmarkFuel), String(wasmBatchCalibrationLimit)], {}];
  }
  if (enabled.has("amu-native")) {
    definitions["amu-native"] = [built.paths.nativeRunner,
      [built.paths.rawNative, built.nativeOffset, target, String(n),
        String(calls), String(warmup), String(benchmarkFuel)], {}];
  }
  if (fixtureName === "kernel") {
    if (!built.skipped.go) definitions.go = [built.paths.go, common, {}];
    if (!built.skipped.mojo) definitions.mojo = [built.paths.mojo, common, {}];
    if (!built.skipped.python) {
      definitions.python = ["python3", [join(benchRoot, "kernel.py"), ...common], {}];
    }
    if (!built.skipped["typescript-node"]) {
      definitions["typescript-node"] = [process.execPath, [built.paths.typescript, ...common], {}];
    }
    if (!built.skipped["typescript-deno"]) {
      definitions["typescript-deno"] =
        ["deno", ["run", "--quiet", join(benchRoot, "kernel.ts"), ...common], {}];
    }
  }
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
    fixture: fixtureName,
    benchmark: fixtureSpec.benchmark,
    contract: {
      n, calls, warmupCalls: warmup, runs, expectedResult: expected,
      arithmetic: fixtureSpec.arithmetic,
      timing: "in-process steady state after explicit warmup; process wall and RSS are separate",
      fuelPerInstance: benchmarkFuel,
      wasmMaxCallsPerInstance: raw["amu-wasm32"]?.[0]?.maxCallsPerInstance ?? null,
      wasmFuel: "Wasm calibrates a workload-specific safe batch on fresh admitted instances before timing; native resets the same benchmark fuel before each call; only call intervals are accumulated",
      nativeBoundary: "benchmark-only direct W^X invocation; no production supervisor or sandbox claim",
      optimization: "each compiler/JIT may optimize the same observable algorithm",
    },
    environment: {
      platform: process.platform,
      architecture: process.arch,
      cpu: cpus()[0]?.model ?? null,
      logicalCpus: cpus().length,
      totalMemoryBytes: totalmem(),
      node: process.version,
      rustc: output("rustc", ["--version"]),
      clojure: output("clojure", ["-Sdescribe"]),
      go: output("go", ["version"]),
      mojo: output("mojo", ["--version"]),
      python: output("python3", ["--version"]),
      typescript: output("tsc", ["--version"]),
      deno: output("deno", ["--version"]),
      compilerCommit: output("git", ["rev-parse", "HEAD"]),
      compilerDirty: Boolean(output("git", ["-c", "core.fsmonitor=false", "status", "--porcelain"])),
    },
    buildMilliseconds: built.durations,
    artifacts: {
      ...(enabled.has("rust") ? { rust: artifact(built.paths.rust) } : {}),
      kotobaSource: artifact(built.paths.fixture),
      ...(enabled.has("clojure") ? { clojureSource: artifact(join(benchRoot, "kernel.clj")) } : {}),
      ...(enabled.has("clojurescript") ? { clojurescript: artifact(built.paths.cljs) } : {}),
      amuWasm32: artifact(built.paths.wasm),
      amuNativeKexe: artifact(built.paths.native),
      amuNativeCode: artifact(built.paths.rawNative),
      amuNativeProvenance: artifact(`${built.paths.native}.provenance.edn`),
      ...(fixtureName === "kernel" ? {
        go: built.skipped.go ? null : artifact(built.paths.go),
        mojo: built.skipped.mojo ? null : artifact(built.paths.mojo),
        typescript: built.skipped["typescript-node"] ? null : artifact(built.paths.typescript),
        pythonSource: artifact(join(benchRoot, "kernel.py")),
        typescriptSource: artifact(join(benchRoot, "kernel.ts")),
      } : {}),
    },
    skippedEngines: built.skipped,
    engines,
  };
  const encoded = `${JSON.stringify(report, null, 2)}\n`;
  if (outputPath) writeFileSync(resolve(outputPath), encoded);
  process.stdout.write(encoded);
} finally {
  rmSync(directory, { recursive: true, force: true });
}
