# ADR 0257: Rematerialize a lone AArch64 constant across local calls

Status: accepted

Date: 2026-08-12

## Context

The new pressure/call corpus exposed a small but expensive call-live shape. A
constant used after a non-tail local call was allocated to the only spill slot:
materialize, store, call, load, consume. On AArch64 one eight-byte slot creates
a 16-byte-aligned storage area, adding stack adjustment as well as the
store/load pair.

Recreating a small pure constant after the call is cheaper and cannot trap.

## Decision

After allocation and before MC lowering, recognize only a function with one
frame slot and exactly this sequence:

`constant R; spill-store R, slot 0; call; spill-load R, slot 0`.

The register must not be a call argument, and these must be the function's only
spill operations. Replace the sequence with `call; constant R` and reduce the
frame-slot count to zero. All other spill shapes remain unchanged. The closed
rule intentionally avoids pretending to be a general allocator spill-cost
model.

Amu pins `kotoba-native`
`d7c82c87c7b831125e8a8b6ac36fe529507f74dd`. x86-64, allocator and IR
contracts, and verifier schemas remain unchanged.

## Evidence

The `local-call-live-constant` symbol falls from 64 to 44 bytes. Its spill
store/load and aligned spill area disappear, while the constant moves after the
call. Control symbols remain stable: `add-one` 28 bytes, register-pressure 264,
`sum-five` 56, and the five-argument tail caller 100.

The corpus fixes five symbol-size contracts and runs the three arity-one
exports through the real AArch64 W^X loader. The landed KEXE ceiling is 4,666
bytes. Native verification passed 155 tests and 2,149 assertions, including a
negative test that retains the spill when the constant is a call argument.

## Consequences

This removes a common local-call tax without extending liveness or reserving a
callee-saved register. The 264-byte register-pressure control is now the
largest obvious code-quality target; its spill structure should be measured
before attempting global register allocation changes.
