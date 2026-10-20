#!/usr/bin/env node
// re_disasm/cli-smoke.mjs — smoke test for bin/re-disasm (KOT-49 slice 1).
//
// Builds the three hand-assembled container fixtures through the compiled
// Kotoba module (re_disasm/disasm.kotoba, js target), runs the CLI on each,
// and asserts the expected facts appear in its output. No external tool's
// output is an expectation here either — the fixtures and every expected
// line come from the same cleanroom sources as the guest tests.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "re-disasm-cli-"));
const esm = path.join(dir, "disasm.mjs");

const build = spawnSync(process.execPath, ["bin/amu", "compile", "re_disasm/disasm.kotoba",
  "--jvm-free", "--target", "js", "--output", esm], { encoding: "utf8", cwd: root });
if (build.status !== 0) {
  process.stderr.write(`compile failed\n${build.stdout || ""}${build.stderr || ""}\n`);
  process.exit(1);
}
const { instantiateKotoba } = await import(pathToFileURL(esm).href);
const api = instantiateKotoba({}, { fuel: 2 ** 48, frames: 1000000, bytes: 2 ** 48 });

for (const [name, fn] of [["macho", "macho-fixture"], ["elf", "elf-fixture"], ["pe", "pe-fixture"]]) {
  fs.writeFileSync(path.join(dir, `${name}.bin`), Buffer.from(api[fn]()));
}

function run(file, args) {
  const r = spawnSync(process.execPath, ["bin/re-disasm", path.join(dir, file), ...args],
    { encoding: "utf8", cwd: root });
  if (r.status !== 0) {
    process.stderr.write(`re-disasm ${file} failed\n${r.stdout || ""}${r.stderr || ""}\n`);
    process.exit(1);
  }
  return r.stdout;
}

const cases = [
  ["macho.bin", ["--all"], [
    "format: macho64", "entry: 0x1000001a0",
    "symbol: 0x1000001a0 _main",
    "bl #0x1000001a8", "ret",
    "0x1000001a0 -> 0x1000001a8",
  ]],
  ["elf.bin", ["--sections", "--symbols", "--imports"], [
    "format: elf64", "entry: 0x1000",
    ".text vaddr=0x1000 off=0x1a0 size=0x10",
    "symbol: 0x1000 _start",
  ]],
  ["pe.bin", ["--sections", "--symbols", "--listing", "--max", "2"], [
    "format: pe32+", "entry: 0x140001000",
    ".text vaddr=0x140001000 off=0x1b0 size=0x10",
    "nop", "ret",
  ]],
];

let checked = 0;
for (const [file, args, expects] of cases) {
  const outText = run(file, args);
  for (const want of expects) {
    if (!outText.includes(want)) {
      process.stderr.write(`cli-smoke: ${file}: missing ${JSON.stringify(want)}\n--- output ---\n${outText}\n`);
      process.exit(1);
    }
    checked++;
  }
}
console.log(`re-disasm cli-smoke: PASS (${checked} expectations across 3 fixtures)`);
