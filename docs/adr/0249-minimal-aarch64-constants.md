# ADR 0249: Materialize AArch64 i64 constants with the shortest wide-move sequence

Status: accepted

Date: 2026-08-12

## Context

The production AArch64 MC encoder emitted every i64 constant as four words:
one `MOVZ` followed by three `MOVK` instructions. Small constants such as
`1` and `48271` therefore cost the same 16 bytes as a value with four populated
16-bit lanes. The modular-mix comparison kernel repeats those constants and a
constant-division reciprocal across eight unrolled rounds, making redundant
wide moves a material part of both its instruction footprint and execution
time.

This is an MC-encoding issue, not a Rust-language comparison. LLVM already
selects compact AArch64 constant sequences for the Rust fixture.

## Decision

The production MC encoder evaluates both legal wide-move seeds:

- `MOVZ`, whose unpatched lanes are zero; and
- `MOVN`, whose unpatched lanes are all ones.

It chooses the seed requiring fewer total words, uses `MOVK` only for lanes
that differ from the seed's fill value, and chooses `MOVZ` on a tie. Zero,
small positive constants, `-1`, `Long/MIN_VALUE`, and values where `MOVN` wins
have explicit wire/size tests.

Two sites deliberately retain the old four-word form. The checked dynamic
division sequence has fixed local branch displacements, and deferred data
addresses reserve exactly 16 bytes during final layout. Compacting either
without first changing its enclosing layout contract would corrupt control
flow or offsets.

Amu pins `kotoba-native` at
`1df2e7eb91e6f1da796dbbc335e24ef6a29e3161` and the matching verifier at
`e67c50bb50bc7b4806dd7447ea07276ead6c022c`. The verifier continues to
re-emit the artifact through its pinned production backend and compare the
code bytes exactly.

## Evidence

The old and new clean commits were measured sequentially on the same Apple M1
Max with five runs, 1,000,000 measured calls, and 100,000 warmup calls per run.
The common kernel and expected result were unchanged.

| clean commit | Amu native median | Rust LLVM O3 median | Amu / O3 | raw native code | KEXE |
|---|---:|---:|---:|---:|---:|
| `dd83717` (old encoder) | 21.293 ns | 9.554 ns | 2.229x | 880 bytes | 5,344 bytes |
| `ba475df` (minimal constants) | 18.312 ns | 9.697 ns | 1.888x | 580 bytes | 4,437 bytes |

This change makes the measured Amu kernel 14.0% faster, reduces its raw native
code by 34.1%, and reduces the complete KEXE by 17.0%. It does not yet beat
LLVM O2/O3; the remaining 1.89x gap is the next optimization target.

Verification passed in the pinned closure:

- `kotoba-native`: 139 tests, 1,999 assertions;
- `kotoba-verifier`: 46 tests, 261 assertions;
- Amu: 964 tests, 7,608 assertions;
- full native/Wasm conformance, JDK-free W^X execution, and the seven-engine
  LLVM O0/O2/O3 runtime comparison.

## Consequences

Code layout now reflects the selected constant width, so ordinary labels and
relative branches move closer and are resolved from final token sizes. The
fixed-width exceptions remain explicit rather than silently depending on a
general encoder always returning 16 bytes.

The optimization changes neither i64 semantics nor the safety boundary. It
only removes instructions that write lanes already supplied by the selected
wide-move seed.
