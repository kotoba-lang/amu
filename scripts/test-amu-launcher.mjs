#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import {
  chmodSync, copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { delimiter, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const directory = mkdtempSync(join(tmpdir(), "amu-launcher-test-"));
try {
  const report = join(directory, "report.json");
  const comparison = spawnSync(process.execPath,
    [join(root, "scripts", "launcher-comparison.mjs"), "--runs", "1", "--output", report],
    { cwd: root, encoding: "utf8", timeout: 180_000, maxBuffer: 16 * 1024 * 1024 });
  if (comparison.error) throw comparison.error;
  if (comparison.status !== 0)
    throw new Error(`launcher comparison failed\n${comparison.stdout}${comparison.stderr}`);
  const evidence = JSON.parse(readFileSync(report, "utf8"));
  if (evidence.format !== "amu.launcher-comparison/v1" || evidence.runs !== 1
      || !evidence.parity.artifactSha256 || !evidence.parity.provenanceSha256)
    throw new Error("launcher parity evidence is incomplete");

  const aliasOutput = join(directory, "alias.wasm");
  const alias = spawnSync(process.execPath,
    [join(root, "bin", "amu"), "-M", "compile", "examples/w1-pure.kotoba",
      "--target", "wasm32", "--output", aliasOutput],
    { cwd: root, encoding: "utf8", timeout: 120_000, maxBuffer: 16 * 1024 * 1024 });
  if (alias.error) throw alias.error;
  if (alias.status !== 0 || !alias.stdout.includes(":ok true"))
    throw new Error(`-M compatibility failed\n${alias.stdout}${alias.stderr}`);

  const jvmFreeOutput = join(directory, "jvm-free.wasm");
  const jvmFree = spawnSync(process.execPath,
    [join(root, "bin", "amu"), "compile", "examples/w1-pure.kotoba",
      "--target", "wasm32", "--jvm-free", "--output", jvmFreeOutput],
    { cwd: root, encoding: "utf8", timeout: 120_000, maxBuffer: 16 * 1024 * 1024 });
  if (jvmFree.error) throw jvmFree.error;
  if (jvmFree.status !== 0 || !jvmFree.stdout.includes(":ok true"))
    throw new Error(`--jvm-free compile failed\n${jvmFree.stdout}${jvmFree.stderr}`);

  const fakeBin = join(directory, "fake-bin");
  const marker = join(directory, "clojure-invoked");
  mkdirSync(fakeBin);
  const fakeClojure = join(fakeBin, "clojure");
  writeFileSync(fakeClojure, `#!/bin/sh\ntouch '${marker}'\nexit 99\n`);
  chmodSync(fakeClojure, 0o755);
  const rejected = spawnSync(process.execPath,
    [join(root, "bin", "amu"), "compile", "examples/w1-pure.kotoba",
      "--source-path", "examples", "--unpinned", "--target", "wasm32",
      "--jvm-free", "--output", join(directory, "forbidden.wasm")],
    { cwd: root, encoding: "utf8", timeout: 120_000, maxBuffer: 16 * 1024 * 1024,
      env: { ...process.env, PATH: `${fakeBin}${delimiter}${process.env.PATH}` } });
  if (rejected.error) throw rejected.error;
  if (rejected.status !== 64
      || !rejected.stderr.includes("refusing to invoke the Clojure/JVM compatibility path"))
    throw new Error(`--jvm-free did not fail closed\n${rejected.stdout}${rejected.stderr}`);
  if (existsSync(marker)) throw new Error("--jvm-free invoked clojure");

  const locklessRoot = join(directory, "lockless-amu");
  mkdirSync(join(locklessRoot, "bin"), { recursive: true });
  copyFileSync(join(root, "bin", "amu"), join(locklessRoot, "bin", "amu"));
  writeFileSync(join(locklessRoot, "deps.edn"), "{}\n");
  const lockless = spawnSync(process.execPath,
    [join(locklessRoot, "bin", "amu"), "check", "component.cljk", "--jvm-free"],
    { cwd: locklessRoot, encoding: "utf8", timeout: 120_000, maxBuffer: 16 * 1024 * 1024,
      env: { ...process.env, PATH: `${fakeBin}${delimiter}${process.env.PATH}` } });
  if (lockless.error) throw lockless.error;
  if (lockless.status !== 70
      || !lockless.stderr.includes("JVM fallback is forbidden"))
    throw new Error(`--jvm-free accepted a missing dependency lock\n${lockless.stdout}${lockless.stderr}`);
  if (existsSync(marker)) throw new Error("--jvm-free lock failure invoked clojure");
  process.stdout.write("amu-launcher: direct and -M commands preserve native artifact/provenance parity\n");
  process.stdout.write("amu-launcher: --jvm-free compiles on nbb and rejects JVM-only routes\n");
} finally {
  rmSync(directory, { recursive: true, force: true });
}
