# ADR 0206: type-directed collection access

Status: accepted

## Context

Kotoba already had exact primitives for bounded heterogeneous vectors, typed
maps, and records. Ordinary `nth` and `get`, however, could not select those
primitives from an inferred receiver type. Authors had to repeat complete type
descriptors at projection sites, or abandon the ordinary collection spelling.
That was compiler-shaped plumbing and blocked the type-directed nested
projection design in ADR 0022 Phase 4.

## Decision

After ordinary expression and local type inference, the frontend specializes
surface collection operations to existing closed primitives:

```clojure
(nth values 1)
;; => (hetero-vector-at [:vector [:i64 :string :bool]] values 1)

(get names :user)
;; => (typed-map-get [:map :keyword :string] names :user)

(get person :name)
;; => (record-get Person person :name)
```

The descriptors are derived from receiver types; they are neither runtime
inspection nor authored source. Each expression retains its exact result type:
the heterogeneous child type, `[:option value-type]` for a two-argument typed
map lookup, the map value type for a lookup with a default, or the declared
record field type. Legacy `:map` lookup continues to select `map-get`.

## Bounds and safety

A heterogeneous index must be an in-range integer literal. A dynamic index
cannot have one statically known result type when child descriptors differ, so
it fails closed. Optional-default heterogeneous `nth` is outside this slice for
the same reason.

Typed-map keys and defaults must match the declared key and value types. Record
keys must be declared keyword fields, and records do not admit a lookup default.
Ordinary homogeneous or project-defined `nth` calls are left unchanged.

## Evidence

- `type-directed-access-test` covers exact string/bool child preservation,
  typed-map option/default results, record fields, and rejection paths.
- `:type-directed-heterogeneous-nth` executes ordinary authored `nth` on KIR
  and `wasm32-kotoba-v1` with result `3`.
