# ADR 0253: Combine AArch64 reciprocal sign correction into shifted ADD

Status: accepted

Date: 2026-08-12

## Context

Signed reciprocal division truncates toward zero by adding one when the shifted
intermediate is negative. Amu emitted this as two AArch64 instructions:

```text
LSR dst, x17, #63
ADD dst, x17, dst
```

AArch64's shifted-register operand expresses the same operation in one word:

```text
ADD dst, x17, x17, LSR #63
```

LLVM uses this combined form. It also avoids overwriting `x16`, where the prior
decision keeps the reciprocal multiplier cached.

## Decision

The AArch64 constant-quotient encoder emits one shifted-register `ADD` for the
final truncation correction. The proof is direct: logical right shift by 63 of
an i64 is zero for non-negative values and one for negative values, exactly the
correction previously produced in a separate destination instruction.

Amu pins `kotoba-native`
`81ba705d48295cccb6f192af29c764bac8bfcf45`. GMIR, MIR, MC, verifier schemas,
and x86-64 output do not change.

An evaluated alternative did not land. Replacing multiplication by the cached
`2^31-1` with shifted subtract plus add expanded the kernel and measured only
0.913x the existing hoisted-divisor `MSUB` path. Apple M1 therefore benefits
from retaining `MSUB`; matching an LLVM transform syntactically is not itself
an optimization.

## Evidence

The eight-round kernel loses exactly one instruction per reciprocal:

| artifact | fine-paired median | extracted file | symbol code | KEXE |
|---|---:|---:|---:|---:|
| leaf-cache baseline | 19.372717 ns | 316 bytes | 276 bytes | 3,543 bytes |
| shifted correction | 19.267004 ns | 284 bytes | 244 bytes | 3,447 bytes |

The host was heavily shared, so each of 31 samples alternated old and new in
100 small blocks of 100,000 calls. The median paired speedup is 1.0024x and the
new artifact won 16 of 31 samples. Runtime improvement is therefore modest;
the strong result is the deterministic 32-byte symbol reduction with no
measured regression.

For a less noisy LLVM comparison, Rust's O3 kernel was compiled as a separate
LLVM object and called beside the extracted Amu function in the same process.
The same 31 by 100-block pairing measured Amu at 11.6902 ns and LLVM at
11.5786 ns, a median paired ratio of 1.0083x. Amu is now within about 0.83% on
this kernel, but has not exceeded LLVM.

Verification passed:

- `kotoba-native`: 146 tests, 2,023 assertions;
- Amu: 964 tests, 7,608 assertions;
- native/Wasm conformance and AArch64 execution under W^X;
- JDK-free extraction, three-target compiler-bundle byte parity,
  worker/daemon protocols, and seven-engine runtime smoke.

## Consequences

Every signed constant quotient using the reciprocal path becomes one word
shorter, independent of this benchmark's divisor. `x16` remains available for
multiplier reuse and `x17` remains local scratch.

The remaining measured gap on this kernel is below one percent and near the
noise floor of the shared host. Subsequent runtime work should broaden the
corpus and optimize register allocation or scheduling across multiple kernels,
rather than tuning only this unrolled expression.
