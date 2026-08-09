# ADR 0222: native emit fuel is sealed, not ambient

- Status: Accepted
- Date: 2026-08-09

## Decision

For `x86_64-kotoba-v1` and `aarch64-kotoba-v1`, the fuel selected from emit
metadata or policy budgets is written identically to:

- `artifact.fuel-abi.initial`;
- `artifact.limits.fuel`;
- the independent verifier oracle budget.

The default remains 512. `kotoba-verifier` ADR 0005 bounds an explicit value to
1..1,048,576 and rejects mismatches. A tender must initialize the hidden native
context with the sealed value; it cannot silently replenish or substitute one.

## Reason

Wasm already compiled the declared budget into its private fuel global, while
native artifacts always claimed 512 even when the caller supplied a different
bounded budget. That made sufficiently deep pure programs impossible to seal
and made build metadata disagree with the native runtime contract.

This change varies only fuel. Memory, stack, string, pair, graph, and vector
arenas remain fixed by the native context ABI.
