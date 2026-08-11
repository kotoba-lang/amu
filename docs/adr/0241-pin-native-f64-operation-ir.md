# ADR 0241: pin native f64 operations through machine IR

## Context

Amu's real-loader table already qualified scalar f64 arithmetic and NaN
comparison semantics, but the pinned native backend still selected those rows
through its legacy recursive emitters.

## Decision

Pin `kotoba-native` at `1eb54af54ce12667af4138bb4fdb0cb02cbe465b`
and regenerate `deps-lock.edn`. This closure carries f64 operations through
GMIR, MIR allocation, selected MC, and the x86-64/AArch64 encoders while
retaining the one-word bit-pattern ABI.

The exact pinned closure must pass the existing real-loader ISA table with both
AArch64 and x86-64 available. Structural assertions also require every admitted
f64 source form to satisfy the production machine-IR pilot.

## Consequences

Scalar f64 is no longer a production legacy-emitter gap. Runtime handles,
capabilities, strings, and escaping aggregates still require explicit runtime
and effect contracts before they can be migrated.
