#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import {
  chmodSync, copyFileSync, existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync,
  rmSync, writeFileSync,
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
  // --module-lock used to be refused here, and the refusal was right while
  // its resolver was JVM-only: serving a lock-pinned build from the PATH
  // resolver would have dropped the pinning silently. Now both halves run on
  // Node -- producing the lock and consuming it -- so the claim to assert is
  // the opposite one, and the marker check is what makes it a claim at all:
  // without it, "exit 0 through the JVM" and "exit 0 without one" are the
  // same assertion.
  //
  // `--blocks blocks` is deliberately RELATIVE and this runs from the
  // caller's directory. A directory name has no separator and no extension,
  // so it used to survive resolveCallerPaths untouched and then be resolved
  // against the Amu checkout by the spawn's `cwd: root`.
  const pinnedRoot = join(directory, "pinned");
  mkdirSync(join(pinnedRoot, "src"), { recursive: true });
  writeFileSync(join(pinnedRoot, "src", "util.cljk"),
    "(ns util (:export [twice]))\n(defn twice [x :i64] :i64 (* 2 x))\n");
  writeFileSync(join(pinnedRoot, "src", "main.cljk"),
    "(ns main (:require [util :as u]) (:export [run]))\n"
    + "(defn run [x :i64] :i64 (+ 1 (u/twice x)))\n");
  const pinnedEnv = { cwd: pinnedRoot, encoding: "utf8", timeout: 120_000,
    maxBuffer: 16 * 1024 * 1024,
    env: { ...process.env, PATH: `${fakeBin}${delimiter}${process.env.PATH}` } };

  const pinning = spawnSync(process.execPath,
    [join(root, "bin", "amu"), "module-lock", "src/main.cljk",
      "--source-path", "src", "--blocks", "blocks",
      "--output", "lock.edn", "--jvm-free"], pinnedEnv);
  if (pinning.error) throw pinning.error;
  if (pinning.status !== 0 || !pinning.stdout.includes(":ok true"))
    throw new Error(`module-lock --jvm-free failed\n${pinning.stdout}${pinning.stderr}`);
  if (existsSync(marker)) throw new Error("module-lock --jvm-free invoked clojure");
  if (!existsSync(join(pinnedRoot, "lock.edn")) || !existsSync(join(pinnedRoot, "blocks")))
    throw new Error("module-lock wrote its lock or blocks outside the caller's directory");
  const lockCid = /:lock-cid "([a-z0-9]+)"/.exec(pinning.stdout);
  if (!lockCid) throw new Error(`module-lock did not report a lock CID\n${pinning.stdout}`);

  const pinnedOutput = join(pinnedRoot, "pinned.wasm");
  const pinned = spawnSync(process.execPath,
    [join(root, "bin", "amu"), "compile", "--module-lock", "lock.edn",
      "--blocks", "blocks", "--target", "wasm32",
      "--jvm-free", "--output", pinnedOutput], pinnedEnv);
  if (pinned.error) throw pinned.error;
  if (pinned.status !== 0 || !pinned.stdout.includes(":ok true"))
    throw new Error(`--module-lock --jvm-free failed\n${pinned.stdout}${pinned.stderr}`);
  if (existsSync(marker)) throw new Error("--module-lock --jvm-free invoked clojure");
  // The build says HOW its inputs were found, and names the identity of the
  // pinned input set. A pinned build that cannot be told apart from an
  // unpinned one afterwards has not delivered what the lock is for.
  if (!pinned.stdout.includes(":kotoba.compile/inputs :module-lock")
      || !pinned.stdout.includes(lockCid[1]))
    throw new Error(`a pinned build did not report its pinning\n${pinned.stdout}`);

  const pinnedInstance = await WebAssembly.instantiate(readFileSync(pinnedOutput), {});
  if (pinnedInstance.instance.exports.run(5n) !== 11n)
    throw new Error(`pinned project computed ${pinnedInstance.instance.exports.run(5n)}, expected 11n`);

  // The refusal the lock exists for, on this route: a block whose bytes do
  // not hash to the CID they are filed under. Same filename, different bytes
  // -- the only thing between this and a silently different build is the
  // hash check. 65 is "your input is wrong", not 70 ("the compiler broke").
  const blockNames = readdirSync(join(pinnedRoot, "blocks"));
  writeFileSync(join(pinnedRoot, "blocks", blockNames[0]),
    "(ns util (:export [twice]))\n(defn twice [x :i64] :i64 (* 3 x))\n");
  const tampered = spawnSync(process.execPath,
    [join(root, "bin", "amu"), "compile", "--module-lock", "lock.edn",
      "--blocks", "blocks", "--target", "wasm32",
      "--jvm-free", "--output", join(pinnedRoot, "tampered.wasm")], pinnedEnv);
  if (tampered.error) throw tampered.error;
  if (tampered.status !== 65
      || !tampered.stderr.includes("locked module block does not hash to its CID"))
    throw new Error(`a tampered block was not refused\n${tampered.stdout}${tampered.stderr}`);
  if (existsSync(marker)) throw new Error("the tampered-block refusal invoked clojure");
  if (existsSync(join(pinnedRoot, "tampered.wasm")))
    throw new Error("a refused build still wrote an artifact");

  // A lock with nowhere to read blocks from is a usage error, not a search.
  const blockless = spawnSync(process.execPath,
    [join(root, "bin", "amu"), "compile", "--module-lock", "lock.edn",
      "--target", "wasm32", "--jvm-free",
      "--output", join(pinnedRoot, "blockless.wasm")], pinnedEnv);
  if (blockless.error) throw blockless.error;
  if (blockless.status !== 64
      || !blockless.stderr.includes("--module-lock requires --blocks <dir>"))
    throw new Error(`--module-lock without --blocks was not refused\n${blockless.stdout}${blockless.stderr}`);
  if (existsSync(marker)) throw new Error("the missing-blocks refusal invoked clojure");

  // --source-path no longer forces the JVM. This is the half a .cljc port
  // needs, since a component that declares (:require ...) is a project, and
  // until the Node resolver landed every such build had to be flattened into
  // one namespace or leave the JDK-free route.
  //
  // The marker check is the load-bearing half of this case: without it,
  // "exit 0 through the JVM" and "exit 0 without one" are the same assertion.
  const projectRoot = join(directory, "project");
  mkdirSync(projectRoot);
  writeFileSync(join(projectRoot, "util.cljk"),
    "(ns util (:export [twice]))\n(defn twice [x :i64] :i64 (* 2 x))\n");
  writeFileSync(join(projectRoot, "main.cljk"),
    "(ns main (:require [util :as u]) (:export [run]))\n"
    + "(defn run [x :i64] :i64 (+ 1 (u/twice x)))\n");
  const projectOutput = join(directory, "project.wasm");
  const linked = spawnSync(process.execPath,
    [join(root, "bin", "amu"), "compile", join(projectRoot, "main.cljk"),
      "--source-path", projectRoot, "--target", "wasm32",
      "--jvm-free", "--output", projectOutput],
    { cwd: root, encoding: "utf8", timeout: 120_000, maxBuffer: 16 * 1024 * 1024,
      env: { ...process.env, PATH: `${fakeBin}${delimiter}${process.env.PATH}` } });
  if (linked.error) throw linked.error;
  if (linked.status !== 0 || !linked.stdout.includes(":ok true"))
    throw new Error(`--source-path --jvm-free failed\n${linked.stdout}${linked.stderr}`);
  if (existsSync(marker)) throw new Error("--source-path --jvm-free invoked clojure");

  // And that the OTHER module is what ran, not an entry module admitted alone.
  const linkedBytes = readFileSync(projectOutput);
  const { instance } = await WebAssembly.instantiate(linkedBytes, {});
  if (instance.exports.run(5n) !== 11n)
    throw new Error(`linked project computed ${instance.exports.run(5n)}, expected 11n`);

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
  process.stdout.write("amu-launcher: --module-lock is produced and consumed without a JVM, and refuses a block that does not hash to its CID\n");
} finally {
  rmSync(directory, { recursive: true, force: true });
}
