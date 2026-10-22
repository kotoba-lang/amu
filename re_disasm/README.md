# re-disasm — cleanroom AArch64 disassembler core (Kotoba / amu)

`disasm.kotoba` is the first slice of a Hopper/Ghidra/IDA alternative written
in the Mithril language (Kotoba, compiled by amu selfhost). It decodes A64
instruction words, computes branch and pc-relative targets, renders one
disassembly line, and does a bounded linear sweep with cross-reference
counting over a word vector.

## Cleanroom provenance

This code is cleanroom with respect to every existing disassembler and
decompiler:

- The encoding tables are transcribed from the **public Arm A64 ISA
  reference (Arm ARM)** — the instruction-set specification, which is a fact
  about the architecture, not a copyrightable expression.
- No disassembly output, source file, table, test vector or string from
  Ghidra, IDA, Hopper, radare2, Rizin, Binary Ninja, binutils/objdump,
  Capstone or LLVM was read, copied, paraphrased or "golden-tested" into
  this file.
- Every test expectation is **hand-computed from the spec encodings**. We do
  not validate against another tool's output, so no de-facto copying creeps
  in through test fixtures.
- No GPL/LGPL code is linked or transcribed (binutils/objdump is GPL-3,
  radare2/Rizin are LGPL-3). The file carries no third-party code at all,
  so the repository license covers it unencumbered.

See `docs/re-disasm-cleanroom.md` in this repository for the architecture,
license analysis (why cleanroom, what each alternative's license would
impose) and the milestone plan.

## Scope (M0 + M1)

- 31 A64 classes: nop, ret, br, blr, b, bl, b.cond, cbz/cbnz, tbz/tbnz,
  adr, adrp, movn, movz, movk, add/sub (immediate and shifted register,
  unflagged), and/orr/eor/ands (shifted register), ldr/str (unsigned
  immediate and register offset, integer), ldp/stp (64-bit, integer),
  svc, brk, hlt; everything else decodes as `class-unknown` rather than
  being guessed. Shifted-register shift rendering and load/store
  extend/shift operands are recorded but not yet printed.
- Field extractors per class (imm16, imm26/19/14 branch offsets, adr imm21,
  addsub imm12, ldr/str scaled offset, rm/rt2/imm6/shift type, ldp/stp
  scaled imm7, rd/rn/rt, cond, op).
- `insn-target` — computed branch / pc-relative target (ADRP uses the
  4 KiB page base).
- `insn-text` — one A64-syntax line, e.g. `ldr x0, [x1, #0x8]`,
  `b.eq #0xffc`, `str x0, [sp, #0x0]`, `ldp x0, x1, [sp, #0x10]`.
- `insn-record` — decoded record `[class rd rn rm imm6 target variant]`
  as a plain vector-i64.
- `words-from-bytes` — little-endian u32 word vector from a byte buffer
  (loader seed).
- `count-class` / `xrefs-count` / `targets-vector` — linear sweep
  histogram, bounded xrefs to one address, and the per-slot target edge
  list (the xrefs graph in two parallel vectors).
- `listing-text` — one `<pc>: <word>  <text>` line per word.

## Not yet (the Hopper replacement roadmap)

Mach-O/ELF/PE loaders, ADRP+ADD literal pools, recursive-descent
traversal, function boundaries, CFG, strings/imports, x86-64 decode,
decompiler, and a UI are all later milestones — see the design doc.
Nothing here reads a binary format yet; callers supply words.

## Build and test (JVM-free)

```sh
npm ci                              # nbb engine (org-babashka-nbb pin)
node bin/amu check re_disasm/disasm.kotoba
node bin/amu test re_disasm/disasm.kotoba --fuel 5000000
```

Measured 2026-10-19: `54/54 passed` on `[:jvm-kir :js :wasm]` (18 tests x
3 targets). The test harness runs every exported zero-arity `test-*`
(`docs/test-harness.md`).

## Native build and run (runtime: no JVM / GraalVM / Node)

```sh
npm run test-re-disasm          # guest suite: 54/54 on [:jvm-kir :js :wasm]
npm run test-re-disasm-native   # -> PASS (main returned 1)
```

The historical `test-re-disasm-native` driver (its old CI workflow is retired) runs
`re_disasm/build-native.mjs`, which compiles `disasm.kotoba` to the
host-native kexe target (`aarch64-macos-kotoba-v1` here, `--jvm-free`),
extracts `main`'s machine code, builds the reviewed C loader
(`tools/kexe_loader.c`) with `cc`, and runs the extracted code under it.
The loader is a standalone Mach-O arm64 binary that spawns no children and
reads no configuration — measured 2026-10-19 with an empty environment:

```sh
env -i .../re-disasm.loader .../re-disasm.bin 30232 0 aarch64 -   # -> 1
```

The runtime tree is cc + one Mach-O + machine code: no JVM, no GraalVM, no
Node.js. End-to-end semantics were A/B-checked: a build whose `main`
expects a wrong count prints `0`, the shipped one prints `1`.

The one remaining non-selfhost piece is the **compile door**: `bin/amu` is
still the node-hosted bootstrap compiler (`docs/selfhost-priority.md`;
`--jvm-free` proves no JVM is used, and the compile-time oracle
`:status :verified` attests the emitted semantics). When the selfhost-built
amu binary lands, phase 1 of `build-native.mjs` swaps to it and the entire
path is Node-free. `main` lives in this single module on purpose: the
:jvm-kir reference charges cross-module calls against its 32-frame budget,
and the oracle must be able to verify the entry.

## Language-surface notes (measured, not assumed)

Kotoba's compiler (kotoba-sema) and its test interpreter (kotoba-script /
osaho KIR reference) do not admit the same surface. This file deliberately
sticks to the interpreter's subset so `amu test` runs it:

- The interpreter has `bit-and` / `bit-xor` but **no `bit-or`, `bit-not`,
  `i64-shift-left`, `i64-shift-right`, `u64-shift-right`, `string-from-i64`,
  `not=`**. Work-arounds used here: `bor` (a+b-(a&b)), `quot` by 2^k for
  logical right shifts, `(* v 2^k)` for left shifts, `pow2`+`sext` as
  arithmetic sign extension, `dec-rec` for i64→decimal text.
- `string-substring` takes **byte offsets `(value, start, end)`**, not
  `(start, length)` — `(string-substring s i 1)` is empty for i>0 and traps
  for i>1.
- Module resolution munges namespace dashes to underscores:
  `(ns re_disasm.disasm)` lives at `re_disasm/disasm.kotoba`
  (`project_files/namespace-relative`).
- Cross-module calls through `(:require [.. :as d])` on the :jvm-kir
  reference add frames against `default-frames` 32 (osaho
  `kir.cljk`): a linked probe with a 40-iteration `loop` traps
  `budget/frames` while the same loop runs fine at 100 iterations in a
  single-module test file. Keep analysis loops single-module, or measure
  before relying on loop-heavy cross-module calls.
