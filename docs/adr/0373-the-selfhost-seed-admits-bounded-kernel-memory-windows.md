# 0373 — the selfhost seed admits bounded kernel memory windows

Date: 2026-10-22

## Status

Proposed. **Design only; no seed change in this ADR.** It touches the adopted
compiler core, so it follows the ADR 0370 review order and needs its own
change with a full self-rebuild and conformance run. It is written to
unblock the aiueos `:browser-component` floor and every other kernel object
that is still built by `kotoba-compiler/1`.

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
