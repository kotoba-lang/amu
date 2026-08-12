# ADR 0255: Coalesce AArch64 phi edges and returns into direct results

Status: accepted

Date: 2026-08-12

## Context

The multi-kernel AArch64 corpus removed constant materialization overhead but
still exposed avoidable copies. Value-position conditionals emitted a result
into a temporary physical register and immediately moved it into the phi
register on each edge. Ordinary leaf expressions similarly computed into an
allocator register and moved the final value into ABI return register `x0`.

AArch64 integer arithmetic is generally three-operand, so changing the
destination does not destroy an input. These copies are therefore avoidable,
provided post-allocation physical-register liveness remains respected.

## Decision

Before lowering allocated MIR to MC, coalesce two closed shapes on AArch64:

- a direct-result producer followed by `return` of that result writes `x0`;
- a direct-result producer, optional edge labels, `move`, and unconditional
  jump writes the move destination directly.

The pass admits only constants, scalar arithmetic, bitwise operations, shifts,
and comparisons whose encoders accept an arbitrary destination and read all
sources before writing it. Calls, memory operations, floating-point bridge
sequences, and encoders with private scratch conventions are excluded.

An edge move is retained if the producer's old physical register is used in
the target block before its next definition. This definition-aware check is
required because the same physical register name may represent distinct
allocations after control-flow joins.

Amu pins `kotoba-native`
`a3ed13b114e806cf005cdf6122ea4c3a630e733f`. GMIR, MIR, MC, verifier schemas,
and x86-64 selection remain unchanged.

## Evidence

The existing five-kernel corpus now records:

| kernel | before | after |
|---|---:|---:|
| add small positive | 32 bytes | 28 bytes |
| add negative | 32 bytes | 28 bytes |
| subtract shifted immediate | 32 bytes | 28 bytes |
| branch with two immediate arms | 48 bytes | 40 bytes |
| repeated-constant control | 36 bytes | 36 bytes |

The full KEXE falls from 3,696 to 3,676 bytes. The branch kernel removes both
edge copies; each supported leaf removes its return copy. The repeated-constant
control is unchanged because extending that value into `x0` is not proven safe
by this local shape.

Verification passed:

- `kotoba-native`: 153 tests, 2,145 assertions;
- Amu: 970 tests, 7,658 assertions;
- five exact symbol-size contracts and five real AArch64 W^X executions;
- a negative liveness test that retains the move when its source is live at
  the join.

## Consequences

Common scalar leaves are one instruction shorter, and value-position branch
results no longer pay one copy per edge. This is local post-allocation
coalescing, not a replacement for graph coloring or global register allocation.

The next useful corpus expansion is register-pressure and local-call kernels.
That evidence can distinguish profitable spill-cost improvements from further
safe local copy elimination.
