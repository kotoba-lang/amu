# ADR 0274: Latency-aware integer scheduling

## Decision

Pin kotoba-mir `699ead0` through kotoba-native `7b757f7`. The MIR allocator
now schedules only consecutive pure, non-trapping integer SSA operations.
Calls, memory, division, constants, floating-point, phi/control flow, and all
other operations are hard barriers. Already-adjacent AArch64 MADD/MSUB
candidates remain fixed so scheduling does not undo existing fusion quality.
Functions containing control flow remain completely unscheduled in this first
qualified scope.

## Evidence boundary

The shared native execution table runs a dependent multiply chain with an
independent add and requires result `33` from real processes on every available
ISA loader. macOS requires both AArch64 and x86-64 loaders.

This proves that the scheduled compilation path preserves the tested program's
semantics. The latency table is a compiler heuristic. No benchmark in this ADR
establishes a wall-clock speed improvement or parity with Rust/LLVM.
