#!/usr/bin/env node

import { spawn, spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createInterface } from "node:readline";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const marker = "KOTOBA_TIMING ";

function option(name, fallback) {
  const index = process.argv.indexOf(name);
  return index < 0 ? fallback : process.argv[index + 1];
}

function positiveInteger(value, name) {
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed) || parsed < 1 || parsed > 100) {
    throw new Error(`${name} must be an integer from 1 through 100`);
  }
  return parsed;
}

function percentile(values, fraction) {
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.ceil(fraction * sorted.length) - 1];
}

function summary(values) {
  return {
    minimumMilliseconds: Math.min(...values),
    medianMilliseconds: percentile(values, 0.5),
    p95Milliseconds: percentile(values, 0.95),
    maximumMilliseconds: Math.max(...values),
  };
}

function commandOutput(command, args) {
  const result = spawnSync(command, args, { cwd: root, encoding: "utf8" });
  return result.status === 0 ? result.stdout.trim() : null;
}

function hostNativeTarget() {
  if (process.arch === "arm64") return "aarch64";
  if (process.arch === "x64") return "x86_64";
  throw new Error(`no ordinary native target for host architecture ${process.arch}`);
}

function timingFrom(stderr) {
  const line = stderr.split(/\r?\n/).find((candidate) => candidate.startsWith(marker));
  if (!line) throw new Error("compiler did not emit KOTOBA_TIMING data");
  const timing = JSON.parse(line.slice(marker.length));
  if (timing.format !== "kotoba.compiler-timing/v1") {
    throw new Error(`unexpected timing format ${timing.format}`);
  }
  return timing;
}

function runCompile({ fixture, target, output }) {
  const started = process.hrtime.bigint();
  const result = spawnSync(process.execPath,
    [join(root, "bin", "amu"), "compile", fixture, "--target", target, "--output", output],
    {
      cwd: root,
      encoding: "utf8",
      timeout: 120_000,
      maxBuffer: 16 * 1024 * 1024,
      env: { ...process.env, KOTOBA_COMPILER_TIMING: "1" },
    });
  const wallMilliseconds = Number(process.hrtime.bigint() - started) / 1e6;
  if (result.error) throw result.error;
  if (result.status !== 0) {
    throw new Error(`compile ${target} failed (${result.status})\n${result.stdout}${result.stderr}`);
  }
  const compilerTiming = timingFrom(result.stderr);
  const commandPhase = compilerTiming.phases.find(({ phase }) => phase === "command");
  if (!commandPhase) throw new Error("compiler timing omitted the command phase");
  return {
    wallMilliseconds,
    compilerMilliseconds: commandPhase.milliseconds,
    entrypointMilliseconds: compilerTiming.totalMilliseconds,
    startupMilliseconds: wallMilliseconds - commandPhase.milliseconds,
    phases: compilerTiming.phases,
    artifactBytes: statSync(output).size,
    provenanceBytes: statSync(`${output}.provenance.edn`).size,
    publicationBytes: statSync(`${output}.publication.edn`).size,
  };
}

function benchmarkTarget({ fixture, target, runs, directory }) {
  const samples = [];
  for (let run = 0; run < runs; run += 1) {
    const extension = target === "wasm32" ? "wasm" : "kexe";
    samples.push(runCompile({
      fixture,
      target,
      output: join(directory, `${target}-${run}.${extension}`),
    }));
  }
  return {
    target,
    runs,
    processColdWall: summary(samples.map((sample) => sample.wallMilliseconds)),
    loadedCompiler: summary(samples.map((sample) => sample.compilerMilliseconds)),
    entrypointAfterSharedSupport: summary(samples.map((sample) => sample.entrypointMilliseconds)),
    processAndNamespaceStartup: summary(samples.map((sample) => sample.startupMilliseconds)),
    artifactBytes: samples[0].artifactBytes,
    provenanceBytes: samples[0].provenanceBytes,
    publicationBytes: samples[0].publicationBytes,
    samples,
  };
}

async function nextWorkerMessage(iterator, stderr) {
  let timeoutId;
  const timeout = new Promise((_, reject) => {
    timeoutId = setTimeout(
      () => reject(new Error(`compiler worker timed out\n${stderr()}`)), 120_000);
  });
  try {
    const next = await Promise.race([iterator.next(), timeout]);
    if (next.done) throw new Error(`compiler worker exited before responding\n${stderr()}`);
    return JSON.parse(next.value);
  } finally {
    clearTimeout(timeoutId);
  }
}

async function benchmarkWorker({ fixture, target, runs, directory }) {
  const started = process.hrtime.bigint();
  const child = spawn(process.execPath,
    [join(root, "bin", "amu"), "worker", "--target", target], {
    cwd: root,
    stdio: ["pipe", "pipe", "pipe"],
    env: { ...process.env, KOTOBA_COMPILER_TIMING: "1",
      KOTOBA_WORKER_MAX_REQUESTS: String(runs + 4) },
  });
  let stderrText = "";
  child.stderr.on("data", (chunk) => { stderrText += chunk.toString(); });
  const lines = createInterface({ input: child.stdout, crlfDelay: Infinity });
  const iterator = lines[Symbol.asyncIterator]();
  const ready = await nextWorkerMessage(iterator, () => stderrText);
  const startupMilliseconds = Number(process.hrtime.bigint() - started) / 1e6;
  if (ready.format !== "kotoba.compiler-worker/v1" || ready.type !== "ready") {
    throw new Error("compiler worker omitted its ready message");
  }

  const compile = async (id, expectedCache, extraArgs = [], input = fixture) => {
    const extension = target === "wasm32" ? "wasm" : "kexe";
    const output = join(directory, `worker-${target}-${id}.${extension}`);
    const request = { id,
      args: ["compile", input, "--target", target, ...extraArgs, "--output", output] };
    const requestStarted = process.hrtime.bigint();
    child.stdin.write(`${JSON.stringify(request)}\n`);
    const response = await nextWorkerMessage(iterator, () => stderrText);
    const roundTripMilliseconds = Number(process.hrtime.bigint() - requestStarted) / 1e6;
    if (response.id !== id || response.status !== 0) {
      throw new Error(`compiler worker request ${id} failed: ${response.stderr ?? ""}`);
    }
    if (!response.stdout.includes(`:cache :${expectedCache}`)) {
      throw new Error(`compiler worker request ${id} was not a cache ${expectedCache}`);
    }
    const command = response.timing?.phases?.find(({ phase }) => phase === "command");
    if (!command) throw new Error("compiler worker response omitted command timing");
    return {
      roundTripMilliseconds,
      compilerMilliseconds: command.milliseconds,
      artifactBytes: statSync(output).size,
      output,
      provenanceOutput: `${output}.provenance.edn`,
      publicationOutput: `${output}.publication.edn`,
      stdout: response.stdout,
    };
  };

  try {
    const warmup = await compile("warmup", "miss");
    const samples = [];
    for (let run = 0; run < runs; run += 1) {
      const sample = await compile(run, "hit");
      if (!readFileSync(warmup.output).equals(readFileSync(sample.output))) {
        throw new Error(`${target} cache hit changed artifact bytes`);
      }
      if (warmup.provenanceOutput
          && !readFileSync(warmup.provenanceOutput).equals(readFileSync(sample.provenanceOutput))) {
        throw new Error(`${target} cache hit changed provenance bytes`);
      }
      if (!readFileSync(sample.publicationOutput, "utf8").includes(":kotoba.output-set/v1")) {
        throw new Error(`${target} cache hit omitted its output-set commit marker`);
      }
      samples.push({ roundTripMilliseconds: sample.roundTripMilliseconds,
        compilerMilliseconds: sample.compilerMilliseconds,
        artifactBytes: sample.artifactBytes });
    }
    const editedFixture = join(directory, `worker-${target}-semantic-edit.kotoba`);
    writeFileSync(editedFixture, `${readFileSync(fixture, "utf8")}\n`);
    const semanticEdit = await compile("semantic-edit", "miss", [], editedFixture);
    const semanticHirMiss = semanticEdit.stdout.includes(":hir :miss");
    const semanticKirHit = semanticEdit.stdout.includes(":kir :hit");
    if (!semanticHirMiss || !semanticKirHit
        || !readFileSync(warmup.output).equals(readFileSync(semanticEdit.output))) {
      throw new Error(`${target} frontend-equivalent edit did not reuse KIR`);
    }
    const changedPolicy = join(directory, `worker-${target}-changed-policy.edn`);
    writeFileSync(changedPolicy, "{}\n");
    const incremental = await compile("policy-change", "miss", ["--policy", changedPolicy]);
    const hirHit = incremental.stdout.includes(":hir :hit");
    const kirHit = incremental.stdout.includes(":kir :hit");
    if (!hirHit || !kirHit) {
      throw new Error(`${target} policy change did not reuse HIR/KIR stages`);
    }
    child.stdin.write(`${JSON.stringify({ id: "shutdown", op: "shutdown", args: [] })}\n`);
    const shutdown = await nextWorkerMessage(iterator, () => stderrText);
    if (shutdown.type !== "shutdown" || shutdown.status !== 0) {
      throw new Error("compiler worker did not acknowledge shutdown");
    }
    child.stdin.end();
    return {
      target,
      runs,
      startupMilliseconds,
      warmRoundTrip: summary(samples.map((sample) => sample.roundTripMilliseconds)),
      loadedCompiler: summary(samples.map((sample) => sample.compilerMilliseconds)),
      policyChangeIncremental: {
        roundTripMilliseconds: incremental.roundTripMilliseconds,
        compilerMilliseconds: incremental.compilerMilliseconds,
        stageCache: { hir: "hit", kir: "hit" },
      },
      semanticEditIncremental: {
        roundTripMilliseconds: semanticEdit.roundTripMilliseconds,
        compilerMilliseconds: semanticEdit.compilerMilliseconds,
        stageCache: { hir: "miss", kir: "hit" },
      },
      artifactBytes: samples[0].artifactBytes,
      samples,
    };
  } finally {
    lines.close();
    if (child.exitCode === null) child.kill();
  }
}

function enforceThreshold(name, benchmark, environmentName) {
  const text = process.env[environmentName];
  if (text === undefined) return;
  const limit = Number(text);
  if (!Number.isFinite(limit) || limit <= 0) {
    throw new Error(`${environmentName} must be a positive millisecond value`);
  }
  const observed = benchmark.processColdWall.medianMilliseconds;
  if (observed > limit) {
    throw new Error(`${name} median ${observed.toFixed(1)} ms exceeds ${environmentName}=${limit} ms`);
  }
}

const runs = positiveInteger(option("--runs", "5"), "--runs");
const fixture = resolve(root, option("--fixture", "examples/i64-semantics.kotoba"));
const outputPath = option("--output", null);
const directory = mkdtempSync(join(tmpdir(), "kotoba-performance-"));

try {
  // Populate the content-addressed classpath cache before measuring fresh
  // compiler processes. This keeps dependency resolution/network state out of
  // the result while retaining Node/nbb namespace-load costs on every sample.
  const warmup = join(directory, "warmup.wasm");
  runCompile({ fixture, target: "wasm32", output: warmup });

  const wasm = benchmarkTarget({ fixture, target: "wasm32", runs, directory });
  const native = benchmarkTarget({ fixture, target: hostNativeTarget(), runs, directory });
  const wasmWorker = await benchmarkWorker({ fixture, target: "wasm32", runs, directory });
  const nativeWorker = await benchmarkWorker({ fixture, target: hostNativeTarget(), runs, directory });

  const report = {
    format: "kotoba.performance-baseline/v1",
    benchmark: "process-cold-compile",
    generatedAt: new Date().toISOString(),
    fixture,
    environment: {
      platform: process.platform,
      architecture: process.arch,
      node: process.version,
      compilerCommit: commandOutput("git", ["rev-parse", "HEAD"]),
      compilerDirty: commandOutput("git", ["status", "--porcelain"]) !== "",
    },
    targets: [wasm, native],
    persistentWorkers: [wasmWorker, nativeWorker],
  };
  const json = `${JSON.stringify(report, null, 2)}\n`;
  if (outputPath) writeFileSync(resolve(outputPath), json);
  process.stdout.write(json);
  enforceThreshold("wasm32", wasm, "KOTOBA_BENCH_MAX_WASM_MS");
  enforceThreshold("native", native, "KOTOBA_BENCH_MAX_NATIVE_MS");
} finally {
  rmSync(directory, { recursive: true, force: true });
}
