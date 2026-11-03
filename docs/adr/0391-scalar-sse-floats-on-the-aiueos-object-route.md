# ADR-0391 -- scalar SSE floats on the aiueos object route (JUN-633 slice 3)

- Status: **implemented** (seed/70 `xg-fbin` / `xg-fcmp` / `xg-fun`, seed/74 `xo-check-sir`, `scripts/seed/check-aiueos-object-f32.py`).
- Date: 2026-10-30
- Tracking: JUN-633 (slice 3). Owner decision 2026-10-30: add native f32 rather than keep the qwen35 objects on kotoba-compiler/1.
- Follows: ADR 0389, ADR 0390.

## Context

The committed `qwen35-*.o` objects in kotoba-lang/kotoba record `:builder :kotoba-compiler/v1`. The native Mac root cannot rebuild them, and `select_output_token`'s argmax cannot move off C: the x86_64 object route refuses every float operation. A probe with `f32-gt` / `f32-add` failed with E7102 at the type check.

The frontend already has the operations. 21-check types the 36 float heads (rung r6j), and 30-lower turns them into SIR BOP-F*, CC-F*, UOP-F*. A float is its IEEE-754 bit pattern in an i64 (R6C / R6F): an f64 its 64 bits, an f32 its 32 bits sign-extended. Only the aarch64 backend (seed/41) emits them; every x86 route refuses them before code generation.

## Decision

**Code generation (seed/70).** The x86 codegen gains scalar SSE for the float SIR codes. Operands are read from their stack slots (`[rbp+disp32]`). The result leaves xmm0 by `movd eax,xmm0; movsxd rax,eax` (f32) or `movq rax,xmm0` (f64). Only rax, rcx and xmm0 are touched.

| SIR | code |
|---|---|
| f32 / f64 add sub mul div | `movss` / `movsd xmm0,[a]`, then `addss subss mulss divss` / the `sd` forms with `[b]` |
| eq | `ucomiss` / `ucomisd`, then `sete al; setnp cl; and al,cl` |
| gt / ge | `ucomis* [a],[b]`, then `seta` / `setae` |
| lt / le | the operands swapped, then `seta` / `setae`. All four are false when unordered. |
| unordered | `setp` |
| f64 neg / abs | `btc` / `btr rax,63` |
| f32 neg / abs | `xor` / `and eax` with the sign mask, then `movsxd` |
| sqrt | `sqrtss` / `sqrtsd` |
| i64 -> f32 / f64 | `cvtsi2ss` / `cvtsi2sd` (qword) |
| f64 <-> f32 | `cvtsd2ss` / `cvtss2sd` |

**Admission (seed/74, the object artifact only):**
- `xo-check-sir` is seed/70's per-instruction check (`xg-check-sir-at`) with the float SIR above admitted.
- `xo-type` admits the carriers :f32 / :f64 for a private function's parameters and result.
- An export or an extern stays scalar, because System V passes a float in xmm0..7, which the shim and the extern call do not. The shared check stage already refuses a float-typed export (E2104).
- The image artifact, the Linux route and the static routes are unchanged and still refuse every float.

**f32-from-bits.** The library's definition traps an out-of-range pattern by a vector access, which this route refuses. `xo-lib` swaps in the same definition trapping by `(assert ...)`, which is `ud2`.

**Still refused (E7101):**
- `f32-min` / `f32-max` / `f64-min` / `f64-max`: `minss` / `maxss` answer the second operand for a NaN or for two zeros, and the aarch64 route's `fmin` / `fmax` do not.
- f32 / f64 -> i64 truncation: `cvtt*2si` answers 2^63 for a NaN or an overflow, while `fcvtzs` saturates.

## Semantics, stated

The results are SSE's, under the MXCSR the kernel runs with (reset value: round to nearest even, exceptions masked, no FTZ / DAZ):
- A generated NaN is x86's default NaN (`0xffc00000` / `0xfff8000000000000`).
- A propagated NaN is the first NaN operand's, quieted.

This equals the C kernel compiled for x86_64, which is the code an object replaces. It is not bit-equal to the aarch64 route for generated NaNs, whose default NaN is positive.

## Not in this slice

- halt-until-interrupt (JUN-633);
- f32-sin / f32-cos and the other library functions the qwen35 sources define in the kotoba-compiler/1 dialect;
- porting those sources and rebuilding the qwen35 objects (kotoba-lang/kotoba, JUN-554).

## Evidence

- `scripts/seed/check-aiueos-object-f32.py` decodes each operation's instruction in an object exporting all of them.
  - It finds no `min*` / `max*` / `cvtt*2si`.
  - It checks the f32-from-bits range trap and the unchanged width object.
  - It refuses min / max, truncation and float-typed exports. It is wired into mac-selfhost-aiueos.yml.
- `docs/evidence/f32-sse-20261030/` runs that object under QEMU (`-cpu qemu64` and `-cpu max`) against the same operations in C: 754,860 cases, 0 differences.
  - The cases are specials (±0, ±inf, quiet and signalling NaNs with payloads, denormals, extremes) crossed, plus random and near-equal pairs.
  - Two patched objects (addss as subss, eq without the parity test) differ in 16,868 and 351 cases, each confined to the operation patched.
- Six committed kotoba-lang/kotoba aiueos objects recompile byte-identical with this root: ssh-userauth, acpi-madt-parse, cpu-reads, xstate-setup, device-result-text, p256-did.
