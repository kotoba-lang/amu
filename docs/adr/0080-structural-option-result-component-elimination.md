# ADR 0080: Structural option/result Component elimination

Status: accepted

## Context

ADR 0079 made scalar structural options and results constructible and
round-trippable as standard Components, but a compiled Kotoba component still
could not inspect them. The frontend and interpreter already define typed tag
predicates and fallback projections, so rejecting those functions at Component
admission left the value codec usable only as a transport echo.

## Decision

Admit capability-free single exports for:

- `option-some?-of` and `result-ok?-of`;
- `option-value-of`, `result-value-of`, and `result-error-of`.

The union must be the first parameter. A projection's fallback is its second
parameter and has exactly the selected scalar payload type. This intentionally
does not pretend to compile an arbitrary fallback expression or exhaustive
match branch; those require a shared general expression-lowering path rather
than another operation-specific expression compiler.

The generated standard32 core function receives the same discriminant and
joined payload positions as ADR 0079. It checks the discriminant before any
case-dependent interpretation. Predicates return the checked tag directly.
Projections select either the active payload or fallback with a typed Wasm
`if`, applying the Component Model's joined-flat coercion table when the two
result cases use different core types.

For boolean projections, the fallback is always checked for canonical `0/1`.
The union payload is checked only inside the selected branch. Consequently a
malformed active boolean traps, while bytes occupying an inactive payload
position are never assigned the inactive case's type.

Operation and descriptor kinds are matched explicitly at admission:
option operations cannot be paired with a result descriptor or vice versa,
even in a hand-crafted KIR that bypasses the source verifier.

## Evidence

Five `.kotoba` programs compile through `compile-component` and execute in the
pinned real Wasmtime engine:

- option tag over `none` and `some`;
- option payload/fallback projection over both cases;
- result tag over `ok` and `err`;
- result ok projection over both cases;
- result error projection over both cases.

Every execution is also compared with `ir/execute`. A separate
`option<bool>` fixture invokes the generated core module directly: active
payload `2` traps, while the same invalid bits in the inactive payload position
are ignored and the canonical fallback is returned.

## Remaining gaps

- aggregate exhaustive match values (heterogeneous i64/f32/f64/bool
  exhaustive computation is implemented by ADR 0082);
- recursive aggregate payload codecs;
- asymmetric or aggregate option/result capability request/result bindings
  (same-type scalar bindings are implemented by ADR 0081);
- option/result values nested inside record fields;
- native AOT parity, which remains a separate ABI track.
