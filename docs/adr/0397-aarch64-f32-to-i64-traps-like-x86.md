# ADR-0397 -- aarch64 f32 -> i64 truncation traps as on x86 (JUN-633)

- Status: **implemented** (seed/41 `gn-fl-f32-to-i64`, `scripts/seed/check-a64-f2i.py`).
- Date: 2026-10-31
- Owner decision: 2026-10-31, JUN-633: "Yes, align aarch64". The aarch64 route takes ADR 0395's semantics bit for
  bit. The owner accepts that existing aarch64 objects that use the conversion change.
- Amends: ADR 0395, "Relation to the aarch64 route".

## Context

ADR 0395 defined `f32-to-i64-truncating` (SIR `OP-UN` code 37) on the x86 object route:
- truncation toward zero, for x finite with -2^63 <= x < 2^63;
- a trap for everything else: every NaN, ±Inf, and |x| >= 2^63 other than -2^63 itself.

It left the aarch64 route alone. The only aarch64 emitter of code 37 is seed/41 `gn-fl-un`, which emitted a bare
`fcvtzs xD, s0`. That instruction saturates: NaN gives 0, values >= 2^63 and +Inf give INT64_MAX, values < -2^63 and
-Inf give INT64_MIN. The two ISAs therefore disagreed on every case-2 operand.

Where code 37 reaches aarch64 code:
- **seed/41, the adopted core's backend.** It serves `--target aarch64-macos`, which is the payload route:
  - the Mac root and CLI compile through it;
  - `extract-native` cuts payloads out of it;
  - the packed `aarch64-linux` runner payloads and the R-aarch64 runner (`selfhost-float-cases.py`) run its output.
- **seed/80 (`--target aarch64-linux` static/runner/launcher) and the kototama aarch64 profiles (seed/83-85).** These
  run the x86 route's admission, `xg-check-sir`, which refuses code 37 with E7101 detail 37. They have no float
  emitter, so they are unchanged.
- **seed/preserved-20261012/41-a64gen.kotoba.** A historical preserved closure, not built by any current route. It is
  left unchanged.

## Decision

seed/41 emits code 37 as a guarded sequence:

```
fmov   s0, wX                 ; the operand's f32 word
movz   xD, #0xdf00, lsl #16   ; -2^63 as f32 (0xdf000000); D, the destination, is the scratch register
fmov   s1, wD
fcmp   s0, s1
b.lt   trap                   ; x < -2^63, or unordered (NaN): N != V
fneg   s1, s1                 ; +2^63
fcmp   s1, s0
b.gt   ok                     ; 2^63 > x, ordered
trap:  brk #0
ok:    fcvtzs xD, s0          ; in range: truncation toward zero
```

- **Bounds.** -2^63 is inclusive and 2^63 exclusive, both exact in binary32. Both compares are ordered tests, so a NaN
  can never reach `fcvtzs`. In range, `fcvtzs` is exact truncation, so the answers are bit-identical to x86's
  `cvttss2si`. -2^63 gives INT64_MIN, and no other operand does.
- **Independent of FPCR.** `fcvtzs` always rounds toward zero. `fcmp` against ±2^63 is unaffected by RMode. With
  FPCR.FZ, a denormal compares as 0 and truncates to 0, which is the same answer.
- **Trap convention.** `brk #0`, the convention seed/SIR `:traps` gives for every trap on this route ("brk #0 for
  every trap"): `quot`, fuel, `OP-TRAP`. The inline runtime handle checks use `udf #0`; this is an arithmetic guard
  like `quot`, not a handle check. A packaged Mac program dies with SIGTRAP.
- **Registers.** Only s0, s1, the destination register and the flags are touched. The operand register is consumed
  by the first `fmov`, so D may equal X. seed/41's other float operations already use d0/d1 as scratch.
- **Emission is inline at each use.** Code generation for a program that does not name the conversion is unchanged.
  The gate pins nine float payloads and the f64 one by their main SHA-256.

**Unchanged: `f64-to-i64-truncating` (code 32).** ADR 0395 does not cover it: x86 still refuses it with E7101. On
aarch64 it stays a bare `fcvtzs xD, dN`, which saturates (NaN 0, out of range INT64_MIN / INT64_MAX). The gate checks
that it is still the single unguarded `fcvtzs xD, dN`. Aligning it is left to the f64 slice that ADR 0395 names.

## Consequences

- A program whose result depends on a case-2 operand now stops on both ISAs instead of continuing on aarch64 with a
  saturated value. This is the accepted break for existing aarch64 objects that use the conversion.
- seed/41 is in the adopted 18-module core. This change therefore takes a core adoption round:
  `seed/adoption-jun633-a64-f2i-20261031.json` (Mac G1=G2=G3), `compiler-core.json`, the CDCI core pins and the amu
  selfhost gate pin. After that the derived pins are regenerated (ADR 0388).

## Evidence

- `scripts/seed/check-a64-f2i.py`, wired into mac-selfhost-aiueos.yml, checks the following on Mac arm64:
  - the guarded sequence, once per use: one for a single conversion, two for a function with two;
  - no other single-precision `fcvtzs`;
  - that f64 -> i64 is unchanged;
  - that ten payloads that do not use the conversion keep their main SHA-256s;
  - packaged, signed native programs: 18 in-range operands give the reference answers, and 13 NaN / Inf /
    out-of-range operands each die by SIGTRAP with no output.

  On the main root the gate is red: there is no guard, and a NaN program exits 0.
- `docs/evidence/f32-to-i64-a64-20261031/` runs the payload natively on the Apple M1 Max and on Linux arm64 in the
  local podman machine. It compares against the same integer-only `ref.c` and the same case list as the x86 run, in
  two FPCR rounding modes:
  - **Default run.** 6,112,168 cases, 0 differences, hash `360b024beaa801d5`, the same hash as the x86 QEMU run.
  - **Exhaustive run.** Every 2^32 pattern; the counts and hash are in that README.
  - **Mutants.** Each goes red: guard removed, rounding `fcvtns`, and the -2^63 bound made exclusive.
