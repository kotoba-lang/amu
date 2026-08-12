# ADR 0256: Summarize the Amu native performance program through AArch64 coalescing

Status: accepted

Date: 2026-08-12

## Context

Amu already compiles Kotoba source directly through GMIR, MIR, allocated
machine code, KEXE sealing, and a W^X runtime loader. The performance question
started as whether Kotoba could build and run faster and more safely than Rust,
C, or C++. For backend implementation work, however, the precise comparison is
LLVM code generation. Rust/C/C++ remain useful end-to-end product comparisons;
LLVM O3 is the reference for instruction selection and generated-code quality.

This ADR consolidates the optimization sequence that was previously spread
across benchmark notes, implementation commits, and ADR 0255.

## Decision

Retain Amu's direct native path and optimize it incrementally after measuring
selected machine code. The completed sequence is:

1. select reciprocal multiplication for signed division by constants and
   remove the now-dead divisor materialization;
2. minimize AArch64 constant materialization, including logical immediates;
3. select `MADD` and `MSUB` when multiply results have one safe consumer;
4. cache profitable repeated constants only in closed branchless leaves;
5. combine reciprocal sign correction into shifted arithmetic;
6. select `ADD/SUB immediate`, including the shifted 12-bit form and negative
   constants;
7. coalesce safe phi-edge and return copies into three-operand destinations.

All transforms remain after validated IR selection and use closed admitted
operation sets. Physical-register reasoning is definition-aware: a reused
register name is not treated as one lifetime across the whole function. W^X
execution, bounded stack frames, closed linkage, and verifier schemas remain
the safety floor; performance work does not relax them.

The current continuation pin is `kotoba-native`
`d7c82c87c7b831125e8a8b6ac36fe529507f74dd`, which also includes the next
call-boundary rematerialization recorded in ADR 0257.

## Evidence

The modular-mix kernel, measured in the same process on Apple M1 Max, reached
11.6902 ns for Amu versus 11.5786 ns for LLVM O3, a ratio of 1.0083x. This is a
kernel result, not a claim that all Kotoba programs are within one percent of
LLVM.

The durable immediate corpus broadened coverage beyond that kernel. Across the
completed sequence, its KEXE fell from 3,760 to 3,676 bytes. Supported scalar
leaves lost constant-materialization and return-copy instructions; the branch
kernel lost both phi-edge copies. All five functions execute through the real
AArch64 W^X loader.

The latest native closure before continuing passed 155 tests and 2,149
assertions. The Amu closure through ADR 0255 passed 970 tests and 7,658
assertions, plus five exact corpus size contracts and five W^X executions.

Compiler startup/build latency is a separate axis from generated-code quality.
Bundle preloading and a persistent daemon were experimentally validated, but
they are not treated as a substitute for backend measurements and are not
silently folded into this latest-main pin.

## Consequences

Performance claims must name their layer: compiler startup, build throughput,
selected code size, steady-state runtime, memory, or safety validation cost.
No single microbenchmark establishes superiority over Rust, C, or C++.

The next durable corpus covers register pressure and direct local calls. Its
first target is call-live constants that are cheaper to recreate than spill.
