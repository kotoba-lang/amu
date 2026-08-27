#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync,
} from "node:fs";
import { tmpdir, cpus, totalmem, loadavg } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptPath = fileURLToPath(import.meta.url);
const scriptRoot = resolve(dirname(scriptPath), "..");
const benchRoot = join(scriptRoot, "bench", "runtime-comparison");
const benchmarkFuel = 1_048_576;

const FIXTURES = {
  kernel_cfg_call: {
    kotoba: "kernel_cfg_call.kotoba",
    expected(n) {
      const step = (x) => {
        const v = (x * 48_271) + 1;
        return v - Math.trunc(v / 2_147_483_647) * 2_147_483_647;
      };
      const a = step(n);
      const b = step(n + 1);
      const c = step(n + 2);
      const d = step(n + 3);
      const e = step(a);
      const f = step(b);
      const g = step(c);
      const h = step(d);
      if (n === 0) return 0;
      return a + b + c + d + e + f + g + h;
    },
    note: "eight live values across calls with one if; post-allocation CFG scheduling target",
  },
  kernel: {
    kotoba: "kernel.kotoba",
    symbol: "kernel",
    expected(n) {
      let expected = n;
      for (let round = 0; round < 8; round += 1) {
        const value = (expected * 48_271) + 1;
        expected = value - (Math.trunc(value / 2_147_483_647) * 2_147_483_647);
      }
      return expected;
    },
    note: "straight-line leaf kernel; scheduler delta should be invisible here",
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

export function fileSha256(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

export function filesByteIdentical(leftPath, rightPath) {
  const left = readFileSync(leftPath);
  const right = readFileSync(rightPath);
  return left.length === right.length && left.equals(right);
}

export function hostLoadQualified(logicalCpus, averages) {
  return Math.max(...averages) <= logicalCpus;
}

function artifactDigests(artifacts) {
  return {
    kexeBytes: artifacts.nativeBytes,
    kexeSha256: fileSha256(artifacts.native),
    codeBytes: artifacts.codeBytes,
    codeSha256: fileSha256(artifacts.rawNative),
  };
}

function compareArtifacts(baselineArtifacts, candidateArtifacts) {
  const baseline = artifactDigests(baselineArtifacts);
  const candidate = artifactDigests(candidateArtifacts);
  const kexeByteIdentical = filesByteIdentical(baselineArtifacts.native, candidateArtifacts.native);
  const codeByteIdentical = filesByteIdentical(baselineArtifacts.rawNative, candidateArtifacts.rawNative);
  return {
    baseline,
    candidate,
    kexeByteIdentical,
    codeByteIdentical,
    byteIdentical: kexeByteIdentical && codeByteIdentical,
  };
}

function execute(command, args, options = {}) {
  const started = process.hrtime.bigint();
  const result = spawnSync(command, args, {
    cwd: options.cwd ?? scriptRoot,
    encoding: "utf8",
    env: { ...process.env, ...(options.env ?? {}) },
    maxBuffer: 32 * 1024 * 1024,
    timeout: options.timeout ?? 300_000,
  });
  const wallMilliseconds = Number(process.hrtime.bigint() - started) / 1e6;
  if (result.error) throw result.error;
  if (result.status !== 0) {
    throw new Error(`${command} ${args.join(" ")} failed (${result.status})\n${result.stdout}${result.stderr}`);
  }
  return { stdout: result.stdout, stderr: result.stderr, wallMilliseconds };
}

function output(command, args, cwd = scriptRoot) {
  try { return execute(command, args, { cwd, timeout: 30_000 }).stdout.trim(); }
  catch (_) { return null; }
}

function hostArchWrapper(target) {
  if (target === "x86_64" && process.arch === "arm64") return ["arch", "-x86_64"];
  return [];
}

function wrapped(command, args, target) {
  const prefix = hostArchWrapper(target);
  return prefix.length === 0 ? [command, args] : [prefix[0], [...prefix.slice(1), command, ...args]];
}

function parseSample(stdout, arm, expected) {
  const line = stdout.split(/\r?\n/).map(value => value.trim())
    .filter(value => value.startsWith("{")).at(-1);
  if (!line) throw new Error(`${arm} emitted no JSON sample`);
  const sample = JSON.parse(line);
  if (sample.format !== "kotoba.runtime-sample/v1")
    throw new Error(`${arm} emitted unexpected sample format`);
  for (const field of ["calls", "warmupCalls", "elapsedNanoseconds", "result"])
    if (!Number.isSafeInteger(sample[field]) || sample[field] < 0)
      throw new Error(`${arm} emitted invalid ${field}`);
  if (sample.result !== expected)
    throw new Error(`${arm} result ${sample.result} != ${expected}`);
  if (sample.elapsedNanoseconds < 1)
    throw new Error(`${arm} elapsedNanoseconds must be positive`);
  return sample;
}

function timedSample(arm, runner, rawNative, offset, target, n, calls, warmup, fuel, expected) {
  const args = [rawNative, offset, target, String(n), String(calls), String(warmup), String(fuel)];
  let executable = runner;
  let timedArgs = args;
  if (process.platform === "darwin") {
    executable = "/usr/bin/time";
    const [runCommand, runArgs] = wrapped(runner, args, target);
    timedArgs = ["-l", runCommand, ...runArgs];
  } else if (process.platform === "linux") {
    executable = "/usr/bin/time";
    const [runCommand, runArgs] = wrapped(runner, args, target);
    timedArgs = ["-v", runCommand, ...runArgs];
  } else {
    const wrappedRun = wrapped(runner, args, target);
    executable = wrappedRun[0];
    timedArgs = wrappedRun[1];
  }
  const run = execute(executable, timedArgs);
  const sample = parseSample(run.stdout, arm, expected);
  return {
    calls: sample.calls,
    warmupCalls: sample.warmupCalls,
    elapsedNanoseconds: sample.elapsedNanoseconds,
    nanosecondsPerKernel: sample.elapsedNanoseconds / sample.calls,
    processWallMilliseconds: run.wallMilliseconds,
  };
}

function compileCommand(root, args) {
  return ["clojure", ["-M:run", ...args], { cwd: root }];
}

function buildArtifacts(root, target, fixtureFile, directory, symbol = "kernel") {
  mkdirSync(directory, { recursive: true });
  const fixture = join(benchRoot, fixtureFile);
  const native = join(directory, "kernel.kexe");
  const rawNative = join(directory, "kernel.bin");
  const nativeRunner = join(directory, "kexe-benchmark");
  const [compileCmd, compileArgs, compileOpts] = compileCommand(root,
    ["compile", fixture, "--target", target, "--fuel", String(benchmarkFuel), "--output", native]);
  execute(compileCmd, compileArgs, compileOpts);
  const [extractCmd, extractArgs, extractOpts] = compileCommand(root,
    ["extract-native", native, "--symbol", symbol, "--output", rawNative]);
  const extracted = execute(extractCmd, extractArgs, extractOpts);
  const offsetMatch = extracted.stdout.match(/:offset\s+([0-9]+)/);
  if (!offsetMatch) throw new Error("native extraction omitted kernel offset");
  const [ccCommand, ccArgs] = wrapped("cc",
    ["-std=c11", "-O3", "-Wall", "-Wextra", "-Werror",
      join(benchRoot, "kexe-benchmark.c"), "-o", nativeRunner],
    target);
  execute(ccCommand, ccArgs);
  return {
    native,
    rawNative,
    nativeRunner,
    nativeOffset: offsetMatch[1],
    nativeBytes: statSync(native).size,
    codeBytes: statSync(rawNative).size,
  };
}

function compileColdWallMilliseconds(root, target, fixtureFile, output) {
  const fixture = join(benchRoot, fixtureFile);
  const marker = "KOTOBA_TIMING ";
  const started = process.hrtime.bigint();
  const [compileCmd, compileArgs, compileOpts] = compileCommand(root,
    ["compile", fixture, "--target", target, "--output", output]);
  const result = spawnSync(compileCmd, compileArgs, {
    ...compileOpts,
    encoding: "utf8",
    timeout: 300_000,
    maxBuffer: 16 * 1024 * 1024,
    env: { ...process.env, KOTOBA_COMPILER_TIMING: "1" },
  });
  const compileWallMilliseconds = Number(process.hrtime.bigint() - started) / 1e6;
  if (result.status !== 0) {
    throw new Error(`compile ${target} failed (${result.status})\n${result.stdout}${result.stderr}`);
  }
  const sample = {
    compileWallMilliseconds,
    artifactBytes: statSync(output).size,
  };
  // `KOTOBA_TIMING` is emitted only on the nbb fast path (`bin/amu`), not `clojure -M:run`.
  const line = result.stderr.split(/\r?\n/).find(candidate => candidate.startsWith(marker));
  if (line) {
    try {
      const timing = JSON.parse(line.slice(marker.length));
      const commandPhase = timing.phases?.find(({ phase }) => phase === "command");
      if (commandPhase) sample.nbbFastPathCommandMilliseconds = commandPhase.milliseconds;
    } catch (_) { /* optional fast-path phase timing only */ }
  }
  return sample;
}

export function main() {
const logicalCpus = cpus().length;
const loadAverage = loadavg();
const hostLoadGate = hostLoadQualified(logicalCpus, loadAverage);

const runs = boundedInteger(option("--runs", hostLoadGate ? "7" : "1"), "--runs", 30);
const calls = boundedInteger(option("--calls", hostLoadGate ? "100000" : "1000"), "--calls", 1_000_000);
const warmup = boundedInteger(option("--warmup", hostLoadGate ? "10000" : "100"), "--warmup", 1_000_000);
const n = boundedInteger(option("--n", "200"), "--n", 2_147_483_646);
const outputPath = option("--output", null);
const fixtureName = option("--fixture", "kernel_cfg_call");
const target = option("--target", process.arch === "arm64" ? "aarch64" : "x86_64");
const baselineRoot = resolve(option("--baseline-root", scriptRoot));
const candidateRoot = resolve(option("--candidate-root", scriptRoot));
const baselineCommit = option("--baseline-commit", "82c7e06494bc0a73d6e2357a3edc66387e20a210");
const candidateCommit = option("--candidate-commit", "417b01760ba2d464707f6988b731cbaad8d6f604");
const includeCompile = option("--compile", "true") !== "false";

if (!FIXTURES[fixtureName]) {
  throw new Error(`unknown --fixture ${fixtureName}; expected one of ${Object.keys(FIXTURES).join(", ")}`);
}
if (!new Set(["aarch64", "x86_64"]).has(target))
  throw new Error("--target must be aarch64 or x86_64");

const fixtureSpec = FIXTURES[fixtureName];
const expected = fixtureSpec.expected(n);
const directory = mkdtempSync(join(tmpdir(), "amu-postalloc-scheduling-"));

try {
  const baselineArtifacts = buildArtifacts(baselineRoot, target, fixtureSpec.kotoba,
    join(directory, "baseline"), fixtureSpec.symbol ?? "kernel");
  const candidateArtifacts = buildArtifacts(candidateRoot, target, fixtureSpec.kotoba,
    join(directory, "candidate"), fixtureSpec.symbol ?? "kernel");

  const baselineRuntime = [];
  const candidateRuntime = [];
  const order = [];
  for (let run = 0; run < runs; run += 1) {
    const baselineFirst = run % 2 === 0;
    const sequence = baselineFirst
      ? ["baseline", "candidate", "candidate", "baseline"]
      : ["candidate", "baseline", "baseline", "candidate"];
    for (const arm of sequence) {
      const artifacts = arm === "baseline" ? baselineArtifacts : candidateArtifacts;
      const sample = timedSample(arm, artifacts.nativeRunner, artifacts.rawNative,
        artifacts.nativeOffset, target, n, calls, warmup, benchmarkFuel, expected);
      (arm === "baseline" ? baselineRuntime : candidateRuntime).push(sample);
      order.push({ run, arm, nanosecondsPerKernel: sample.nanosecondsPerKernel });
    }
  }

  let compile = null;
  if (includeCompile) {
    try {
      const extension = "kexe";
      const baselineCompile = [];
      const candidateCompile = [];
      const compileOrder = [];
      for (let run = 0; run < runs; run += 1) {
        const baselineFirst = run % 2 === 0;
        const sequence = baselineFirst
          ? ["baseline", "candidate", "candidate", "baseline"]
          : ["candidate", "baseline", "baseline", "candidate"];
        for (const arm of sequence) {
          const root = arm === "baseline" ? baselineRoot : candidateRoot;
          const output = join(directory, `compile-${arm}-${compileOrder.length}.${extension}`);
          const sample = compileColdWallMilliseconds(root, target, fixtureSpec.kotoba, output);
          (arm === "baseline" ? baselineCompile : candidateCompile).push(sample);
          compileOrder.push({ run, arm, compileWallMilliseconds: sample.compileWallMilliseconds });
        }
      }
      compile = {
        measurement: "subprocess wall clock via clojure -M:run; not compiler-internal phase time",
        baseline: {
          samples: baselineCompile,
          compileWallMilliseconds: summary(baselineCompile.map(s => s.compileWallMilliseconds)),
        },
        candidate: {
          samples: candidateCompile,
          compileWallMilliseconds: summary(candidateCompile.map(s => s.compileWallMilliseconds)),
        },
        order: compileOrder,
      };
    } catch (error) {
      compile = { error: error instanceof Error ? error.message : String(error) };
    }
  }

  const artifactComparison = compareArtifacts(baselineArtifacts, candidateArtifacts);
  const performanceVerdict = hostLoadGate ? "deferred-quiet-host-rerun" : "unqualified-host-load";
  const fixtureVerdict = artifactComparison.codeByteIdentical ? "non-sensitive" : "scheduler-sensitive";

  const report = {
    format: "amu.postalloc-scheduling-benchmark/v1",
    fixture: fixtureName,
    fixtureNote: fixtureSpec.note,
    target,
    rosetta: target === "x86_64" && process.arch === "arm64",
    contract: {
      n,
      calls,
      warmupCalls: warmup,
      expectedResult: expected,
      runs,
      samplesPerArm: baselineRuntime.length,
      rotation: "ABBA/BAAB per run pair",
      fuelPerInstance: benchmarkFuel,
      compilerLauncher: "clojure -M:run",
      nativeBoundary: "benchmark-only direct W^X invocation; no production supervisor or safety claim",
      hostLoadGate,
      reducedRuntimeUnderHostLoad: !hostLoadGate,
    },
    isolation: {
      amuDiffCommits: `${baselineCommit}..${candidateCommit}`,
      amuChangedPaths: ["deps.edn", "deps-lock.edn", "docs/adr/0275-post-allocation-cfg-scheduling.*", "test/kotoba/compiler/aggregate_abi_test.clj", "test/kotoba/compiler/isa_execution_test.clj"],
      kotobaMir: { before: "699ead0308065ffb0eb2919bfeefd0123e9b0d46", after: "ad739526d9f80cdda76fd8de3239acb4c07a8f58", changedSourceFiles: ["src/kotoba/mir.cljc"] },
      kotobaNative: { before: "7b757f79e9d3fcafacd277ce3883a11faba35ff3", after: "542ad8e1383fd3f7aef637847fb3733b079655ab", changedSourceFiles: ["deps.edn", "test/kotoba/native/machine_ir_test.clj"] },
      schedulerDelta: "post-allocation per-basic-block integer scheduling after physical MIR allocation",
    },
    environment: {
      platform: process.platform,
      hostArchitecture: process.arch,
      cpu: cpus()[0]?.model ?? null,
      logicalCpus,
      totalMemoryBytes: totalmem(),
      loadAverage,
      hostLoadQualified: hostLoadGate,
      node: process.version,
      baseline: {
        root: baselineRoot,
        commit: output("git", ["rev-parse", "HEAD"], baselineRoot),
        dirty: Boolean(output("git", ["-c", "core.fsmonitor=false", "status", "--porcelain"], baselineRoot)),
        kotobaNativePin: output("git", ["grep", "-A1", "kotoba-native", "deps.edn"], baselineRoot)?.split("\n")[1] ?? null,
      },
      candidate: {
        root: candidateRoot,
        commit: output("git", ["rev-parse", "HEAD"], candidateRoot),
        dirty: Boolean(output("git", ["-c", "core.fsmonitor=false", "status", "--porcelain"], candidateRoot)),
        kotobaNativePin: output("git", ["grep", "-A1", "kotoba-native", "deps.edn"], candidateRoot)?.split("\n")[1] ?? null,
      },
    },
    artifacts: {
      baseline: artifactComparison.baseline,
      candidate: artifactComparison.candidate,
      kexeByteIdentical: artifactComparison.kexeByteIdentical,
      codeByteIdentical: artifactComparison.codeByteIdentical,
      byteIdentical: artifactComparison.byteIdentical,
    },
    qualification: {
      hostLoad: {
        logicalCpus,
        loadAverage,
        maxLoadAverage: Math.max(...loadAverage),
        qualified: hostLoadGate,
      },
      performance: {
        verdict: performanceVerdict,
        note: hostLoadGate
          ? "host load is within the per-CPU gate; timing still requires a quiet-host rerun before any improvement claim"
          : "host load exceeds logical CPU count; medians and perfgate are diagnostic only",
      },
      fixture: {
        verdict: fixtureVerdict,
        basis: "extracted-native-sha256",
        schedulerSensitive: !artifactComparison.codeByteIdentical,
      },
    },
    runtime: {
      baseline: {
        nanosecondsPerKernel: summary(baselineRuntime.map(sample => sample.nanosecondsPerKernel)),
        processWallMilliseconds: summary(baselineRuntime.map(sample => sample.processWallMilliseconds)),
        samples: baselineRuntime,
      },
      candidate: {
        nanosecondsPerKernel: summary(candidateRuntime.map(sample => sample.nanosecondsPerKernel)),
        processWallMilliseconds: summary(candidateRuntime.map(sample => sample.processWallMilliseconds)),
        samples: candidateRuntime,
      },
      order,
    },
    compile,
  };

  const encoded = `${JSON.stringify(report, null, 2)}\n`;
  if (outputPath) writeFileSync(resolve(outputPath), encoded);
  process.stdout.write(encoded);
} finally {
  rmSync(directory, { recursive: true, force: true });
}
}

if (process.argv[1] && resolve(process.argv[1]) === resolve(scriptPath)) main();
