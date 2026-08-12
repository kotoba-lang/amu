#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdtempSync, readFileSync, realpathSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { delimiter, dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const coordinate = "io.github.kotoba-lang/kotoba-wasm";

function option(args, name, fallback = null) {
  const index = args.indexOf(name);
  return index < 0 ? fallback : args[index + 1];
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: options.cwd ?? root,
    encoding: "utf8",
    timeout: options.timeout ?? 300_000,
    maxBuffer: 16 * 1024 * 1024,
    env: process.env,
  });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    throw new Error(`${command} ${args.join(" ")} failed (${result.status})\n${result.stdout}${result.stderr}`);
  }
  return result.stdout.trim();
}

function pinAfterCoordinate(text, pinKey) {
  const coordinateIndex = text.indexOf(coordinate);
  if (coordinateIndex < 0) throw new Error(`${coordinate} is absent`);
  const tail = text.slice(coordinateIndex);
  const match = tail.match(new RegExp(`${pinKey.replace("/", "\\/")}\\s+\"([0-9a-f]{40})\"`));
  if (!match) throw new Error(`${coordinate} has no full ${pinKey}`);
  return match[1];
}

export function extractDepsPin(text) {
  return pinAfterCoordinate(text, ":git/sha");
}

export function extractLockPin(text) {
  return pinAfterCoordinate(text, ":git-sha");
}

export function promotionState({ commit, dirty, depsPin, lockPin, checksPassed,
  remoteAdvertisesCommit = false }) {
  const pinsAgree = depsPin === lockPin;
  const compilerPinsHeadCommit = pinsAgree && depsPin === commit;
  const candidateTreePublished = !dirty && remoteAdvertisesCommit;
  return {
    candidateQualified: checksPassed,
    backendClean: !dirty,
    pinsAgree,
    compilerPinsHeadCommit,
    remoteAdvertisesCommit,
    candidateTreePublished,
    promotionReady: checksPassed && compilerPinsHeadCommit && candidateTreePublished,
  };
}

export function main(args = process.argv.slice(2)) {
  const wasmRootOption = option(args, "--wasm-root");
  if (!wasmRootOption) {
    throw new Error("usage: qualify-wasm-backend --wasm-root /absolute/path [--require-clean] [--require-pinned] [--require-published] [--output report.json]");
  }
  const wasmRoot = realpathSync(resolve(wasmRootOption));
  if (!statSync(join(wasmRoot, "deps.edn")).isFile()
      || !statSync(join(wasmRoot, "src")).isDirectory()) {
    throw new Error(`not a kotoba-wasm checkout: ${wasmRoot}`);
  }

  const commit = run("git", ["rev-parse", "HEAD"], { cwd: wasmRoot });
  const dirty = run("git", ["status", "--porcelain"], { cwd: wasmRoot }) !== "";
  const remotes = run("git", ["remote"], { cwd: wasmRoot }).split(/\r?\n/).filter(Boolean);
  const remoteName = remotes.includes("origin") ? "origin"
    : remotes.length === 1 ? remotes[0]
      : null;
  if (!remoteName) throw new Error("candidate checkout needs an unambiguous publication remote");
  const remoteUrl = run("git", ["config", "--get", `remote.${remoteName}.url`], { cwd: wasmRoot });
  const publicationChecked = args.includes("--require-published");
  const remoteAdvertisesCommit = publicationChecked
    && run("git", ["ls-remote", "--refs", remoteName], { cwd: wasmRoot })
      .split(/\r?\n/)
      .some((line) => line.split(/\s+/)[0] === commit);
  const depsPin = extractDepsPin(readFileSync(join(root, "deps.edn"), "utf8"));
  const lockPin = extractLockPin(readFileSync(join(root, "deps-lock.edn"), "utf8"));
  const directory = mkdtempSync(join(tmpdir(), "kotoba-wasm-qualification-"));

  try {
    const alias = "wasm-qualification-candidate";
    const override = `{:aliases {:${alias} {:override-deps {${coordinate} {:local/root ${JSON.stringify(wasmRoot)}}}}}}`;
    const classpath = run("clojure", ["-Sdeps", override, `-A:${alias}`, "-Spath"]);
    const candidateSource = realpathSync(join(wasmRoot, "src"));
    const classpathVerified = classpath.split(delimiter)
      .map((entry) => realpathSync(entry))
      .includes(candidateSource);
    if (!classpathVerified) throw new Error(`candidate src is absent from classpath: ${candidateSource}`);

    const fixtures = [
      { name: "scalar", source: "scalar.kotoba", exportName: "mix",
        iterations: 1_000_000, warmup: 100_000, checksum: 2_318_261_108 },
      { name: "vector", source: "vector.kotoba", exportName: "vector-alloc",
        iterations: 256, warmup: 256, checksum: 7_560 },
      { name: "vectorBulk", source: "vector_escape.kotoba", exportName: "vector-escape",
        iterations: 256, warmup: 256, checksum: 7_560 },
    ];
    const artifacts = {};
    const executions = {};
    for (const fixture of fixtures) {
      const source = join(root, "benchmarks", "runtime", fixture.source);
      const jvmArtifact = join(directory, `${fixture.name}-jvm.wasm`);
      const nbbArtifact = join(directory, `${fixture.name}-nbb.wasm`);
      run("clojure", ["-Sdeps", override, `-M:${alias}:run`, "compile", source,
        "--target", "wasm32", "--output", jvmArtifact]);
      run("nbb", ["--classpath", classpath,
        join(root, "src", "kotoba", "compiler", "nbb", "wasm_cli.cljs"),
        "compile", source, "--target", "wasm32", "--output", nbbArtifact]);
      const jvmBytes = readFileSync(jvmArtifact);
      const nbbBytes = readFileSync(nbbArtifact);
      if (!jvmBytes.equals(nbbBytes)) {
        throw new Error(`${fixture.name} JVM and nbb candidate artifacts differ`);
      }
      run("wasm-tools", ["validate", jvmArtifact]);
      const execution = JSON.parse(run(process.execPath,
        [join(root, "benchmarks", "runtime", "wasm-runner.mjs"), jvmArtifact,
          fixture.exportName, "--steady", String(fixture.iterations), String(fixture.warmup)]));
      if (execution.checksum !== fixture.checksum
          || execution.iterations !== fixture.iterations
          || execution.warmupIterations !== fixture.warmup) {
        throw new Error(`${fixture.name} checksum contract failed: ${JSON.stringify(execution)}`);
      }
      artifacts[fixture.name] = {
        bytes: jvmBytes.length,
        sha256: createHash("sha256").update(jvmBytes).digest("hex"),
      };
      executions[fixture.name] = execution;
    }

    const checks = {
      classpathVerified,
      jvmNbbByteIdentical: true,
      wasmToolsValidated: true,
      scalarChecksumVerified: true,
      vectorChecksumVerified: true,
      vectorBulkChecksumVerified: true,
    };
    const state = promotionState({
      commit, dirty, depsPin, lockPin, remoteAdvertisesCommit,
      checksPassed: Object.values(checks).every(Boolean),
    });
    const report = {
      format: "kotoba.wasm-backend-qualification/v2",
      generatedAt: new Date().toISOString(),
      candidate: { root: wasmRoot, commit, dirty },
      publication: { checked: publicationChecked, remoteName, remoteUrl, remoteAdvertisesCommit },
      compiler: { depsPin, lockPin },
      artifacts,
      executions,
      checks,
      state,
    };
    const output = `${JSON.stringify(report, null, 2)}\n`;
    const outputPath = option(args, "--output");
    if (outputPath) writeFileSync(resolve(outputPath), output);
    process.stdout.write(output);

    if (args.includes("--require-clean") && !state.backendClean) {
      throw new Error("candidate backend is dirty");
    }
    if (args.includes("--require-pinned") && !state.compilerPinsHeadCommit) {
      throw new Error("deps.edn and deps-lock.edn do not both pin the candidate commit");
    }
    if (publicationChecked && !state.remoteAdvertisesCommit) {
      throw new Error("no advertised origin ref names the candidate commit");
    }
    return report;
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
}

if (process.argv[1] && pathToFileURL(resolve(process.argv[1])).href === import.meta.url) {
  try {
    main();
  } catch (error) {
    process.stderr.write(`${error.stack ?? error}\n`);
    process.exitCode = 1;
  }
}
