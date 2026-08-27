# ADR 0275: Post-allocation per-basic-block CFG scheduling

## Decision

Pin kotoba-mir `ad739526` through kotoba-native `542ad8e1`. Integer
scheduling now runs after register allocation on physical MIR. Each basic block
is scheduled independently; labels, branches, spills, moves, calls, and every
other non-schedulable operation remain hard barriers. Pre-allocation CFG
scheduling is rejected: reordering virtual SSA before the linear scanner changes
register reuse under spill pressure and miscompiles real programs.

## Evidence boundary

The shared native execution table requires
`a-value-spilled-in-one-branch-arm-survives-into-the-other` to return `282` from
real processes on every available ISA loader. macOS requires both AArch64 and
x86-64 loaders. ADR 0274's straight-line scheduled-integer oracle is withdrawn
here: post-allocation scheduling no longer uses that pre-allocation evidence
shape.

This proves that post-allocation per-basic-block scheduling preserves the
tested programs' semantics. The latency table remains a compiler heuristic. No
benchmark in this ADR establishes a wall-clock speed improvement or parity with
Rust/LLVM.
