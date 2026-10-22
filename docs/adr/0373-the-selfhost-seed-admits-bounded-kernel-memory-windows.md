# 0373 — the selfhost seed admits bounded kernel memory windows

Date: 2026-10-22

## Status

Accepted for the first slice (u32 load, u32 store, subregion). The slice is
implemented as a change to the **selfhost x86 object backend only**, not to the
adopted core: the heads are not added to `seed/HEADS`, so `seed/MANIFEST` and
its sixteen adopted files are byte-identical, no adoption round is needed,
and `seed/compiler-core.json` is untouched. See "As built" below for how this
differs from the design first written here. The aiueos `:browser-component`
floor is not closed by this slice (CSSOM and the project-capable CLI remain).

## Context

Measured 2026-10-22 at amu `fae61b0e` (aiueos PR 443): the loaderless selfhost
compiler S3 (`selfhost-bootstrap.py` on arm64 Linux, S2=S3) compiles a scalar
probe for `x86_64-aiueos-kernel-v1` (ADR 0356), but refuses
`os/aiueos/kotoba/browser-frame2.kotoba` with `E2101` at its first
`(kernel-load-u32 (kernel-subregion s 8192 (* i 4) 4) 4 0)`. The
`kernel-load-*` / `kernel-store-*` / `kernel-subregion` family is defined
only in `src/kotoba/compiler/frontend_tables.kotoba`, outside the seed
closure (`seed/HEADS` has 41 heads, none of them kernel memory). Every
`os/aiueos/kotoba/browser-*.kotoba` object, and 116 `.o` files in all, were
built by `kotoba-compiler/1`, so none can be rebuilt by Amu selfhost.

The semantics already exist and are specified (docs/threat-model.md,
ADR 0240, ADR 0242): a window is a base (an i64 parameter or literal) plus a
length; every access is bounds-checked and traps (`UD2`) on violation;
`kernel-subregion` narrows with unsigned checks against the remainder so a
hostile pair cannot wrap; hand-written `(+ base offset)` in a base position
is refused; bases must be ROOTED (a literal, `kernel-boot-info`, or a
parameter). Nothing here needs a new first-class region *type*: a window is
two scalars at the object ABI (ADR 0356 already allows five scalar
parameters).

## Decision

Admit a **closed first slice** of the family into the seed, as new heads in
`seed/HEADS`, and nothing else from it:

1. `kernel-subregion base length offset sublen` -> i64 base.
2. `kernel-load-u32` / `kernel-store-u32` (`window length offset [value]`),
   then `u8`, `u16`, `u64` in a second step. The `-4k/-16k/-64k` static-bound
   variants wait until the plain forms are qualified.
3. Rooted-base admission in the checker: a base that is not a literal, a
   parameter, or the result of `kernel-subregion` over a rooted base is
   refused by name. Taint through call sites is a later step; the first
   slice refuses a base passed through a call.
4. Emission only on `x86_64-aiueos-kernel-v1` (and the object route of
   ADR 0356). Other targets refuse the heads by name, never ignore them.

Every access emits the check before the memory operation: length against the
op's static maximum, base against zero, offset against length, all unsigned,
`UD2` on violation. The fuel and frame rules of ADR 0356 are unchanged.

## Qualification (required before landing)

- Disassembly-derived encoding assertions for the check sequences, as ADR 0242
  does for the kotoba-native path, plus a negative control for each check
  (null base, offset == length, offset + sublen wrapping, negative offset),
  each seen to trap.
- G1 = G2 = G3 for the selfhost closure with the new heads, and the adopted
  AArch64 bootstrap unchanged or re-adopted through ADR 0370, whichever the
  edit of the shared `21-check.kotoba` requires. This is the cost of the
  change: `21-check.kotoba` is shared with `seed/MANIFEST`.
- Conformance: rebuild `browser-damage.kotoba` (175 lines, only
  `kernel-load-u32` / `kernel-store-u32` / `kernel-subregion`) with the
  selfhost compiler and compare its behaviour with the published `.o` on the
  oracle vectors in aiueos `verify-*` scripts. Only then `browser-frame2` and
  `browser-reduce`.

## Non-claims

- Not the kernel IMAGE route; not the entry allowlist or fuel-tier table.
- No rebuilt object has run in a kernel until an aiueos gate says so.
- `kernel-region-report` (the list of ABI boundaries and narrowings) is not
  ported by this slice; until it is, a rebuilt object does not replace the
  published one in aiueos.
- Not a claim that the entry window's length describes real memory; that
  remains the trusted ABI boundary named in the threat model.

## As built

The Decision above proposed three new heads in `seed/HEADS`. Reading the code
before writing it showed a cheaper, safer route with the same semantics and no
change to the adopted core:

- The three operations are **private library functions** (`kernel-load-u32`,
  `kernel-store-u32`, `kernel-subregion`) that the object route appends to the
  guest source (`xk-lib` in `seed/74-x86_64-aiueos-object.kotoba`), as it
  already appends the R6B source library. The shared frontend, checker and
  lowering see ordinary calls of ordinary `:i64` functions.
- The x86 backend replaces a call of those three stubs by inline code
  (`xk-intrinsic`, the way the static route replaces the `kxrt-` stubs). The
  byte sequences and displacements are kotoba-native's `emit-kernel-load-u32`,
  `emit-kernel-store-u32` and `emit-kernel-subregion`; the displacement sets
  (+36/+27/+18/+5 and +27/+18/+6) match that file's own comments.
- **Rooted bases** are enforced on the SIR the backend already reads (`xk-check`):
  the base operand's last writer is found in straight-line code (a label or jump
  in between refuses) and must be a literal, a parameter that is never assigned,
  a `kernel-subregion` of a rooted base, or a let-bound local with one
  assignment of a rooted value. Everything else is E7106. Thirteen cases in
  `seed/tests/kernel-memory/` (six accepted, seven refused: a base read from
  memory, arithmetic, a call result, a branch, a computed let, a loop variable,
  a subregion of arithmetic).
- Only `x86_64-aiueos-kernel-v1` has the library; other targets are unchanged
  (M[200] stays 0), so a program that uses these names there is the same
  "unknown function" it was.

### Measured

`scripts/seed/check-kernel-memory.py` (arm64 Linux, the selfhost-built
compiler): the three emitted routines run in an emulator of exactly the
instruction forms the backend emits, 12,380 runs over boundary and random
values, zero deviations from the specification (every access inside the
window, every trap before any access). Eleven single-condition mutants of the
emitted checks (ja, jae, jz in each routine, the second ja where there is one)
are each seen red. One first-choice mutant (`jae` to `ja` in load) turned out
to be equivalent -- the later `index + 4 <= length` check traps the same case --
and was replaced by `jae` to `jb`, which is not.

`os/aiueos/kotoba/browser-damage.kotoba`, with its export renamed to the C symbol
(`kotoba_aiueos_browser_damage`) and `main` dropped from the export list (the
object route admits exactly one export), is compiled by the selfhost compiler
(14,714 text bytes; `verify-kotoba-kernel-object.py` accepts it), linked into
KERNEL.ELF in place of the `kotoba-compiler/1` object, and
`guest-browser-damage` exits 0 on QEMU with the same census, the same damage
bytes and screendumps identical to the whole-screen ones. That is the first
aiueos kernel object whose code was produced by Amu selfhost and ran in the
kernel gate.

### Still open

- The other `browser-*.kotoba` objects are not yet built by selfhost (they need
  the same one-export form, and some use the other `kernel-*` operations: u8,
  u16, u64, the 4k/16k/64k tiers, atomics).
- The shipped `browser-damage.o` is still the `kotoba-compiler/1` object; the
  selfhost one was linked for the experiment only. Replacing it is an aiueos
  change (pin, provenance, a source with one export).
- `kernel-region-report` is not ported.
- The `:browser-component` floor needs the whole Browser/CSSOM graph; the
  project-capable native CLI is still missing (JUN-137).

