#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync,
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
  kernel_batch: {
    kotoba: "kernel_batch.kotoba",
    rust: "kernel_batch.rs",
    benchmark: "artifact-batch-modular-mix-v1",
    metric: "artifact-batch",
    engines: ["amu-native"],
    comparators: ["rust"],
    arithmetic: "one artifact call performs the declared recurrence count and returns its final state as a checksum",
    expected(n, iterations) {
      let expected = n;
      for (let index = 0; index < iterations; index += 1)
        expected = modularStep(expected);
      return expected;
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

function parseSample(stdout, engine, expected, batchIterations = null) {
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
  if (batchIterations !== null
      && (sample.calls !== 1 || sample.warmupCalls !== 0
        || sample.iterations !== batchIterations || sample.hostCalls !== 1))
    throw new Error(`${engine} violated the one-boundary artifact-batch contract`);
  if (batchIterations !== null && engine === "amu-native"
      && (sample.fuelInitial !== batchIterations + 2
        || sample.fuelConsumed !== batchIterations + 2
        || sample.fuelRemaining !== 0))
    throw new Error("amu-native did not consume the exact sealed batch fuel");
  return sample;
}

function timedSample(engine, command, args, expected, env = {}, batchIterations = null) {
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
  const sample = parseSample(run.stdout, engine, expected, batchIterations);
  return {
    result: sample.result,
    calls: sample.calls,
    warmupCalls: sample.warmupCalls,
    elapsedNanoseconds: sample.elapsedNanoseconds,
    nanosecondsPerKernel: sample.elapsedNanoseconds / sample.calls,
    ...(batchIterations === null ? {} : {
      iterations: sample.iterations,
      hostCalls: sample.hostCalls,
      nanosecondsPerIteration: sample.elapsedNanoseconds / sample.iterations,
    }),
    processWallMilliseconds: run.wallMilliseconds,
    maxRssBytes: maximumRss(run.stderr) ?? sample.maxRssBytes ?? null,
    ...(sample.fuelPerInstance === undefined ? {}
      : { fuelPerInstance: sample.fuelPerInstance }),
    ...(sample.maxCallsPerInstance === undefined ? {}
      : { maxCallsPerInstance: sample.maxCallsPerInstance }),
    ...(sample.fuelPerCall === undefined ? {} : { fuelPerCall: sample.fuelPerCall }),
    ...(sample.fuelInitial === undefined ? {} : { fuelInitial: sample.fuelInitial }),
    ...(sample.fuelRemaining === undefined ? {} : { fuelRemaining: sample.fuelRemaining }),
    ...(sample.fuelConsumed === undefined ? {} : { fuelConsumed: sample.fuelConsumed }),
  };
}

function build(directory, target, fixtureSpec, enabled, skipped, fuel) {
  const fixtureSource = readFileSync(join(benchRoot, fixtureSpec.kotoba), "utf8");
  const fixture = join(directory, "source.kotoba");
  writeFileSync(fixture, fixtureSource);
  const wasmFixture = fixtureSource.includes("(defn main") ? fixture : join(directory, "wasm-fixture.kotoba");
  if (fixtureSpec.metric !== "artifact-batch" && wasmFixture !== fixture) {
    const source = fixtureSource.replace(/\(:export \[kernel\]\)/, "(:export [kernel main])")
      + "\n(defn main [] :i64 (kernel 1))\n";
    writeFileSync(wasmFixture, source);
  }
  const wasm = join(directory, "kernel.wasm");
  const native = join(directory, "kernel.kexe");
  const rawNative = join(directory, "kernel.bin");
  const nativeRunner = join(directory, "kexe-benchmark");
  const wasmRunner = join(directory, "wasm-runner.mjs");
  const browserHost = join(directory, "browser-host.mjs");
  if (fixtureSpec.metric !== "artifact-batch") {
    writeFileSync(browserHost, readFileSync(join(root, "runtime", "browser-host.mjs")));
    writeFileSync(wasmRunner, readFileSync(join(benchRoot, "wasm-runner.mjs"), "utf8")
      .replace("../../runtime/browser-host.mjs", "./browser-host.mjs"));
  }
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
  if (fixtureSpec.metric !== "artifact-batch") {
    step("amuWasm", "clojure",
      ["-M:run", "compile", wasmFixture, "--target", "wasm32",
        "--fuel", String(fuel), "--output", wasm]);
  }
  step("amuNative", "clojure",
    ["-M:run", "compile", fixture, "--target", target,
      "--fuel", String(fuel), "--output", native]);
  const extracted = step("amuNativeExtract", "clojure",
    ["-M:run", "extract-native", native, "--symbol", "kernel", "--output", rawNative]);
  const offsetMatch = extracted.stdout.match(/:offset\s+([0-9]+)/);
  if (!offsetMatch) throw new Error("native extraction omitted kernel offset");
  const nativeOffset = offsetMatch[1];
  step("nativeBenchmarkRunner", "cc",
    ["-std=c11", "-O3", "-Wall", "-Wextra", "-Werror",
      join(benchRoot, fixtureSpec.metric === "artifact-batch"
        ? "kexe-batch-benchmark.c" : "kexe-benchmark.c"), "-o", nativeRunner]);
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
    paths: {
      fixture,
      ...(fixtureSpec.metric === "artifact-batch" ? {}
        : { wasmFixture, wasm, wasmRunner, browserHost }),
      native, rawNative, nativeRunner, rust, cljs, go, mojo, typescript,
    },
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

function bundleFile(bundlePath, relative) {
  if (typeof relative !== "string" || relative.length === 0 || relative.startsWith("/"))
    throw new Error("prepared bundle contains an invalid path");
  const path = resolve(bundlePath, relative);
  if (!path.startsWith(`${resolve(bundlePath)}/`))
    throw new Error(`prepared bundle path escapes its root: ${relative}`);
  return path;
}

function verifyPreparedBundle(bundlePath, expectedContract, expectedDigest) {
  const metadataPath = join(bundlePath, "bundle.json");
  const metadataBytes = readFileSync(metadataPath);
  const digest = createHash("sha256").update(metadataBytes).digest("hex");
  if (!expectedDigest || digest !== expectedDigest)
    throw new Error(`prepared bundle manifest SHA-256 ${digest} does not match caller-bound digest`);
  const metadata = JSON.parse(metadataBytes);
  if (metadata.format !== "kotoba.runtime-prepared-bundle/v1")
    throw new Error("prepared bundle has an unsupported format");
  for (const relative of Object.values(metadata.built.paths)) bundleFile(bundlePath, relative);
  for (const [key, value] of Object.entries(expectedContract)) {
    if (metadata.contract[key] !== value)
      throw new Error(`prepared bundle ${key} ${metadata.contract[key]} != requested ${value}`);
  }
  for (const [relative, sealed] of Object.entries(metadata.files)) {
    const path = bundleFile(bundlePath, relative);
    if (!existsSync(path)) throw new Error(`prepared bundle omitted ${relative}`);
    const actual = artifact(path);
    if (actual.bytes !== sealed.bytes || actual.sha256 !== sealed.sha256)
      throw new Error(`prepared bundle hash mismatch: ${relative}`);
  }
  const source = metadata.files[metadata.built.paths.fixture]?.sha256;
  const provenanceText = readFileSync(bundleFile(bundlePath,
    metadata.built.paths.nativeProvenance), "utf8");
  const provenanceSource = provenanceText.match(/:source-sha256\s+"([0-9a-f]{64})"/)?.[1];
  if (!source || provenanceSource !== source)
    throw new Error("prepared bundle provenance does not identify its sealed source");
  return metadata;
}

function writePreparedBundle(bundlePath, contract, built, enabled) {
  const relativePaths = Object.fromEntries(Object.entries(built.paths)
    .filter(([, path]) => existsSync(path))
    .map(([name, path]) => [name, path.slice(bundlePath.length + 1)]));
  const provenance = `${built.paths.native}.provenance.edn`;
  relativePaths.nativeProvenance = provenance.slice(bundlePath.length + 1);
  const files = Object.fromEntries(Object.values(relativePaths)
    .map(relative => [relative, artifact(join(bundlePath, relative))]));
  const metadata = {
    format: "kotoba.runtime-prepared-bundle/v1",
    contract,
    preparedAt: new Date().toISOString(),
    compiler: {
      commit: output("git", ["rev-parse", "HEAD"]),
      dirty: Boolean(output("git", ["-c", "core.fsmonitor=false", "status", "--porcelain"])),
    },
    toolchains: {
      rustc: enabled.has("rust") ? output("rustc", ["--version"]) : null,
    },
    enabled: [...enabled],
    built: { paths: relativePaths, nativeOffset: built.nativeOffset, durations: built.durations,
      skipped: built.skipped },
    files,
  };
  writeFileSync(join(bundlePath, "bundle.json"), `${JSON.stringify(metadata, null, 2)}\n`);
  return { metadata, digest: artifact(join(bundlePath, "bundle.json")).sha256 };
}

const runs = boundedInteger(option("--runs", "5"), "--runs", 30);
const calls = boundedInteger(option("--calls", "100000"), "--calls", 1_000_000);
const warmup = boundedInteger(option("--warmup", "10000"), "--warmup", 1_000_000);
const n = boundedInteger(option("--n", "200"), "--n", 2_147_483_646);
const iterations = boundedInteger(option("--iterations", "100000"), "--iterations", 1_048_574);
const outputPath = option("--output", null);
const preparePath = option("--prepare", null);
const measurePath = option("--measure", null);
const expectedBundleDigest = option("--bundle-sha256", null);
if (preparePath && measurePath) throw new Error("--prepare and --measure are mutually exclusive");
const fixtureName = option("--fixture", "kernel");
const suite = option("--suite", "core");
if (!new Set(["core", "competitive"]).has(suite))
  throw new Error("--suite must be core or competitive");
const fixtureSpec = FIXTURES[fixtureName];
if (!fixtureSpec) {
  throw new Error(`unknown --fixture ${fixtureName}; expected one of ${Object.keys(FIXTURES).join(", ")}`);
}
const batchMode = fixtureSpec.metric === "artifact-batch";
const fixtureFuel = batchMode ? iterations + 2 : benchmarkFuel;
if (fixtureName === "kernel_loop_call" && n + 2 > benchmarkFuel) {
  throw new Error(`--n must be at most ${benchmarkFuel - 2} for the loop-call fuel contract`);
}
const disabled = new Set(option("--disable-engines", "").split(",").filter(Boolean));
const unknownDisabled = [...disabled].filter(name => !(name in comparatorTools));
if (unknownDisabled.length > 0)
  throw new Error(`unknown --disable-engines value(s): ${unknownDisabled.join(", ")}`);
const enabled = new Set(fixtureSpec.engines ?? coreEngines);
const skipped = {};
if (suite === "competitive" && !measurePath) {
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
const expected = fixtureSpec.expected(n, iterations);
const directory = preparePath ? resolve(preparePath)
  : measurePath ? resolve(measurePath)
    : mkdtempSync(join(tmpdir(), "amu-runtime-comparison-"));
const temporaryDirectory = !preparePath && !measurePath;
const logicalCpus = cpus().length;
const loadBefore = loadavg();
class PreparationComplete extends Error {
  constructor(encoded) { super("preparation complete"); this.encoded = encoded; }
}

try {
  const target = hostNativeTarget();
  let built;
  let preparedMetadata = null;
  if (measurePath) {
    preparedMetadata = verifyPreparedBundle(directory,
      { fixture: fixtureName, suite, n, iterations: batchMode ? iterations : null,
        fuel: fixtureFuel, target, benchmark: fixtureSpec.benchmark },
      expectedBundleDigest);
    enabled.clear();
    for (const name of preparedMetadata.enabled) enabled.add(name);
    built = {
      paths: Object.fromEntries(Object.entries(preparedMetadata.built.paths)
        .filter(([name]) => name !== "nativeProvenance")
        .map(([name, relative]) => [name, bundleFile(directory, relative)])),
      nativeOffset: preparedMetadata.built.nativeOffset,
      durations: preparedMetadata.built.durations,
      skipped: preparedMetadata.built.skipped,
    };
  } else {
    if (preparePath && existsSync(directory) && readdirSync(directory).length !== 0)
      throw new Error("--prepare directory must be absent or empty");
    mkdirSync(directory, { recursive: true });
    built = build(directory, target, fixtureSpec, enabled, skipped, fixtureFuel);
    if (preparePath) {
      const sealed = writePreparedBundle(directory,
        { fixture: fixtureName, suite, n, iterations: batchMode ? iterations : null,
          fuel: fixtureFuel, target, benchmark: fixtureSpec.benchmark }, built, enabled);
      const encoded = `${JSON.stringify({
        format: "kotoba.runtime-prepare-report/v1",
        bundle: directory,
        bundleSha256: sealed.digest,
        contract: sealed.metadata.contract,
        files: sealed.metadata.files,
        buildMilliseconds: built.durations,
      }, null, 2)}\n`;
      if (outputPath) writeFileSync(resolve(outputPath), encoded);
      throw new PreparationComplete(encoded);
    }
  }
  const common = [String(n), String(calls), String(warmup)];
  const wasmBatchCalibrationLimit = Math.max(calls, warmup);
  const definitions = {};
  if (enabled.has("rust")) definitions.rust = [built.paths.rust,
    batchMode ? [String(n), String(iterations)] : common, {}];
  if (enabled.has("clojure")) {
    definitions.clojure = ["clojure", ["-M", join(benchRoot, "kernel.clj"), ...common], {}];
  }
  if (enabled.has("clojurescript")) {
    definitions.clojurescript = [process.execPath, [built.paths.cljs, ...common], {}];
  }
  if (enabled.has("amu-wasm32")) {
    definitions["amu-wasm32"] = [process.execPath,
      [built.paths.wasmRunner, built.paths.wasm, ...common,
        String(benchmarkFuel), String(wasmBatchCalibrationLimit)], {}];
  }
  if (enabled.has("amu-native")) {
    definitions["amu-native"] = [built.paths.nativeRunner,
      batchMode
        ? [built.paths.rawNative, built.nativeOffset, target, String(n),
          String(iterations), String(fixtureFuel), String(fixtureFuel)]
        : [built.paths.rawNative, built.nativeOffset, target, String(n),
          String(calls), String(warmup), String(fixtureFuel)], {}];
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
    const sequence = pairs.length === 0 ? names
      : pairs.flatMap(([left, right]) => run % 2 === 0
        ? [left, right, right, left]
        : [right, left, left, right]);
    for (const name of sequence) {
      const [command, args, env] = definitions[name];
      raw[name].push(timedSample(name, command, args, expected, env,
        batchMode ? iterations : null));
    }
  }
  const engines = Object.fromEntries(names.map(name => {
    const samples = raw[name];
    const timing = batchMode
      ? {
        artifactBatchNanoseconds: summary(samples.map(sample => sample.elapsedNanoseconds)),
        nanosecondsPerIteration: summary(samples.map(sample => sample.nanosecondsPerIteration)),
      }
      : { steadyStateNanosecondsPerKernel:
          summary(samples.map(sample => sample.nanosecondsPerKernel)) };
    return [name, {
      runs: samples.length,
      ...timing,
      processWallMilliseconds: summary(samples.map(sample => sample.processWallMilliseconds)),
      maxRssBytes: samples.every(sample => sample.maxRssBytes !== null)
        ? summary(samples.map(sample => sample.maxRssBytes)) : null,
      samples,
    }];
  }));
  const rustMedian = batchMode
    ? engines.rust?.nanosecondsPerIteration.median ?? null
    : engines.rust?.steadyStateNanosecondsPerKernel.median ?? null;
  for (const value of Object.values(engines))
    value.slowdownVsRust = rustMedian === null
      ? null : (batchMode ? value.nanosecondsPerIteration.median
        : value.steadyStateNanosecondsPerKernel.median) / rustMedian;

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
    metric: batchMode ? "artifact-batch-nanoseconds-per-iteration"
      : "per-call-abi-nanoseconds-per-kernel",
    normalization: rustMedian === null
      ? { engine: "rust", status: suite === "core" ? "not-requested" : "unavailable" }
      : { engine: "rust", status: "measured" },
    contract: {
      n, calls: batchMode ? 1 : calls, warmupCalls: batchMode ? 0 : warmup,
      iterations: batchMode ? iterations : null, runs, expectedResult: expected,
      samplesPerEngine: raw[names[0]].length,
      rotation: "all-engine-pairs ABBA/BAAB per run",
      arithmetic: fixtureSpec.arithmetic,
      enginePolicy: suite === "core"
        ? (batchMode ? "Rust-independent Amu native artifact-batch evidence"
          : "Rust-independent Amu native/Wasm semantic and execution evidence")
        : "optional comparison adapters; unavailable engines are explicit and produce no ratio",
      timing: batchMode
        ? "one timed call crosses into each compiled artifact; the complete iteration loop is inside that artifact"
        : "in-process steady state after explicit warmup; process wall and RSS are separate",
      compilerLauncher: "clojure -M:run canonical compiler entrypoint",
      fuelPerInstance: fixtureFuel,
      wasmMaxCallsPerInstance: raw["amu-wasm32"]?.[0]?.maxCallsPerInstance ?? null,
      wasmFuel: batchMode ? null
        : "Wasm calibrates a workload-specific safe batch on fresh admitted instances before timing; native resets the same benchmark fuel before each call; only call intervals are accumulated",
      hostCallsPerSample: batchMode ? 1 : calls,
      fuelContract: batchMode
        ? "exact: exported wrapper + loop entry + one charge per recurrence; fuel = iterations + 2"
        : "fixed benchmark fuel, reset or freshly instantiated as documented",
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
      rustc: enabled.has("rust")
        ? (preparedMetadata?.toolchains?.rustc ?? output("rustc", ["--version"])) : null,
      clojure: enabled.has("clojure") || enabled.has("clojurescript")
        ? output("clojure", ["-Sdescribe"]) : null,
      go: enabled.has("go") ? output("go", ["version"]) : null,
      mojo: enabled.has("mojo") ? output("mojo", ["--version"]) : null,
      python: enabled.has("python") ? output("python3", ["--version"]) : null,
      typescript: enabled.has("typescript-node") ? output("tsc", ["--version"]) : null,
      deno: enabled.has("typescript-deno") ? output("deno", ["--version"]) : null,
      compilerCommit: preparedMetadata?.compiler.commit ?? output("git", ["rev-parse", "HEAD"]),
      compilerDirty: preparedMetadata?.compiler.dirty
        ?? Boolean(output("git", ["-c", "core.fsmonitor=false", "status", "--porcelain"])),
      preparedBundle: preparedMetadata === null ? null : {
        format: preparedMetadata.format,
        preparedAt: preparedMetadata.preparedAt,
        verifiedFileCount: Object.keys(preparedMetadata.files).length,
        buildPhaseEnteredDuringMeasure: false,
      },
    },
    buildMilliseconds: built.durations,
    artifacts: {
      ...(enabled.has("rust") ? { rust: artifact(built.paths.rust) } : {}),
      ...(enabled.has("rust") ? { rustSource: artifact(join(benchRoot, fixtureSpec.rust)) } : {}),
      kotobaSource: artifact(built.paths.fixture),
      ...(batchMode ? {} : { kotobaWasmSource: artifact(built.paths.wasmFixture) }),
      ...(enabled.has("clojure") ? { clojureSource: artifact(join(benchRoot, "kernel.clj")) } : {}),
      ...(enabled.has("clojurescript") ? { clojurescript: artifact(built.paths.cljs) } : {}),
      ...(batchMode ? {} : { amuWasm32: artifact(built.paths.wasm) }),
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
} catch (error) {
  if (error instanceof PreparationComplete) process.stdout.write(error.encoded);
  else throw error;
} finally {
  if (temporaryDirectory) rmSync(directory, { recursive: true, force: true });
}
