# ADR 0250: Fuse safe allocated AArch64 multiply-add and multiply-subtract pairs

Status: accepted

Date: 2026-08-12

## Context

After compact constant materialization, the comparison kernel still emitted
two avoidable instructions in each unrolled round: `MUL` followed by `ADD`,
and another `MUL` followed by `SUB`. AArch64 represents these exact operations
as `MADD` and `MSUB`.

Fusing before allocation would make register aliasing and intervening clobbers
implicit. Fusing only in the byte emitter would hide the new ternary operation
from the closed MIR and MC contracts and their independent validation.

## Decision

MIR and MC admit explicit physical `multiply-add` and `multiply-subtract`
operations with two multiplicands and one addend. They remain unavailable in
virtual target-independent MIR.

The AArch64 MIR-to-MC lowering fuses an allocated multiply with its consumer
when all of these conditions hold:

- only constant materializations appear between producer and consumer;
- none of those constants overwrites the multiply result or either input;
- the consumer is `product + addend`, `addend + product`, or
  `addend - product`;
- product and addend are distinct physical registers.

`product - addend` is not an `MSUB` shape and remains unfused. The selector
accepts legal allocation aliases such as multiply destination equal to an
input. x86-64 output is unchanged.

Amu pins the resulting closure:

- `kotoba-mir` `3d2673472b6100d2928ac998c02709b4238c0058`;
- `kotoba-codegen` `c85088bfe9dd85e9c6a65d986f34a651b2af7d13`;
- `kotoba-native` `98dd22a63044ce9cd5ddb7babb3efc7cdcddcbbe`;
- `kotoba-verifier` `1c28555e57a3c26c531353f8b86ac32c6f263455`.

## Evidence

The host was under variable background load, so the optimization delta was
measured with prebuilt artifacts through one native runner, alternating old
and new order for 15 samples. Each sample used 10,000,000 measured calls after
1,000,000 warmup calls on an Apple M1 Max.

| artifact | median | raw native code | KEXE |
|---|---:|---:|---:|
| constant-minimization baseline (`b1d5ba5`) | 22.7294 ns | 580 bytes | 4,437 bytes |
| MADD/MSUB closure (`8134fb3`) | 19.0757 ns | 516 bytes | 4,259 bytes |

The fused artifact is 16.1% faster and its raw code is 11.0% smaller. All 16
eligible multiply/consumer pairs became one instruction, accounting for the
64-byte code reduction.

An additional alternating 15-sample run measured the fused artifact at
23.0068 ns and Rust LLVM O3 at 14.6847 ns under the same load, leaving Amu at
1.567x LLVM O3. This remains a compiler-backend comparison and is not a claim
that Amu has exceeded LLVM.

Verification passed:

- `kotoba-mir`: 31 tests, 898 assertions;
- `kotoba-codegen`: 20 tests, 118 assertions;
- `kotoba-native`: 142 tests, 2,010 assertions;
- `kotoba-verifier`: 46 tests, 261 assertions;
- Amu: 964 tests, 7,608 assertions;
- full native/Wasm conformance, JDK-free W^X execution, compiler bundle byte
  parity, worker/daemon protocol tests, and seven-engine runtime smoke.

## Consequences

The optimization has an explicit, validated ternary representation rather
than depending on neighboring byte patterns. Negative tests preserve
unfusable subtraction order and clobber cases. The remaining LLVM gap must be
addressed by later selection, reciprocal, scheduling, and register-move work;
this decision does not weaken arithmetic or safety semantics.
