#!/usr/bin/env node
// Build re-disasm as a native program and run its checks with NO JVM,
// GraalVM or Node.js in the runtime tree.
//
//   node re_disasm/build-native.mjs [output-prefix]
//
// Default output prefix is a fresh mkdtemp under os.tmpdir().
//
// Phase 1 is the COMPILE DOOR: `bin/amu` is still the node-hosted bootstrap
// compiler (docs/selfhost-priority.md). `--jvm-free` proves no JVM is used;
// Node is used only here. When the selfhost-built amu binary lands, phase 1
// swaps to it and the whole script is Node-free too.
//
// Phases 2 and 3 are pure: cc builds the reviewed C loader
// (tools/kexe_loader.c), and the loader executes the extracted machine code
// as a standalone native process (it spawns no children and reads no
// configuration).
//
// This file is Node (not POSIX shell) on purpose: scripts/check-workflows.cljk
// refuses `.sh` execution files in this repository.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const out = process.argv[2]
  || path.join(fs.mkdtempSync(path.join(os.tmpdir(), "re-disasm-")), "re-disasm");
fs.mkdirSync(path.dirname(out), { recursive: true });

function run(cmd, args) {
  const r = spawnSync(cmd, args, { encoding: "utf8", cwd: root });
  if (r.status !== 0) {
    process.stderr.write(`${cmd} ${args.join(" ")}\n${r.stdout || ""}${r.stderr || ""}\n`);
    process.exit(r.status === null ? 1 : r.status);
  }
  return r.stdout || "";
}

// Phase 1 -- compile + extract (bootstrap door; --jvm-free, no JVM).
// --target is explicit: the compiler's default program target is now
// Kototama (upstream), which refuses kexe emission. The machine-code
// target is named after the host.
const osTag = process.platform === "darwin" ? "macos"
  : process.platform === "linux" ? "linux" : null;
const archTag = process.arch === "arm64" ? "aarch64"
  : process.arch === "x64" ? "x86_64" : null;
if (!osTag || !archTag) {
  console.error(`unsupported host: ${process.platform}/${process.arch}`);
  process.exit(1);
}
run(process.execPath, ["bin/amu", "compile", "re_disasm/disasm.kotoba",
  "--jvm-free", "--target", `${archTag}-${osTag}`, "--output", `${out}.kexe`]);
const extract = run(process.execPath, ["bin/amu", "extract-native", `${out}.kexe`,
  "--symbol", "main", "--output", `${out}.bin`]);
const offset = Number((extract.match(/:offset (\d+)/) || [])[1]);
if (!Number.isInteger(offset)) {
  console.error(`extract-native did not report :offset -- ${extract}`);
  process.exit(1);
}

// Phase 2 -- reviewed C loader (cc only).
run("cc", ["-O2", "-o", `${out}.loader`, "tools/kexe_loader.c"]);

// Phase 3 -- run: the loader prints main's i64 result; 1 = all checks pass.
const arch = archTag;
const result = run(`${out}.loader`, [`${out}.bin`, String(offset), "0", arch, "-"]).trim();
if (result === "1") {
  console.log("re-disasm native checks: PASS (main returned 1)");
} else {
  console.error(`re-disasm native checks: FAIL (main returned ${result})`);
  process.exit(1);
}
