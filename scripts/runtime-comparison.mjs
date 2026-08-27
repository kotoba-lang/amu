#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync,
} from "node:fs";
import { tmpdir, cpus, loadavg, totalmem } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const benchRoot = join(root, "bench", "runtime-comparison");
const benchmarkFuel = 1_048_576;
const coreEngines = ["amu-wasm32", "amu-native"];

const FIXTURES = {
  kernel: {
    kotoba: "kernel.kotoba",
    rust: "kernel.rs",
    benchmark: "unrolled-modular-mix-v1",
    comparators: [
      "rust", "clojure", "clojurescript", "go", "mojo", "python",
      "typescript-node", "typescript-deno",
    ],
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
    comparators: ["rust"],
    arithmetic: "n iterations; each calls id(1) and accumulates — acc and counter live across call and back edge",
    expected(n) {
      return n;
    },
  },
  kernel_wide: {
    kotoba: "kernel_wide.kotoba",
    rust: "kernel_wide.rs",
    benchmark: "wide-register-pressure-v1",
    comparators: ["rust"],
    arithmetic: "eight independent two-step modular-mix lanes stay live until one reduction",
    expected(n) {
      return Array.from({ length: 8 }, (_, i) => modularStep(modularStep(n + i)))
        .reduce((sum, value) => sum + value, 0);
    },
  },
  kernel_deep: {
    kotoba: "kernel_deep.kotoba",
    rust: "kernel_deep.rs",
    benchmark: "deep-spill-pressure-v1",
    comparators: ["rust"],
    arithmetic: "twenty-four independent modular-mix lanes exceed both target register pools",
    expected(n) {
      // The fixture intentionally names lane 13 `n`, shadowing the argument;
      // lanes 14..23 therefore start from that bound value. Mirror the source
      // exactly instead of silently benchmarking a cleaner, different kernel.
      const first = Array.from({ length: 14 }, (_, i) => modularStep(n + i));
      const shadowedN = first.at(-1);
      const rest = Array.from({ length: 10 }, (_, i) => modularStep(shadowedN + 14 + i));
      return [...first, ...rest].reduce((sum, value) => sum + value, 0);
    },
  },
  kernel_call: {
    kotoba: "kernel_call.kotoba",
    rust: "kernel_call.rs",
    benchmark: "call-preservation-v1",
    comparators: ["rust"],
    arithmetic: "eight values survive real local calls before reduction",
    expected(n) {
      const first = Array.from({ length: 4 }, (_, i) => modularStep(n + i));
      return [...first, ...first.map(modularStep)].reduce((sum, value) => sum + value, 0);
    },
  },
  kernel_call_branch: {
    kotoba: "kernel_call_branch.kotoba",
    rust: "kernel_call_branch.rs",
    benchmark: "branch-call-preservation-v1",
    comparators: ["rust"],
    arithmetic: "the call-preservation workload crosses an explicit control-flow join",
    expected(n) {
      if (n === 0) return 0;
      const first = Array.from({ length: 4 }, (_, i) => modularStep(n + i));
      return [...first, ...first.map(modularStep)].reduce((sum, value) => sum + value, 0);
    },
  },
};

function modularStep(value) {
  const mixed = (value * 48_271) + 1;
  return mixed - (Math.trunc(mixed / 2_147_483_647) * 2_147_483_647);
}

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

// Comparison adapters are not compiler dependencies. The core suite never
// probes them. The competitive suite records every unavailable or deliberately
// disabled adapter by name instead of silently dropping it.
const comparatorTools = {
  rust: ["rustc", ["--version"]],
  clojure: ["clojure", ["-Sdescribe"]],
  clojurescript: ["clojure", ["-Sdescribe"]],
  go: ["go", ["version"]],
  mojo: ["mojo", ["--version"]],
  python: ["python3", ["--version"]],
  "typescript-node": ["tsc", ["--version"]],
  "typescript-deno": ["deno", ["--version"]],
};

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
    result: sample.result,
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

function build(directory, target, fixtureSpec, enabled, skipped) {
  const fixture = join(benchRoot, fixtureSpec.kotoba);
  const fixtureSource = readFileSync(fixture, "utf8");
  const wasmFixture = fixtureSource.includes("(defn main") ? fixture : join(directory, "wasm-fixture.kotoba");
  if (wasmFixture !== fixture) {
    const source = fixtureSource.replace(/\(:export \[kernel\]\)/, "(:export [kernel main])")
      + "\n(defn main [] :i64 (kernel 1))\n";
    writeFileSync(wasmFixture, source);
  }
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

  // Keep runtime evidence on one canonical compiler entrypoint. Launcher
  // conformance is measured separately and must not select a different
  // code-generation path inside one comparison report.
  step("amuWasm", "clojure",
    ["-M:run", "compile", wasmFixture, "--target", "wasm32",
      "--fuel", String(benchmarkFuel), "--output", wasm]);
  step("amuNative", "clojure",
    ["-M:run", "compile", fixture, "--target", target,
      "--fuel", String(benchmarkFuel), "--output", native]);
  const extracted = step("amuNativeExtract", "clojure",
    ["-M:run", "extract-native", native, "--symbol", "kernel", "--output", rawNative]);
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
  if (fixtureSpec === FIXTURES.kernel) {
    if (enabled.has("go")) {
      step("go", "go", ["build", "-o", go, join(benchRoot, "kernel.go")]);
    }
    if (enabled.has("mojo")) {
      step("mojo", "mojo", ["build", join(benchRoot, "kernel.mojo"), "-o", mojo]);
    }
    if (enabled.has("typescript-node")) {
      step("typescript", "tsc",
        [join(benchRoot, "kernel.ts"), "--outDir", typescriptDir,
          "--target", "es2022", "--lib", "es2022,dom"]);
    }
  }
  return {
    paths: { fixture, wasmFixture, wasm, native, rawNative, nativeRunner, rust, cljs, go, mojo, typescript },
    nativeOffset,
    durations,
    skipped,
  };
}

function artifact(path) {
  const bytes = readFileSync(path);
  return {
    bytes: statSync(path).size,
    sha256: createHash("sha256").update(bytes).digest("hex"),
  };
}

const runs = boundedInteger(option("--runs", "5"), "--runs", 30);
const calls = boundedInteger(option("--calls", "100000"), "--calls", 1_000_000);
const warmup = boundedInteger(option("--warmup", "10000"), "--warmup", 1_000_000);
const n = boundedInteger(option("--n", "200"), "--n", 2_147_483_646);
const outputPath = option("--output", null);
const fixtureName = option("--fixture", "kernel");
const suite = option("--suite", "core");
if (!new Set(["core", "competitive"]).has(suite))
  throw new Error("--suite must be core or competitive");
const fixtureSpec = FIXTURES[fixtureName];
if (!fixtureSpec) {
  throw new Error(`unknown --fixture ${fixtureName}; expected one of ${Object.keys(FIXTURES).join(", ")}`);
}
if (fixtureName === "kernel_loop_call" && n + 2 > benchmarkFuel) {
  throw new Error(`--n must be at most ${benchmarkFuel - 2} for the loop-call fuel contract`);
}
const disabled = new Set(option("--disable-engines", "").split(",").filter(Boolean));
const unknownDisabled = [...disabled].filter(name => !(name in comparatorTools));
if (unknownDisabled.length > 0)
  throw new Error(`unknown --disable-engines value(s): ${unknownDisabled.join(", ")}`);
const enabled = new Set(coreEngines);
const skipped = {};
if (suite === "competitive") {
  for (const name of fixtureSpec.comparators) {
    const probe = comparatorTools[name];
    if (disabled.has(name)) skipped[name] = "disabled by request";
    else if (name === "rust"
        && (!fixtureSpec.rust || !existsSync(join(benchRoot, fixtureSpec.rust))))
      skipped[name] = "Rust semantic-twin fixture not present";
    else if (available(probe)) enabled.add(name);
    else skipped[name] = `${probe[0]} not on PATH`;
  }
}
const expected = fixtureSpec.expected(n);
const directory = mkdtempSync(join(tmpdir(), "amu-runtime-comparison-"));
const logicalCpus = cpus().length;
const loadBefore = loadavg();

try {
  const target = hostNativeTarget();
  const built = build(directory, target, fixtureSpec, enabled, skipped);
  const common = [String(n), String(calls), String(warmup)];
  const wasmBatchCalibrationLimit = Math.max(calls, warmup);
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
    if (enabled.has("go")) definitions.go = [built.paths.go, common, {}];
    if (enabled.has("mojo")) definitions.mojo = [built.paths.mojo, common, {}];
    if (enabled.has("python")) {
      definitions.python = ["python3", [join(benchRoot, "kernel.py"), ...common], {}];
    }
    if (enabled.has("typescript-node")) {
      definitions["typescript-node"] = [process.execPath, [built.paths.typescript, ...common], {}];
    }
    if (enabled.has("typescript-deno")) {
      definitions["typescript-deno"] =
        ["deno", ["run", "--quiet", join(benchRoot, "kernel.ts"), ...common], {}];
    }
  }
  const names = Object.keys(definitions);
  const raw = Object.fromEntries(names.map(name => [name, []]));
  // Every comparison is made inside an ABBA/BAAB pair.  For competitive runs
  // enumerate all engine pairs, so adding an optional adapter cannot weaken
  // the ordering contract or give one engine a fixed thermal position.
  for (let run = 0; run < runs; run += 1) {
    const pairs = [];
    for (let left = 0; left < names.length; left += 1)
      for (let right = left + 1; right < names.length; right += 1)
        pairs.push([names[left], names[right]]);
    const sequence = pairs.flatMap(([left, right]) => run % 2 === 0
      ? [left, right, right, left]
      : [right, left, left, right]);
    for (const name of sequence) {
      const [command, args, env] = definitions[name];
      raw[name].push(timedSample(name, command, args, expected, env));
    }
  }
  const engines = Object.fromEntries(names.map(name => {
    const samples = raw[name];
    return [name, {
      runs: samples.length,
      steadyStateNanosecondsPerKernel: summary(samples.map(sample => sample.nanosecondsPerKernel)),
      processWallMilliseconds: summary(samples.map(sample => sample.processWallMilliseconds)),
      maxRssBytes: samples.every(sample => sample.maxRssBytes !== null)
        ? summary(samples.map(sample => sample.maxRssBytes)) : null,
      samples,
    }];
  }));
  const rustMedian = engines.rust?.steadyStateNanosecondsPerKernel.median ?? null;
  for (const value of Object.values(engines))
    value.slowdownVsRust = rustMedian === null
      ? null : value.steadyStateNanosecondsPerKernel.median / rustMedian;

  const loadAfter = loadavg();
  const loadLimit = logicalCpus * 0.75;
  const hostLoadQualified = loadBefore[0] <= loadLimit
    && loadAfter[0] <= loadLimit
    && Math.abs(loadAfter[0] - loadBefore[0]) <= logicalCpus * 0.10;
  const report = {
    format: "kotoba.runtime-comparison/v2",
    suite,
    fixture: fixtureName,
    benchmark: fixtureSpec.benchmark,
    normalization: rustMedian === null
      ? { engine: "rust", status: suite === "core" ? "not-requested" : "unavailable" }
      : { engine: "rust", status: "measured" },
    contract: {
      n, calls, warmupCalls: warmup, runs, expectedResult: expected,
      samplesPerEngine: raw[names[0]].length,
      rotation: "all-engine-pairs ABBA/BAAB per run",
      arithmetic: fixtureSpec.arithmetic,
      enginePolicy: suite === "core"
        ? "Rust-independent Amu native/Wasm semantic and execution evidence"
        : "optional comparison adapters; unavailable engines are explicit and produce no ratio",
      timing: "in-process steady state after explicit warmup; process wall and RSS are separate",
      compilerLauncher: "clojure -M:run canonical compiler entrypoint",
      fuelPerInstance: benchmarkFuel,
      wasmMaxCallsPerInstance: raw["amu-wasm32"]?.[0]?.maxCallsPerInstance ?? null,
      wasmFuel: "Wasm calibrates a workload-specific safe batch on fresh admitted instances before timing; native resets the same benchmark fuel before each call; only call intervals are accumulated",
      nativeBoundary: "benchmark-only direct W^X invocation; no production supervisor or sandbox claim",
      optimization: "each compiler/JIT may optimize the same observable algorithm",
      rustOptimization: enabled.has("rust")
        ? "rustc --edition 2021 -C opt-level=3 -C codegen-units=1 -C strip=symbols"
        : null,
    },
    environment: {
      platform: process.platform,
      architecture: process.arch,
      cpu: cpus()[0]?.model ?? null,
      logicalCpus,
      loadAverageBefore: loadBefore,
      loadAverageAfter: loadAfter,
      hostLoadLimit: loadLimit,
      hostLoadQualified,
      totalMemoryBytes: totalmem(),
      node: process.version,
      rustc: enabled.has("rust") ? output("rustc", ["--version"]) : null,
      clojure: enabled.has("clojure") || enabled.has("clojurescript")
        ? output("clojure", ["-Sdescribe"]) : null,
      go: enabled.has("go") ? output("go", ["version"]) : null,
      mojo: enabled.has("mojo") ? output("mojo", ["--version"]) : null,
      python: enabled.has("python") ? output("python3", ["--version"]) : null,
      typescript: enabled.has("typescript-node") ? output("tsc", ["--version"]) : null,
      deno: enabled.has("typescript-deno") ? output("deno", ["--version"]) : null,
      compilerCommit: output("git", ["rev-parse", "HEAD"]),
      compilerDirty: Boolean(output("git", ["-c", "core.fsmonitor=false", "status", "--porcelain"])),
    },
    buildMilliseconds: built.durations,
    artifacts: {
      ...(enabled.has("rust") ? { rust: artifact(built.paths.rust) } : {}),
      ...(enabled.has("rust") ? { rustSource: artifact(join(benchRoot, fixtureSpec.rust)) } : {}),
      kotobaSource: artifact(built.paths.fixture),
      kotobaWasmSource: artifact(built.paths.wasmFixture),
      ...(enabled.has("clojure") ? { clojureSource: artifact(join(benchRoot, "kernel.clj")) } : {}),
      ...(enabled.has("clojurescript") ? { clojurescript: artifact(built.paths.cljs) } : {}),
      amuWasm32: artifact(built.paths.wasm),
      amuNativeKexe: artifact(built.paths.native),
      amuNativeCode: artifact(built.paths.rawNative),
      amuNativeProvenance: artifact(`${built.paths.native}.provenance.edn`),
      ...(suite === "competitive" && fixtureName === "kernel" ? {
        go: enabled.has("go") ? artifact(built.paths.go) : null,
        mojo: enabled.has("mojo") ? artifact(built.paths.mojo) : null,
        typescript: enabled.has("typescript-node") ? artifact(built.paths.typescript) : null,
        pythonSource: enabled.has("python") ? artifact(join(benchRoot, "kernel.py")) : null,
        typescriptSource: enabled.has("typescript-node") || enabled.has("typescript-deno")
          ? artifact(join(benchRoot, "kernel.ts")) : null,
      } : {}),
    },
    skippedEngines: built.skipped,
    qualification: {
      hostLoad: {
        qualified: hostLoadQualified,
        policy: "load1 before and after <= 75% of logical CPUs and drift <= 10% of logical CPUs",
      },
      performance: {
        verdict: hostLoadQualified ? "eligible-for-perfgate" : "unqualified-host-load",
      },
    },
    engines,
  };
  const encoded = `${JSON.stringify(report, null, 2)}\n`;
  if (outputPath) writeFileSync(resolve(outputPath), encoded);
  process.stdout.write(encoded);
} finally {
  rmSync(directory, { recursive: true, force: true });
}
