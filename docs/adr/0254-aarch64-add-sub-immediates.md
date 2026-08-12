# ADR 0254: Fold single-use AArch64 add and subtract immediates

Status: accepted

Date: 2026-08-12

## Context

The modular-mix benchmark is now within about one percent of LLVM O3, but it
does not cover ordinary scalar code well. A five-function corpus exposed a
common difference: Amu materialized every single-use integer constant and then
used register `ADD` or `SUB`, while LLVM selects AArch64's immediate forms.

Unrestricted constant CSE is not the answer for these values. Extending their
liveness can increase pressure in the current four-register allocator, and a
constant used once should not occupy a register at all.

## Decision

After physical allocation and leaf-constant caching, fold a constant followed
immediately by its sole consuming `ADD` or `SUB` when its magnitude fits either
an unsigned 12-bit immediate or that immediate shifted left by 12.

The sole-use proof follows the physical register from this definition through
the next definition of the same register. This matters across branch arms:
counting a physical register name over the whole function confuses distinct
post-allocation definitions and unnecessarily blocks safe folds.

Commutative `ADD` accepts the constant on either side. `register - constant`
folds, while `constant - register` does not. Negative constants invert the
selected operation, so add-negative becomes `SUB immediate` and
subtract-negative becomes `ADD immediate`. Values outside the two architectural
forms retain their former materialization.

Amu pins `kotoba-native`
`9e32a479419ffe28ae533aecdeea24fd51f609d9`. GMIR, MIR, MC, verifier schemas,
and x86-64 output remain unchanged.

## Corpus and evidence

The landed corpus compiles five exported functions, checks exact selected
symbol sizes, and on AArch64 executes every function through the existing W^X
benchmark loader. It includes positive, negative, shifted, control-flow, and
repeated-constant cases.

| kernel | old symbol | new symbol | paired speedup |
|---|---:|---:|---:|
| add small positive | 36 bytes | 32 bytes | 1.0034x |
| add negative | 36 bytes | 32 bytes | 1.0020x |
| subtract shifted immediate | 36 bytes | 32 bytes | 0.9946x |
| branch with two immediate arms | 56 bytes | 48 bytes | 1.0022x |
| repeated-constant control | 36 bytes | 36 bytes | 0.9936x |

Each timing used 31 samples, with old and new alternated in 100 blocks of
100,000 calls per sample. These 1.7–2.1 ns functions are dominated by call
overhead; all results remain within 0.6% of parity. The supported cases remove
one instruction per fold, the repeated-cache control remains byte-identical,
and the complete corpus KEXE falls from 3,760 to 3,696 bytes.

Verification passed:

- `kotoba-native`: 148 tests, 2,033 assertions;
- Amu: 964 tests, 7,608 assertions;
- five corpus code-size contracts and five real AArch64 W^X executions;
- native/Wasm conformance, JDK-free W^X extraction, compiler-bundle byte parity,
  worker/daemon protocols, and seven-engine runtime smoke.

## Consequences

Ordinary scalar arithmetic and branch arms gain LLVM-style immediate selection
without extending virtual-register liveness. Repeated constants still use the
leaf cache when profitable, and non-encodable or non-commutative shapes remain
explicit.

The corpus is now a durable complement to the unrolled modular-mix benchmark.
The next backend step should extend it with register-pressure and local-call
kernels, then improve allocation or move coalescing based on failures across
that broader set rather than a single expression.
