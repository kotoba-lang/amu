# ADR 0079: Structural option/result Component lowering

Status: accepted

## Context

ADR 0068 implemented the standard32 layout for structural `option<T>` and
`result<T,E>`, but the component emitter rejected every function using those
types. The layout's bounded-discriminant requirement was therefore descriptive
only, and no Kotoba program could produce a standard WIT option or result.

## Decision

Admit two capability-free, single-export shapes when every payload is an
`i64`, `f32`, `f64`, or `bool`:

- identity: one option/result parameter returned unchanged;
- explicit construction: `option-none-of`, `option-some-of`,
  `result-ok-of`, or `result-err-of`.

The structural layout retains its two ordered case layouts. Code generation
reuses the sealed-variant Canonical ABI emitter for identity instead of adding
a second union codec. It receives the flattened discriminant and joined
payload, checks the discriminant with an unsigned comparison against the case
count before dispatch, stores only the active payload, and returns an aligned
indirect result area.

Constructors use the same result-area layout and bounded allocator, write a
compiler-selected discriminant, validate a boolean payload when present, and
store only that case's scalar payload. `none` has no fabricated payload store.

The WIT remains structural: `option<T>` and `result<T,E>` are emitted directly,
without nominal wrapper types or runtime-specific imports. No ambient WASI or
provider authority is introduced.

## Security consequences

- A caller-controlled discriminant outside `0..1` traps before payload
  interpretation.
- Result allocation is alignment checked, overflow checked, and bounded to the
  module's declared memory.
- Only the selected case is read or stored; payload-less `none` touches no
  payload value.
- Unsupported nested or resource-owning payloads remain rejected at component
  admission rather than receiving an incomplete recursive codec.

## Evidence

Tests package the generated core module as a standard Component and execute
`none`, `some(7)`, `ok(7)`, and `err(-8)` identity calls with the pinned real
Wasmtime engine. A direct core invocation with discriminant `2` traps.

Four `.kotoba` programs compile through `compile-component` for the explicit
constructors. Their `none`/`some`/`ok`/`err` results execute in Wasmtime and
match the reference interpreter's values.

## Remaining gaps

- recursive aggregate payload codecs and aggregate values nested in records;
- option/result capability request/result and provider bindings;
- projections, matches, and general computation in the Component emitter;
- payload-less WIT result forms outside Kotoba's existing two-payload result
  descriptor;
- native AOT parity, which remains a distinct ABI track.
