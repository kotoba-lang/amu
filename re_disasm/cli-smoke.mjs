#!/usr/bin/env node
// re_disasm/cli-smoke.mjs — smoke test for bin/re-disasm (KOT-49 slice 1).
//
// Builds the three hand-assembled container fixtures through the compiled
// Kotoba module (re_disasm/disasm.kotoba, js target), runs the CLI on each,
// and asserts the expected facts appear in its output. No external tool's
// output is an expectation here either — the fixtures and every expected
// line come from the same cleanroom sources as the guest tests. The tail
// cases cover the CLI review fixes: --arch x64 listings, ABI-bounded
// container/strings/listing windows, entry-seeded analysis and the mach-o
// load-command bounds check.
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

// the CLI must refuse this invocation; the message must carry `want`
function runFail(file, args, want) {
  const r = spawnSync(process.execPath, ["bin/re-disasm", path.join(dir, file), ...args],
    { encoding: "utf8", cwd: root });
  if (r.status === 0) {
    process.stderr.write(`re-disasm ${file} ${args.join(" ")} unexpectedly succeeded\n${r.stdout || ""}\n`);
    process.exit(1);
  }
  if (!(r.stderr || "").includes(want)) {
    process.stderr.write(`re-disasm ${file}: refusal lacks ${JSON.stringify(want)}\n${r.stderr || ""}\n`);
    process.exit(1);
  }
}

// x64 blob: nop ; ret (cleanroom field document: 0x90 nop, 0xC3 ret)
fs.writeFileSync(path.join(dir, "x64.bin"), Buffer.from([0x90, 0xc3]));

// a blob with a string past the 8 KiB window boundary (12000 = 0x2ee0)
const big = Buffer.alloc(20000);
big.write("HELLO-REDISASM", 12000, "latin1");
fs.writeFileSync(path.join(dir, "big.bin"), big);

// 4096 a64 nop words (0xD503201F): a listing of 4096 lines exceeds the
// 65,536-byte exported-string cap, so it only reports through chunking
const nops = Buffer.alloc(4096 * 4);
for (let i = 0; i < 4096; i++) nops.writeUInt32LE(0xd503201f, i * 4);
fs.writeFileSync(path.join(dir, "nops.bin"), nops);

// a mach-o header claiming four billion load commands
const bad = Buffer.alloc(64);
bad.writeUInt32LE(0xfeedfacf, 0);
bad.writeUInt32LE(0xffffffff, 16);
fs.writeFileSync(path.join(dir, "badmacho.bin"), bad);

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
  ["macho.bin", ["--all", "--json"], [
    '"format": "macho64"', '"entry": "0x1000001a0"',
    '"name": "_main"', '"from": "0x1000001a0",', '"to": "0x1000001a8"',
  ]],
  // --arch x64 listings come from x86disasm.kotoba, not the a64 core
  ["x64.bin", ["--raw", "--arch", "x64", "--listing"], ["listing:", "nop", "ret"]],
  // string scanning is windowed at 8 KiB with file-relative offsets
  ["big.bin", ["--raw", "--strings"], ['0x2ee0 "HELLO-REDISASM"']],
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

// chunked listings: 4096 requested lines must all be reported
const nopsOut = run("nops.bin", ["--raw", "--listing", "--max", "4096"]);
const nopsLines = nopsOut.split("\n").filter((l) => l.includes("nop")).length;
if (nopsLines < 4096) {
  process.stderr.write(`cli-smoke: nops.bin: chunked listing reported ${nopsLines} nop lines\n`);
  process.exit(1);
}
checked++;

// refusals: unbounded mach-o headers and a64-only views under --arch x64
runFail("badmacho.bin", ["--sections"], "bounds check");
runFail("x64.bin", ["--raw", "--arch", "x64", "--functions"], "a64-only");
checked += 2;

console.log(`re-disasm cli-smoke: PASS (${checked} expectations across 5 fixtures)`);
