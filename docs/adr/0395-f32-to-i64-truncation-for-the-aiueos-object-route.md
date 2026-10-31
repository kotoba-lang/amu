# ADR-0395 -- f32 -> i64 truncation on the aiueos object route (JUN-633 slice 7)

- Status: **implemented** (seed/70 `xg-fun` code 37, seed/74 `xo-float-sir?`, `scripts/seed/check-aiueos-object-f2i.py`).
- Date: 2026-10-31
- Tracking: JUN-633 (slice 7): "Define rounding and out-of-range behaviour for f32→int explicitly".
- Follows: ADR 0391 (scalar SSE floats; this conversion was left refused there), ADR 0394.

## Context

The frontend already has the conversion. `f32-to-i64-truncating` (21-check head 805) is typed f32 -> i64 and lowers to
SIR `OP-UN` code 37 (`UOP-F32-TO-I64`). Its binary64 sibling `f64-to-i64-truncating` is code 32. Only the aarch64
backend emits them (seed/41 `gn-fl-un`), as `fcvtzs`. Every x86 route refused both with E7101.

ADR 0391 left the conversion out because the two ISAs disagree on everything outside the integer range:

| operand | x86 `cvttss2si r64` | aarch64 `fcvtzs x` |
|---|---|---|
| finite, in [-2^63, 2^63) | truncated toward zero | truncated toward zero |
| >= 2^63, +Inf | 0x8000000000000000 (the "integer indefinite") | INT64_MAX (saturates) |
| < -2^63, -Inf | 0x8000000000000000 | INT64_MIN |
| NaN (any payload) | 0x8000000000000000 | 0 |

The kernel C that the qwen35 objects replace, and kotoba code that converted from the bit pattern by hand, need only
the in-range answer. An out-of-range or NaN operand there is a bug upstream. A silent 0x8000000000000000 would turn
that bug into a plausible negative index or count.

## Decision

**Semantics.** `f32-to-i64-truncating x` on the x86_64-aiueos-kernel-v1 object artifact:

1. If x is finite and -2^63 <= x < 2^63, the answer is x truncated toward zero: the fraction is dropped. Examples:
   ±0, the denormals and (-1, 1) give 0; 2.5 gives 2; -2.5 gives -2; -2^63 gives INT64_MIN.
2. Otherwise the code traps: `ud2`, #UD. This covers every NaN (quiet or signalling, any sign or payload), ±Inf, and
   finite values with |x| >= 2^63 other than -2^63 itself. No value is returned.

The answer does not depend on MXCSR. cvttss2si always truncates. Its invalid-operation exception is masked at the
reset MXCSR the kernel runs with, and only sets the sticky IE flag. Neither changes the result.

**Shape: an emitted trap, not a checked result.** The route's other guards trap with `ud2` at the point of misuse:
- the fused dots' lengths, nulls and spans (ADR 0394);
- the kernel memory windows (ADR 0373);
- this route's `f32-from-bits` range check (ADR 0391).

A checked form, with a sentinel plus a flag the caller must branch on, would be the only operation on this route whose
failure is a value. Its sentinel would also have to be a legal i64, so a caller that forgets the branch is back to a
silent wrong integer. A caller that wants to handle an out-of-range operand can do so without the trap, since the
compares are admitted (ADR 0391): `(and (f32-ge x -2^63) (f32-lt x 2^63))` is false for NaN.

**Code (seed/70 `xg-fun`, code 37).** The operand is the f32 word in its slot (sign-extended, R6F). Only rax, rcx and
the flags are touched. No xmm register is used: the memory form of cvttss2si reads the slot directly.

```
f3 48 0f 2c 85 d32      cvttss2si rax, dword [rbp+d]
48 89 c1                mov  rcx, rax
48 f7 d9                neg  rcx                     ; OF = 1 exactly when rax = INT64_MIN
71 0e                   jno  ok
81 bd d32 00 00 00 df   cmp  dword [rbp+d], 0xdf000000   ; the one in-range f32 whose answer is INT64_MIN
74 02                   je   ok
0f 0b                   ud2
ok: 48 89 85 d32        mov  [rbp+d], rax
```

cvttss2si answers INT64_MIN for every operand of case 2, and for case 1 only at x = -2^63. The guard therefore keys
on the indefinite value itself, not on a range compare that could drift from the instruction's own boundary. The x86
object route never returns 0x8000000000000000 except as the true answer for -2^63.

**Admission (seed/74, the object artifact only).** `xo-float-sir?` admits `OP-UN` code 37 next to the slice 3 float
SIR. `xg-check-sir-at`, which every other x86 route uses, is unchanged, so those routes still refuse the conversion
(E7101 detail 37): x86_64-linux, the kernel image artifact, and the user and static routes. The emission is inline at
each use. An object that does not name the conversion gets no new byte, and the gate pins three such objects.

**Still refused (E7101):** `f64-to-i64-truncating` (code 32). Its guard is the same construction with cvttsd2si and
the f64 pattern 0xc3e0000000000000. It is left for a slice with its own evidence, because no consumer needs it yet.
`f32-min` / `f32-max` / `f64-min` / `f64-max` stay refused, as in ADR 0391.

## Relation to the aarch64 route

> **Amended 2026-10-31 (ADR 0398, owner decision on JUN-633: "Yes, align aarch64").** seed/41 now emits code 37
> with a guarded `fcvtzs` that traps with `brk #0` on exactly the operands this route traps on. The answers are
> bit-identical, and the cross-ISA differential hash matches. The paragraph below describes the state before
> that amendment.

The two routes agree on case 1: truncation toward zero, bit for bit. They do not agree on case 2. The aarch64 route
keeps `fcvtzs`'s saturating answers (INT64_MAX, INT64_MIN, 0 for NaN). This ADR does not change seed/41. A
program whose result depends on case 2 is therefore not portable between the routes, and on this route it stops
rather than continuing with a value. Making aarch64 trap as well would change every aarch64 object that uses the
conversion. That is a separate decision.

## Evidence

- `scripts/seed/check-aiueos-object-f2i.py`, wired into mac-selfhost-aiueos.yml, checks:
  - the guarded sequence exactly once, with both displacements naming the same slot, and no cvtss2si or cvttsd2si;
  - that slice 3's fops object, the pause object and the 512-byte width object keep their main 3d160442 SHA-256s;
  - the object-route refusals: two operands and no operand (E2103), an i64 operand (E2104), f64 -> i64 (E7101);
  - E7101 detail 37 on x86_64-linux and on the kernel image artifact.

  Against the previous root (main 3d160442), the gate is red: the object route refuses the conversion with E7101
  detail 37.
- `docs/evidence/f32-to-i64-20261031/` runs the object under QEMU TCG (`-cpu qemu64` and `-cpu max`). Each pass sets
  MXCSR twice: at its reset value, then with RC = round up. The run compares the object against `ref.c`, an
  integer-only C implementation of the semantics above.
  - The default run has 6,112,168 cases per CPU: named specials, the first and last eight mantissas of every
    exponent and sign, a stride-4099 sweep of all 2^32 patterns, and random patterns and in-range values. There are
    0 differences and 0 indefinite answers.
  - The exhaustive run covers every 2^32 pattern in both MXCSR passes: 8,589,951,142 cases per CPU, 0 differences.
  - Three mutants go red: rounding (cvtss2si), the guard skipped, and the -2^63 exemption moved.
- The derived pins are regenerated with `repin-derived-pins.py` (ADR 0388). The committed kotoba native-route
  objects recompile byte-identical.
