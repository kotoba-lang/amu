#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { delimiter, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const benchmarkRoot = join(root, "benchmarks", "runtime");

function option(name, fallback) {
  const index = process.argv.indexOf(name);
  return index < 0 ? fallback : process.argv[index + 1];
}

function positiveInteger(value, name, maximum) {
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed) || parsed < 1 || parsed > maximum) {
    throw new Error(`${name} must be an integer from 1 through ${maximum}`);
  }
  return parsed;
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: options.cwd ?? root,
    encoding: "utf8",
    timeout: options.timeout ?? 180_000,
    maxBuffer: 16 * 1024 * 1024,
    env: { ...process.env, ...(options.env ?? {}) },
  });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    throw new Error(`${command} ${args.join(" ")} failed (${result.status})\n${result.stdout}${result.stderr}`);
  }
  return result.stdout.trim();
}

function commandVersion(command, args) {
  return run(command, args).split(/\r?\n/)[0];
}

function gitCheckoutState(directory) {
  return {
    gitCommit: run("git", ["rev-parse", "HEAD"], { cwd: directory }),
    dirty: run("git", ["-c", "core.fsmonitor=false", "status", "--porcelain"],
      { cwd: directory }) !== "",
  };
}

function requireUnchangedCheckout(directory, expected, label) {
  const actual = gitCheckoutState(directory);
  if (actual.gitCommit !== expected.gitCommit || actual.dirty !== expected.dirty) {
    throw new Error(`${label} checkout changed during measurement`);
  }
}

function percentile(values, fraction) {
  const sorted = [...values].sort((left, right) => left - right);
  return sorted[Math.ceil(sorted.length * fraction) - 1];
}

function summary(values) {
  return {
    minimum: Math.min(...values),
    median: percentile(values, 0.5),
    p95: percentile(values, 0.95),
    maximum: Math.max(...values),
  };
}

function hostNativeTarget() {
  if (process.arch === "arm64") return "aarch64";
  if (process.arch === "x64") return "x86_64";
  throw new Error(`unsupported native benchmark architecture ${process.arch}`);
}

function parseJsonOutput(text, lane) {
  try {
    return JSON.parse(text.split(/\r?\n/).filter(Boolean).at(-1));
  } catch (error) {
    throw new Error(`${lane} emitted invalid benchmark JSON: ${text}`, { cause: error });
  }
}

function coldSample(lane, workload) {
  const args = lane.onceArgs(workload);
  const started = process.hrtime.bigint();
  const output = run(lane.command, args, { cwd: lane.cwd });
  const wallMilliseconds = Number(process.hrtime.bigint() - started) / 1e6;
  const checksum = lane.plainOutput ? Number(output) : parseJsonOutput(output, lane.name).checksum;
  const expected = workload.expected(workload.coldIterations);
  if (checksum !== expected) {
    throw new Error(`${lane.name}/${workload.name} cold checksum mismatch: ${checksum}`);
  }
  return wallMilliseconds;
}

function supervisedBatchSample(lane, workload, iterations) {
  const started = process.hrtime.bigint();
  const output = run(lane.command, lane.batchArgs(workload, iterations), { cwd: lane.cwd });
  const wallMilliseconds = Number(process.hrtime.bigint() - started) / 1e6;
  const checksum = lane.plainOutput ? Number(output) : parseJsonOutput(output, lane.name).checksum;
  if (checksum !== workload.expected(iterations)) {
    throw new Error(`${lane.name}/${workload.name} supervised batch checksum mismatch: ${checksum}`);
  }
  return wallMilliseconds;
}

function supervisedSteadySample(lane, workload, invocationIterations,
  measuredInvocations, warmupInvocations) {
  const output = run(lane.command, lane.supervisedSteadyArgs(workload, invocationIterations), {
    cwd: lane.cwd,
    env: {
      KEXE_STRUCTURED_REPORT: "1",
      KEXE_SUPERVISED_REPEAT: String(measuredInvocations),
      KEXE_SUPERVISED_WARMUP: String(warmupInvocations),
    },
  });
  const result = output.match(/:status :ok\s+:result (-?[0-9]+)/);
  const evidence = output.match(
    /:supervised-repeat \{:warmup-invocations ([0-9]+) :measured-invocations ([0-9]+) :elapsed-nanoseconds ([0-9]+) :fuel-consumed ([0-9]+)/,
  );
  if (!result || !evidence
      || Number(result[1]) !== workload.expected(invocationIterations)
      || Number(evidence[1]) !== warmupInvocations
      || Number(evidence[2]) !== measuredInvocations
      || !(Number(evidence[3]) > 0)
      || !(Number(evidence[4]) >= 0)) {
    throw new Error(`${lane.name}/${workload.name} supervised steady contract mismatch: ${output}`);
  }
  return Number(evidence[3]) / (measuredInvocations * invocationIterations);
}

function peakResidentSetBytes(lane, workload) {
  const args = lane.onceArgs(workload);
  const timeArgs = process.platform === "darwin"
    ? ["-l", lane.command, ...args]
    : ["-v", lane.command, ...args];
  const result = spawnSync("/usr/bin/time", timeArgs, {
    cwd: lane.cwd ?? root,
    encoding: "utf8",
    timeout: 180_000,
    maxBuffer: 16 * 1024 * 1024,
    env: process.env,
  });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    throw new Error(`RSS measurement failed for ${lane.name}\n${result.stdout}${result.stderr}`);
  }
  const output = result.stdout.trim();
  const checksum = lane.plainOutput ? Number(output) : parseJsonOutput(output, lane.name).checksum;
  const expected = workload.expected(workload.coldIterations);
  if (checksum !== expected) {
    throw new Error(`${lane.name}/${workload.name} RSS checksum mismatch: ${checksum}`);
  }
  const match = process.platform === "darwin"
    ? result.stderr.match(/^\s*([0-9]+)\s+maximum resident set size$/mi)
    : result.stderr.match(/Maximum resident set size \(kbytes\):\s*([0-9]+)/i);
  if (!match) throw new Error(`${lane.name} RSS output was not recognized: ${result.stderr}`);
  return process.platform === "darwin" ? Number(match[1]) : Number(match[1]) * 1024;
}

function steadySample(lane, workload, iterations, warmupIterations) {
  const output = run(lane.command,
    lane.steadyArgs(workload, iterations, warmupIterations), { cwd: lane.cwd });
  const value = parseJsonOutput(output, lane.name);
  if (value.iterations !== iterations || value.warmupIterations !== warmupIterations
      || value.checksum !== workload.expected(iterations)
      || !(value.elapsedNanoseconds > 0)) {
    throw new Error(`${lane.name}/${workload.name} steady-state contract mismatch: ${output}`);
  }
  return value.elapsedNanoseconds / iterations;
}

function xorshift32Expected(count) {
  let state = 2_463_534_242;
  for (let index = 0; index < count; index += 1) {
    state ^= state << 13;
    state ^= state >>> 17;
    state ^= state << 5;
    state >>>= 0;
  }
  return state;
}

function vectorAllocationExpected(count) {
  const values = [3, 5, 8, 13, 21, 34, 55, 89];
  let state = 2_463_534_242;
  let total = 0;
  for (let index = 0; index < count; index += 1) {
    state ^= state << 13;
    state ^= state >>> 17;
    state ^= state << 5;
    state >>>= 0;
    total += values[state & 7];
  }
  return total;
}

const wasmLocalRootOption = option("--wasm-local-root", null);
const wasmLocalRoot = wasmLocalRootOption ? resolve(wasmLocalRootOption) : null;
const nativeLocalRootOptions = {
  kir: option("--native-kir-root", null),
  verifier: option("--native-verifier-root", null),
  backend: option("--native-backend-root", null),
};
const nativeCandidateRequested = Object.values(nativeLocalRootOptions).some(Boolean);
if (nativeCandidateRequested && !Object.values(nativeLocalRootOptions).every(Boolean)) {
  throw new Error("native candidate requires --native-kir-root, --native-verifier-root, and --native-backend-root together");
}
const nativeLocalRoots = Object.fromEntries(Object.entries(nativeLocalRootOptions)
  .map(([name, value]) => [name, value ? resolve(value) : null]));
const runs = positiveInteger(option("--runs", "5"), "--runs", 30);
const iterations = positiveInteger(option("--iterations", wasmLocalRoot ? "10000" : "5000"),
  "--iterations", wasmLocalRoot ? 10_000_000 : 5_000);
if (iterations % 2 !== 0) throw new Error("--iterations must be even for balanced-branch");
const outputPath = option("--output", null);
const directory = mkdtempSync(join(tmpdir(), "kotoba-runtime-comparison-"));
const workloads = [
  {
    name: "scalar-multiply",
    cliName: "scalar",
    exportName: "scalar",
    operation: "sum 6 * 7 for N loop iterations",
    checksumRule: "42 * N",
    coldIterations: 1,
    expected: (count) => count * 42,
  },
  {
    name: "balanced-branch",
    cliName: "branch",
    exportName: "branch",
    operation: "sum 41 for the first half and 43 for the second half of even N",
    checksumRule: "42 * N for even N",
    coldIterations: 2,
    expected: (count) => count * 42,
  },
  {
    name: "integer-mix",
    cliName: "mix",
    exportName: "mix",
    operation: "apply xorshift32 to a loop-carried state N times",
    checksumRule: "xorshift32^N(2463534242)",
    coldIterations: 1,
    expected: xorshift32Expected,
  },
  {
    name: "vector-allocate-scan",
    artifactKind: "vector",
    cliName: "vector",
    exportName: "vector-alloc",
    operation: "construct an eight-item immutable vector, xorshift32-select one item, and sum it per iteration; materialization may be scalar-replaced when the value cannot escape",
    checksumRule: "sum [3,5,8,13,21,34,55,89][xorshift32^i(seed) & 7]",
    coldIterations: 8,
    maximumIterations: wasmLocalRoot ? 100_000 : 256,
    iterationCeilingReason: wasmLocalRoot
      ? "bounds aggregate-benchmark duration while retaining optimizer-resistant timing"
      : "the recursive pinned helper and bounded native vector arena require a shallow qualification count",
    expected: vectorAllocationExpected,
  },
  {
    name: "vector-materialize-scan",
    artifactKind: "vectorBulk",
    cliName: "vector-materialize",
    exportName: "vector-escape",
    operation: "construct an eight-item immutable vector, cross a source function boundary every 512th iteration, xorshift32-select one item, and sum it; the boundary use requires materialization",
    checksumRule: "sum [3,5,8,13,21,34,55,89][xorshift32^i(seed) & 7] with retain(values) selected when i mod 512 = 0",
    coldIterations: 8,
    maximumIterations: wasmLocalRoot ? 100_000 : 256,
    iterationCeilingReason: wasmLocalRoot
      ? "bounds materialized aggregate duration while retaining optimizer-resistant timing"
      : "the recursive pinned helper and bounded native vector arena require a shallow qualification count",
    expected: vectorAllocationExpected,
  },
];

try {
  const kotobaSources = {
    scalar: join(benchmarkRoot, "scalar.kotoba"),
    vector: join(benchmarkRoot, "vector.kotoba"),
    vectorBulk: join(benchmarkRoot, "vector_escape.kotoba"),
  };
  const wasmArtifacts = {
    scalar: join(directory, "scalar.wasm"),
    vector: join(directory, "vector.wasm"),
    vectorBulk: join(directory, "vector-bulk.wasm"),
  };
  const nativeArtifacts = {
    scalar: join(directory, "scalar.kexe"),
    vector: join(directory, "vector.kexe"),
    vectorBulk: join(directory, "vector-bulk.kexe"),
  };
  const artifactKind = (workload) => workload.artifactKind ?? "scalar";
  const nativeLoader = join(directory, "kexe-loader");
  const nativeTarget = hostNativeTarget();
  const kotoba = join(root, "bin", "kotoba");
  const nativeUnsupportedKinds = new Map();
  let nativeBackend = { source: "compiler-dependency-pins" };
  let nativeCandidateClasspath = null;
  let nativeCandidateSdeps = null;

  if (nativeCandidateRequested) {
    const alias = "runtime-native-candidate";
    const override = `{:aliases {:${alias} {:override-deps {`
      + `io.github.kotoba-lang/kotoba-kir {:local/root ${JSON.stringify(nativeLocalRoots.kir)}} `
      + `io.github.kotoba-lang/kotoba-verifier {:local/root ${JSON.stringify(nativeLocalRoots.verifier)}} `
      + `io.github.kotoba-lang/kotoba-native {:local/root ${JSON.stringify(nativeLocalRoots.backend)}}}}}}`;
    nativeCandidateSdeps = override;
    nativeCandidateClasspath = run("clojure", ["-Sdeps", override, `-A:${alias}`, "-Spath"]);
    for (const candidateRoot of Object.values(nativeLocalRoots)) {
      const source = join(candidateRoot, "src");
      if (!nativeCandidateClasspath.split(delimiter).includes(source)) {
        throw new Error(`local native candidate is absent from resolved classpath: ${source}`);
      }
    }
    nativeBackend = {
      source: "local-roots",
      components: Object.fromEntries(Object.entries(nativeLocalRoots).map(([name, candidateRoot]) => [
        name,
        {
          root: candidateRoot,
          ...gitCheckoutState(candidateRoot),
        },
      ])),
      classpathVerified: true,
    };
  }

  let wasmBackend;
  if (wasmLocalRoot) {
    const alias = "runtime-wasm-candidate";
    const override = `{:aliases {:${alias} {:override-deps `
      + `{io.github.kotoba-lang/kotoba-wasm {:local/root ${JSON.stringify(wasmLocalRoot)}}}}}}`;
    const candidateClasspath = run("clojure",
      ["-Sdeps", override, `-A:${alias}`, "-Spath"]);
    const candidateSource = join(wasmLocalRoot, "src");
    if (!candidateClasspath.split(delimiter).includes(candidateSource)) {
      throw new Error(`local Wasm backend is absent from resolved classpath: ${candidateSource}`);
    }
    for (const kind of Object.keys(kotobaSources)) {
      run(process.execPath, ["--stack-size=4096", join(root, "node_modules", "nbb", "cli.js"),
        "--classpath", candidateClasspath, join(root, "src", "kotoba", "compiler", "nbb",
          "wasm_cli.cljs"), "compile", kotobaSources[kind], "--target", "wasm32", "--output",
        wasmArtifacts[kind]]);
    }
    wasmBackend = {
      source: "local-root",
      root: wasmLocalRoot,
      ...gitCheckoutState(wasmLocalRoot),
      classpathVerified: true,
    };
  } else {
    for (const kind of Object.keys(kotobaSources)) {
      run("nbb", [kotoba, "-M", "compile", kotobaSources[kind], "--target", "wasm32",
        "--output", wasmArtifacts[kind]]);
    }
    wasmBackend = { source: "compiler-dependency-pin" };
  }
  for (const kind of Object.keys(kotobaSources)) {
    try {
      if (nativeCandidateClasspath) {
        run("clojure", ["-Sdeps", nativeCandidateSdeps,
          "-M:runtime-native-candidate:run", "compile", kotobaSources[kind],
          "--target", nativeTarget, "--output", nativeArtifacts[kind]],
        { timeout: 300_000 });
      } else {
        run("nbb", [kotoba, "-M", "compile", kotobaSources[kind], "--target", nativeTarget,
          "--output", nativeArtifacts[kind]]);
      }
    } catch (error) {
      const message = String(error?.message ?? error);
      if (kind !== "vectorBulk" || !message.includes("kotoba/target-rejected")
          || !message.includes("typed values currently require")) throw error;
      nativeUnsupportedKinds.set(kind,
        "the native backend does not yet admit vector-i64 values across function boundaries");
    }
  }
  const nativeOffsets = {};
  const nativeCodes = {};
  for (const workload of workloads) {
    if (nativeUnsupportedKinds.has(artifactKind(workload))) continue;
    const code = join(directory, `${workload.exportName}.bin`);
    const extractArgs = ["extract-native", nativeArtifacts[artifactKind(workload)],
      "--symbol", workload.exportName, "--output", code];
    const extracted = nativeCandidateClasspath
      ? run("clojure", ["-Sdeps", nativeCandidateSdeps,
          "-M:runtime-native-candidate:run", ...extractArgs], { timeout: 300_000 })
      : run("nbb", [kotoba, "-M", ...extractArgs]);
    const offsetMatch = extracted.match(/:offset ([0-9]+)/);
    if (!offsetMatch) throw new Error(`native extraction omitted offset: ${extracted}`);
    nativeOffsets[workload.exportName] = offsetMatch[1];
    nativeCodes[workload.exportName] = code;
  }
  run("cc", ["-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
    join(root, "tools", "kexe_loader.c"), "-o", nativeLoader]);

  const rustBinary = join(directory, "scalar-rust");
  run("rustc", [join(benchmarkRoot, "scalar.rs"), "-C", "opt-level=3",
    "-C", "target-cpu=native", "-o", rustBinary]);

  const cljsOutput = join(directory, "scalar-cljs.js");
  const sourcePathEdn = JSON.stringify(benchmarkRoot);
  const cljsDeps = `{:paths [${sourcePathEdn}] :deps {org.clojure/clojurescript {:mvn/version \"1.12.145\"}}}`;
  run("clojure", ["-Sdeps", cljsDeps, "-M", "-m", "cljs.main", "-O", "advanced",
    "-t", "node", "-d", join(directory, "cljs-out"), "-o", cljsOutput,
    "-c", "kotoba-bench.scalar"], { cwd: directory });

  const cljDeps = `{:paths [${sourcePathEdn}] :deps {org.clojure/clojure {:mvn/version \"1.12.0\"}}}`;
  const wasmUsesTypedHost = Object.fromEntries(Object.entries(wasmArtifacts).map(([kind, artifact]) => [
    kind,
    WebAssembly.Module.imports(new WebAssembly.Module(readFileSync(artifact)))
      .some(({ module }) => module === "kotoba:typed"),
  ]));
  const lanes = [
    {
      name: "kotoba-wasm-v8", command: process.execPath,
      onceArgs: (workload) => [join(benchmarkRoot, "wasm-runner.mjs"),
        wasmArtifacts[artifactKind(workload)],
        workload.exportName, "--once", String(workload.coldIterations)],
      steadyArgs: (workload, count, warmup) => [join(benchmarkRoot, "wasm-runner.mjs"),
        wasmArtifacts[artifactKind(workload)], workload.exportName, "--steady", String(count),
        String(warmup)],
      artifactBytes: (workload) => statSync(wasmArtifacts[artifactKind(workload)]).size,
    },
    {
      name: "kotoba-wasm-wasmtime", command: "wasmtime", plainOutput: true,
      onceArgs: (workload) => ["run", "--invoke", workload.exportName,
        wasmArtifacts[artifactKind(workload)], String(workload.coldIterations)],
      artifactBytes: (workload) => statSync(wasmArtifacts[artifactKind(workload)]).size,
      steadyReason: "Wasmtime CLI exposes a fresh process invocation, not an embedded in-process timer",
      unsupportedWorkloads: new Set(workloads
        .filter((workload) => wasmUsesTypedHost[artifactKind(workload)])
        .map((workload) => workload.name)),
      unsupportedReason: "the standalone Wasmtime CLI has no kotoba:typed externref host; an embedded typed host must be measured separately",
    },
    {
      name: "kotoba-native-supervised", command: nativeLoader, plainOutput: true,
      onceArgs: (workload) => [nativeCodes[workload.exportName],
        nativeOffsets[workload.exportName], "1",
        nativeTarget, "-", String(workload.coldIterations)],
      batchArgs: (workload, count) => [nativeCodes[workload.exportName],
        nativeOffsets[workload.exportName], "1", nativeTarget, "-", String(count)],
      supervisedSteadyArgs: (workload, count) => [nativeCodes[workload.exportName],
        nativeOffsets[workload.exportName], "1", nativeTarget, "-", String(count)],
      artifactBytes: (workload) => nativeUnsupportedKinds.has(artifactKind(workload))
        ? null : statSync(nativeArtifacts[artifactKind(workload)]).size,
      loaderBytes: statSync(nativeLoader).size,
      unsupportedWorkloads: new Set(workloads
        .filter((workload) => nativeUnsupportedKinds.has(artifactKind(workload)))
        .map((workload) => workload.name)),
      unsupportedReason: nativeUnsupportedKinds.get("vectorBulk"),
    },
    {
      name: "clojure-hotspot", command: "clojure", cwd: directory,
      onceArgs: (workload) => ["-Sdeps", cljDeps, "-M", "-m", "kotoba-bench.scalar",
        workload.cliName, "--once", String(workload.coldIterations)],
      steadyArgs: (workload, count, warmup) => ["-Sdeps", cljDeps, "-M", "-m",
        "kotoba-bench.scalar", workload.cliName, "--steady", String(count), String(warmup)],
    },
    {
      name: "clojure-hotspot-boxed", command: "clojure", cwd: directory,
      onceArgs: (workload) => ["-Sdeps", cljDeps, "-M", "-m", "kotoba-bench.scalar-boxed",
        workload.cliName, "--once", String(workload.coldIterations)],
      steadyArgs: (workload, count, warmup) => ["-Sdeps", cljDeps, "-M", "-m",
        "kotoba-bench.scalar-boxed", workload.cliName, "--steady", String(count),
        String(warmup)],
    },
    {
      name: "clojurescript-v8-advanced", command: process.execPath,
      onceArgs: (workload) => [cljsOutput, workload.cliName, "--once",
        String(workload.coldIterations)],
      steadyArgs: (workload, count, warmup) => [cljsOutput, workload.cliName, "--steady",
        String(count), String(warmup)],
      artifactBytes: statSync(cljsOutput).size,
    },
    {
      name: "rust-native-release", command: rustBinary,
      onceArgs: (workload) => [workload.cliName, "--once", String(workload.coldIterations)],
      steadyArgs: (workload, count, warmup) => [workload.cliName, "--steady", String(count),
        String(warmup)],
      artifactBytes: statSync(rustBinary).size,
    },
  ];

  const workloadResults = workloads.map((workload) => {
    const measuredIterations = Math.min(iterations, workload.maximumIterations ?? iterations);
    const workloadWarmupIterations = Math.min(measuredIterations,
      wasmLocalRoot ? 1_000_000 : 5_000);
    const results = lanes.map((lane) => {
      if (lane.unsupportedWorkloads?.has(workload.name)) {
        return {
          lane: lane.name,
          support: { measured: false, reason: lane.unsupportedReason },
          artifactBytes: typeof lane.artifactBytes === "function"
            ? lane.artifactBytes(workload) : lane.artifactBytes ?? null,
          loaderBytes: lane.loaderBytes ?? null,
        };
      }
      const cold = [];
      for (let index = 0; index < runs; index += 1) {
        cold.push(coldSample(lane, workload));
      }
      const result = {
        lane: lane.name,
        coldProcessWallMilliseconds: summary(cold),
        peakResidentSetBytes: peakResidentSetBytes(lane, workload),
        artifactBytes: typeof lane.artifactBytes === "function"
          ? lane.artifactBytes(workload) : lane.artifactBytes ?? null,
        loaderBytes: lane.loaderBytes ?? null,
      };
      if (lane.steadyArgs) {
        const steady = [];
        for (let index = 0; index < runs; index += 1) {
          steady.push(steadySample(lane, workload, measuredIterations,
            workloadWarmupIterations));
        }
        result.steadyNanosecondsPerIteration = summary(steady);
      } else if (lane.supervisedSteadyArgs) {
        const invocationIterations = Math.min(measuredIterations, 256);
        const measuredInvocations = 100;
        const warmupInvocations = 10;
        const steady = [];
        for (let index = 0; index < runs; index += 1) {
          steady.push(supervisedSteadySample(lane, workload, invocationIterations,
            measuredInvocations, warmupInvocations));
        }
        result.steadyNanosecondsPerIteration = summary(steady);
        result.supervisedSteady = {
          invocationIterations, measuredInvocations, warmupInvocations,
          excludesProcessStartup: true,
        };
      } else {
        result.steadyState = { measured: false, reason: lane.steadyReason };
      }
      if (lane.batchArgs) {
        const batchIterations = Math.min(measuredIterations, 256);
        const batches = [];
        for (let index = 0; index < runs; index += 1) {
          batches.push(supervisedBatchSample(lane, workload, batchIterations));
        }
        result.supervisedBatchIterations = batchIterations;
        result.supervisedBatchWallMilliseconds = summary(batches);
        result.supervisedBatchNanosecondsPerIterationIncludingStartup = summary(
          batches.map((milliseconds) => (milliseconds * 1e6) / batchIterations));
      }
      return result;
    });

    const rust = results.find(({ lane }) => lane === "rust-native-release");
    for (const result of results) {
      if (result.support?.measured === false) continue;
      result.coldProcessRatioToRust = result.coldProcessWallMilliseconds.median
        / rust.coldProcessWallMilliseconds.median;
      if (result.steadyNanosecondsPerIteration) {
        result.steadyRatioToRust = result.steadyNanosecondsPerIteration.median
          / rust.steadyNanosecondsPerIteration.median;
      }
    }
    return {
      benchmark: workload.name,
      semantics: {
        operation: workload.operation,
        checksumRule: workload.checksumRule,
        coldChecksum: workload.expected(workload.coldIterations),
        steadyChecksum: workload.expected(measuredIterations),
        coldIterations: workload.coldIterations,
        steadyIterations: measuredIterations,
        warmupIterations: workloadWarmupIterations,
        iterationCeiling: workload.maximumIterations ?? null,
        iterationCeilingReason: workload.iterationCeilingReason ?? null,
      },
      results,
    };
  });

  if (wasmLocalRoot) {
    requireUnchangedCheckout(wasmLocalRoot, wasmBackend, "Wasm candidate");
  }
  if (nativeCandidateRequested) {
    for (const [name, candidateRoot] of Object.entries(nativeLocalRoots)) {
      requireUnchangedCheckout(candidateRoot, nativeBackend.components[name],
        `native ${name} candidate`);
    }
  }

  const report = {
    format: "kotoba.runtime-comparison/v7",
    benchmark: "runtime-workload-matrix",
    generatedAt: new Date().toISOString(),
    environment: {
      platform: process.platform, architecture: process.arch, node: process.version,
      clojure: commandVersion("clojure", ["-e", "(print (clojure-version))"]),
      clojurescript: "1.12.145",
      rustc: commandVersion("rustc", ["--version"]),
      wasmtime: commandVersion("wasmtime", ["--version"]),
      compilerCommit: run("git", ["rev-parse", "HEAD"]),
      wasmBackend,
      nativeBackend,
    },
    methodology: {
      cold: "fresh process and the workload's minimum checksum-stable iteration count; includes runtime and artifact loading",
      steady: "in-process timer after an explicitly reported warmup; excludes process startup",
      nativeSafety: "Kotoba native cold and steady lanes use the production W^X, fork-supervised sandbox loader; steady repeat admits only an empty capability allowlist, resets fuel and every bounded arena before each deterministic invocation, and times inside the sandbox child",
      rss: "one fresh-process maximum resident set measurement via /usr/bin/time",
      typedCollections: "non-escaping literals use checked Wasm locals; materialized literals use one bounded copy from fixed 2-page scratch memory into a validated immutable externref; standalone Wasmtime is unsupported only for artifacts retaining typed-host imports",
      nativeVectorBoundary: nativeUnsupportedKinds.has("vectorBulk")
        ? "the function-boundary materialization workload is explicitly unsupported until native vector-i64 parameters/results are admitted"
        : "native vector-i64 function-boundary compilation and supervised cold execution are measured",
      wasmVectorRepresentations: {
        nonEscaping: "scalar-replaced into checked Wasm locals",
        materialized: "fixed scratch memory plus one bounded typed-host copy",
      },
      caveat: "five loop workloads improve scalar, branch, dependent-integer, non-escaping aggregate, and materialized aggregate coverage but do not establish general language speed",
      wasmLoopLimit: wasmLocalRoot
        ? "verified local backend override permits up to 10,000,000 iterations"
        : "iterations are capped at 5,000 because the pinned backend still lowers workload-dependent loop-helper frames through the Wasm host stack",
    },
    runs,
    workloads: workloadResults,
  };
  const json = `${JSON.stringify(report, null, 2)}\n`;
  if (outputPath) writeFileSync(resolve(outputPath), json);
  process.stdout.write(json);
} finally {
  rmSync(directory, { recursive: true, force: true });
}
