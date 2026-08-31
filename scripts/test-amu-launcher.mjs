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

  // `--prelude` reaches only the CLJS backend. On every route this launcher
  // sends to nbb it changed nothing and still reported `:ok true`, so a
  // caller could believe `lang/stdlib/core.kotoba` was linked when it was
  // not. Refusing is the point; this asserts the refusal and, below, that
  // the same command without the flag is unaffected.
  const preludeRejected = spawnSync(process.execPath,
    [join(root, "bin", "amu"), "check", "examples/w1-pure.kotoba",
      "--prelude", "lang/stdlib/core.kotoba", "--jvm-free"],
    { cwd: root, encoding: "utf8", timeout: 120_000, maxBuffer: 16 * 1024 * 1024,
      env: { ...process.env, PATH: `${fakeBin}${delimiter}${process.env.PATH}` } });
  if (preludeRejected.error) throw preludeRejected.error;
  if (preludeRejected.status !== 64
      || !preludeRejected.stderr.includes("--prelude is not implemented on this route"))
    throw new Error(`--prelude did not fail closed\n${preludeRejected.stdout}${preludeRejected.stderr}`);
  if (existsSync(marker)) throw new Error("--prelude rejection invoked clojure");

  const preludeAbsent = spawnSync(process.execPath,
    [join(root, "bin", "amu"), "check", "examples/w1-pure.kotoba", "--jvm-free"],
    { cwd: root, encoding: "utf8", timeout: 120_000, maxBuffer: 16 * 1024 * 1024 });
  if (preludeAbsent.error) throw preludeAbsent.error;
  if (preludeAbsent.status !== 0 || !preludeAbsent.stdout.includes(":ok true"))
    throw new Error(`the prelude guard rejected a command that does not use it\n${preludeAbsent.stdout}${preludeAbsent.stderr}`);

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
  // A caller-relative path resolves against the CALLER's directory, not the Amu
  // checkout. Both spawns in bin/amu set `cwd: root`, so before this was fixed
  // the backend looked for the source inside Amu and reported
  // `:decode / "input could not be read"` -- "your file is malformed" for a
  // file it never opened. Run from a directory that is not the repository, with
  // a bare filename, which is the shape every consumer types.
  const elsewhere = mkdtempSync(join(tmpdir(), "amu-cwd-test-"));
  try {
    writeFileSync(join(elsewhere, "probe.kotoba"),
      "(ns probe.cwd (:export [main]))\n(defn main [] 7)\n");
    const relative = spawnSync(process.execPath,
      [join(root, "bin", "amu"), "compile", "probe.kotoba",
       "--target", "wasm32-browser", "--output", "out.wasm"],
      { cwd: elsewhere, encoding: "utf8", timeout: 180_000 });
    if (relative.status !== 0)
      throw new Error(`a caller-relative source was not found\n${relative.stdout}${relative.stderr}`);
    // The output is the caller's too: writing it into the Amu checkout would be
    // the same mistake pointed the other way.
    if (!existsSync(join(elsewhere, "out.wasm")))
      throw new Error("a caller-relative --output did not land in the caller's directory");
    if (existsSync(join(root, "out.wasm")))
      throw new Error("--output landed inside the Amu checkout");
  } finally {
    rmSync(elsewhere, { recursive: true, force: true });
  }
  process.stdout.write("amu-launcher: caller-relative source and output paths resolve against the caller\n");

  process.stdout.write("amu-launcher: direct and -M commands preserve native artifact/provenance parity\n");
  process.stdout.write("amu-launcher: --jvm-free compiles on nbb and rejects JVM-only routes\n");
} finally {
  rmSync(directory, { recursive: true, force: true });
}
