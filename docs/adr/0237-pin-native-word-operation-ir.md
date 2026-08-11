# ADR 0237: pin native word operations on machine IR

## Context

Amu already exercised bool/bit negation, i64 shifts, and i32 wrapping through
the real native loader, but its pinned native backend still selected those rows
through the established recursive emitter. The split GMIR/MIR/MC repositories
now publish portable left, signed-right, and unsigned-right shift contracts.

## Decision

Pin `kotoba-native` merge `c1d67beb48936a77885f2ee0631390a7545129fe`
and regenerate `deps-lock.edn` in the same commit. Keep the existing real-loader
word rows as the semantic gate, and add a structural assertion that every
admitted word form satisfies the production machine-IR pilot.

## Evidence

- `kotoba-native`: 119 tests, 1,346 assertions;
- local Amu real-loader run against the new native checkout: 3 tests, 493
  assertions, with both AArch64 and x86-64 available;
- exact `deps.edn` / `deps-lock.edn` native commit identity.

## Consequences

Portable word arithmetic no longer depends on the legacy production route.
Runtime handles, capabilities, floating point, strings, and escaping aggregate
boundaries remain explicit later stages of the complete native migration.
