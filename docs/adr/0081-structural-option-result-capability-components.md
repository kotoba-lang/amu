# ADR 0081: Structural option/result capability Components

Status: accepted

## Context

ADR 0079 and ADR 0080 made scalar structural options and results executable
inside one Component, but a `typed-cap-call` using either type still failed
Component admission. Sealed variants already had a named WIT application
import, an independently packaged provider export, and closed-world
composition. Implementing a second union transport would duplicate the
security-sensitive discriminant and joined-payload codec.

## Decision

Admit a direct `typed-cap-call` when request and result are the same structural
`option<T>` or `result<T,E>` and every payload is `i64`, `f32`, `f64`, or
`bool`.

The application reuses the sealed-variant capability emitter. It forwards the
checked WIT value as discriminant plus joined payload positions to the named
provider import, allocates a bounded indirect result area, and returns it
through standard Canonical lifting.

Provider packaging also reuses the variant provider emitter and its
case-dispatch validation. The provider WIT is structural
`option<T>`/`result<T,E>` rather than a nominal wrapper. Its type spelling is
obtained from the same now-public `component-wit/type-text` function used by
the application world, eliminating a second descriptor renderer.

`compose-closed` remains the authority closure gate. Its existing exact
frequency comparison requires one provider for every declared import and no
extras; `wac plug` and `wasm-tools validate` then prove the resulting Component
has a valid closed graph.

Linear-resource capability mode is not widened by this ADR. An option/result
payload is a value, not proof that provider authority itself was consumed
linearly; the existing resource-mode admission continues to accept only its
qualified scalar call shape.

## Security properties

- capability authority is a named WIT import, never ambient WASI;
- source policy must explicitly allow the numeric capability effect;
- request/result descriptor equality is checked in both KIR and WIT;
- application imports and provider exports derive type spelling from one
  renderer;
- provider dispatch rejects an out-of-range discriminant before interpreting
  payload bits;
- aggregate and resource-owning payloads remain fail-closed.

## Evidence

Two `.kotoba` programs use an explicitly declared and policy-allowed
`:http/post` typed capability with `option<s64>` and `result<s64,s64>`.
`compile-component` produces the application Component and its
`:aiueos-http-post` ability identity. Independently packaged identity providers
close each application with no remaining import.

The pinned real Wasmtime engine executes `none`, `some(7)`, `ok(8)`, and
`err(-9)` through the composed application/provider boundary. A direct
invocation of the provider core export with discriminant `2` traps.

## Remaining gaps

- request and result structural unions with different descriptors;
- recursive record/string/list/nested-union payloads;
- production provider semantics instead of the wiring-only identity fixture;
- aggregate exhaustive matches around the call (heterogeneous
  i64/f32/f64/bool matching is implemented by ADR 0082);
- portable host adapters beyond the already standardized Component artifact.
