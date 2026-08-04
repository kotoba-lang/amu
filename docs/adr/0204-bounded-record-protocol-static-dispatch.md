# ADR 0204: bounded record and protocol static dispatch

Status: accepted

## Context

The primary Kotoba runtimes accept `defrecord`, `defprotocol`, and
`extend-type`, but the canonical compiler rejected those forms at top level.
Authors therefore had to repeat complete `[:record ...]` descriptors at every
constructor boundary, and the shared `record-protocol-static-dispatch`
conformance case was not executed by the compiler.

## Decision

The frontend expands a closed namespace's record and protocol declarations
before ordinary function analysis:

- `defrecord` fields are a bounded, unique symbol vector and are `:i64` in this
  first profile. The generated `->Type` constructor returns a nominal
  `[:record qualified-id ...]` value.
- `map->Type` accepts one literal map containing exactly the declared fields
  and lowers directly to the same nominal constructor.
- record-local protocol methods and `extend-type` methods become private,
  deterministically named functions whose receiver parameter carries that
  nominal record descriptor. Each protocol section implements every declared
  method exactly once; one `extend-type` may contain multiple protocol sections.
- a protocol call is rewritten from the statically inferred receiver type to
  the matching private implementation. Unknown, untyped, or unimplemented
  receivers are rejected; there is no reflection or runtime type guessing.

`definterface` shares the declaration contract. ADR 0217 subsequently admits
`extend-protocol`: named sections use the same static implementation path, and
one `default` section specializes only across otherwise-unimplemented nominal
records in the sealed module. It never becomes a dynamic fallback.

## Bounds and safety

Records and method arities obey the existing five-parameter ABI bound.
Protocol and ordinary function names may not collide, implementations must be
unique per protocol/method/record, and generated implementation functions are
private. The expansion introduces no new host capability, loader, ABI, or
backend operation: KIR and Wasm see only existing nominal record operations and
static calls.

## Evidence

- `record-protocol-static-dispatch-test`: constructors, lexical type flow,
  deterministic Wasm, and fail-closed diagnostics.
- `resources/kotoba/lang-conformance/values/record_protocol_static_dispatch.kotoba`:
  the authority fixture runs as pure product with result `16` on KIR and
  `wasm32-kotoba-v1`.
