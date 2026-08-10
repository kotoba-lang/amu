# ADR 0228: native record SROA evidence follows the pinned closure

- Status: accepted
- Date: 2026-08-11
- Machine-readable companion:
  [`0228-native-record-sroa-evidence.edn`](0228-native-record-sroa-evidence.edn)

## Context

The legacy native record path boxes values that cross function boundaries.
That representation remains necessary until the aggregate ABI and call-clobber
contract are explicit. It is unnecessarily costly for a bounded local record
whose fields are projected before a scalar return, however.

`kotoba-native` now scalar-replaces one deliberately narrow family: a
non-escaping, non-empty fixed record with unique keyword field names and only
`:i64` or `:bool` fields. All constructor fields are evaluated once in declared
order. A record-valued value-position `if` carries an ordered SSA bundle and
emits one GMIR phi per field.

## Decision

Amu pins `kotoba-native` `8374a6c4cdd31110363a6996eaba6a737d9d9f02`.
It also pins the independently matching `kotoba-verifier`
`5f7905d8ca3849c857d466aa843b4ddde3b4a472`.
The generated dependency lock continues to bind `kotoba-codegen`
`58b923db72d3a1c984155eb93ebdcffbbe8885f2` and `kotoba-mir`
`30f9afacfc1cbbbb41956f893a9eca0a16934c1b`.

The shared ISA gate compiles a source-level two-field record-valued branch.
Both AArch64 and x86-64 production loaders execute both edges as real
processes: argument one returns three and argument zero returns seven. The
consumer plan has two phis, zero frame slots, two selected edge moves, and no
spill traffic. A second source projects only the second field after the first
field divides by zero; both loaders trap, proving scalar replacement did not
discard or reorder constructor evaluation.

The verifier re-derives the admitted value shape instead of trusting producer
metadata: both `if` branches must be direct constructors of the same exact
`:i64`/`:bool` record. The value may be projected directly or named by one
`let`; schema drift, nested/non-scalar fields, and symbol forwarding remain
rejected before re-emission.

## Consequences

This record family needs neither heap allocation nor a serialized aggregate
GMIR operation. The representation is eliminated before GMIR and the existing
scalar MIR parallel-copy contract transports its fields.

Escaping records, nested or non-scalar fields, variants, and a general
aggregate calling convention remain on the legacy path or fail the pilot
predicate. This evidence does not establish Rust-wide performance parity or a
global optimizing register allocator.
