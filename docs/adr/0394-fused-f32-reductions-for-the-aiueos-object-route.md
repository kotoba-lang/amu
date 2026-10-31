# ADR-0394 -- the aiueos object route's fused f32 reductions (JUN-633 slice 6)

- Status: **implemented** (seed/74, `scripts/seed/check-aiueos-object-fused-dot.py`).
- Date: 2026-10-31
- Tracking: JUN-633 (slice 6). Owner decision 2026-10-31.
- Follows: ADR 0393.

## Context

kotoba's `qwen35-matvec` object (kotoba-lang/kotoba) reaches two builtins that the native object route did not
emit: `kernel-dot-f32` (the live dot product, kotoba-gmir ADR 0010) and `kernel-dequant-dot-ptq1-0` (the fused PTQ1_0
row dot, kotoba-native ADR 0088). The canonical frontend lists both, with arity 5. The native compile stopped with
`E2101 unknown or unsupported form 'kernel-dot-f32'`. Without them, a native build of the object has to drop to a
scalar Kotoba loop and loses its AVX2 path.

## Decision

Ids 30 and 31 are `kernel-dot-f32 [a a-len b b-len count]` and `kernel-dequant-dot-ptq1-0 [weights w-len input i-len
blocks]`. They form a block of their own, after the pause block (so the ids stay positional), and the block is
appended only to a source that names one of them. Every other object keeps its bytes.

The emitted sequences are kotoba-native's `x86-kernel-dot-f32` and `x86-kernel-dequant-dot` (PTQ1_0) as
kotoba-compiler/1 put them into qwen35-matvec.o. Normalized instruction for instruction, both arms match the old
object's. The differences:

- the operands come from their frame slots;
- the answer leaves through eax;
- each guard failure is a local `jcc +2; ud2` instead of a jump to one shared trap.

The contract is an order of summation: four lanes; within each eight-element block, element k of the lower half and
then of the upper half into lane k; then (l0+l1)+(l2+l3); then, for the dot only, the tail onto that sum. There is no
FMA. The two arms compute this tree identically: the AVX2 arm uses xmm0's four lanes, and the scalar arm uses
xmm0..xmm3.

Guards (each traps with `ud2` before any access), in the oracle's order:

1. both lengths are at most 65536;
2. both bases are non-null;
3. count is at most 16384, or blocks at most 128 (min(65536/28, 65536/512)). This check runs before any span is
   formed.
4. count*4 fits each window. For PTQ1_0, blocks*28 fits the weights window and blocks*512 the input window.

The arm is chosen per call, by kotoba-native's guard: cpuid leaf 0 at least 7, OSXSAVE and AVX, XCR0 SSE and YMM,
then AVX2. rbx is pushed around the sequence. The AVX2 arm ends with `vzeroupper`. The answer is the binary32 pattern
sign-extended from bit 31.

Admission: each builtin reads two windows, and both pairs obey the window rule (ADR 0373). The base must be rooted,
and the length must be the base's own region length (its owner's length parameter or a literal). A computed length is
refused (E7106), and so is a record base used as either window. A call with four or six arguments is refused (E2103).

## Evidence

- `scripts/seed/check-aiueos-object-fused-dot.py` (wired into mac-selfhost-aiueos.yml) checks:
  - the guards, the arm choice and both arms in each object;
  - that the pause object (c24f9c96...) and the width object are unchanged;
  - the E2103 refusals (four and six arguments) and the E7106 refusals (computed lengths).
- `seed/tests/kernel-memory`: four ok and eight no cases for the two builtins, covering:
  - subregion and helper-parameter bases;
  - a computed first or second length, a second length naming the other region;
  - an arithmetic or literal base, a record base.
- `docs/evidence/fused-dot-20261031/`: a QEMU TCG differential against the committed kotoba-compiler/1
  qwen35-matvec.o, in the scalar, AVX2 and AVX2-CPU-without-OSXSAVE configurations:
  - 20000 dot and 8000 PTQ1_0 cases with NaN, Inf, ±0 and denormals: 0 differences; 0 mismatches against a C model
    of the tree (modulo NaN payloads); the same answer hash in all three runs;
  - 19 of 19 guards behave as expected;
  - two summation-order mutants are caught (286 and 329 of 4500 cases differ).
- Every other object gate (pause, halt, xstate, f32, cpu, windows16) passes on this root. The 11 kotoba aiueos
  objects built on the native route recompile byte-identical, and 80 kotoba aiueos sources compile to the same bytes
  as under ADR 0393.

## Gaps

The differential runs under TCG, so a difference between TCG and hardware in NaN, denormal or MXCSR behaviour would
affect both sides alike and go unseen. No hardware run is recorded.
