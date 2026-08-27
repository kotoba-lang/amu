# ADR 0273: CFG-colored all-vreg fallback

## Status

Accepted.

## Context

The conservative `:all-vregs` fallback stored every SSA definition in a
distinct frame slot. This was safe but made frame size proportional to the
number of definitions rather than the maximum number simultaneously live.
Production continues to prefer the `:call-live` scanner; this ADR changes only
the fallback frame layout.

## Decision

Pin kotoba-mir `2d7f0c0` and kotoba-native `368f7ee`. Fixed-point CFG liveness
builds slot interference, including lowered phi definitions on incoming edges
and slot uses at joins. Greedy coloring follows deterministic SSA definition
order and always selects the lowest available slot.

The allocation fixture colors five definitions into two slots. The call plus
back-edge fixture colors eight definitions into four slots on AArch64 and
x86-64. Amu explicitly forces that fixture through `:all-vregs`, executes real
machine code for inputs 0, 1, 5 and 50 on both available ISA loaders, and
requires the result to equal the input without `KEXE_TRAP`.

## Consequences

The conservative fallback now has a frame footprint bounded by interference
rather than total SSA definition count. This does not remove spill loads or
stores, change production routing, or establish a runtime-speed improvement.
Those require separate measured evidence.
