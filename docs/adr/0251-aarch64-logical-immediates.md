# ADR 0251: Select compact AArch64 logical immediates for integer constants

Status: accepted

Date: 2026-08-12

## Context

The fused runtime-comparison kernel uses the constant `2,147,483,647` in each
of its eight unrolled remainder calculations. The existing AArch64 constant
selector required `MOVZ` plus `MOVK` for this value. AArch64 can encode it in
one `ORR Xd, XZR, #imm` instruction, whose architectural alias is
`MOV Xd, #imm`.

LLVM O3 uses the same signed reciprocal construction as Amu: `SMULH`, the
numerator correction, arithmetic shift, and truncation-toward-zero correction.
It also avoids repeated two-word divisor materialization. Therefore the
reciprocal arithmetic itself must not be weakened; constant selection is the
first independently provable remaining difference.

## Decision

`kotoba-native` admits every legal 64-bit AArch64 logical immediate: a rotated,
non-empty and non-full run of ones in a power-of-two element, replicated to 64
bits. The selector constructs the immediate fields from four exact unsigned
16-bit chunks. This keeps JVM and ClojureScript selection identical without
depending on JavaScript's 32-bit bitwise-number semantics.

The encoder uses `ORR Xd, XZR, #imm` only when its one word is strictly shorter
than the best `MOVZ`/`MOVN` plus `MOVK` sequence. Ties retain the existing wide
move spelling. All-zero and all-one values remain `MOVZ` and `MOVN`, and sites
whose branch layout reserves a fixed four-word constant remain unchanged.

Amu pins `kotoba-native`
`b11f869d06a955fd7a47d5ecdb800718df7c6419`. MIR and MC schemas do not change:
this is a target encoder choice for the existing constant operation.

## Evidence

Prebuilt old and new artifacts were executed through one W^X benchmark runner,
alternating order for 15 samples. Each sample used 10,000,000 measured calls
after 1,000,000 warmup calls on an Apple M1 Max.

| artifact | median | extracted file | symbol code | KEXE |
|---|---:|---:|---:|---:|
| MADD/MSUB baseline (`21ba227`) | 15.1363 ns | 516 bytes | 476 bytes | 4,259 bytes |
| logical-immediate closure | 14.6365 ns | 484 bytes | 444 bytes | 4,123 bytes |

The new artifact is 3.30% faster and removes one 4-byte word from each of the
eight divisor materializations. An independent alternating 15-sample comparison
measured this Amu artifact at 14.3947 ns and Rust LLVM O3 at 9.6792 ns, leaving
Amu at 1.487x LLVM O3 under that run's host load. This is a backend comparison,
not a claim that Amu has exceeded LLVM.

Verification passed:

- `kotoba-native`: 143 tests, 2,014 assertions;
- Amu: 964 tests, 7,608 assertions;
- full native/Wasm conformance;
- JDK-free independent extraction and AArch64 execution under W^X;
- three-target compiler bundle byte parity and integrity fallback.

## Consequences

All code using multiword replicated or rotated bitmask constants can benefit,
not only this benchmark. Invalid bitmasks and fixed-layout sequences preserve
their former encoding. The next material gap visible in LLVM output is
cross-expression constant reuse: LLVM keeps `48,271`, `1`, and the reciprocal
multiplier live across all eight rounds, while Amu currently rematerializes
them. That requires liveness-aware constant CSE or hoisting rather than another
local byte-encoding rule.
