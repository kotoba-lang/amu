# ADR 0207: type-directed nested destructuring

Status: accepted

## Context

ADR 0206 made ordinary `get` and `nth` type-directed, but destructuring still
expanded immediately to legacy `map-get` and `vector-at`. It also rejected a
pattern nested inside another pattern. Consequently a value could be projected
cleanly by hand while the equivalent data-shaped binding either selected the
wrong representation or was illegal.

## Decision

Composite bindings expand to deterministic temporary bindings and unresolved
projection forms. The existing post-inference rewrite then selects the exact
accessor from each receiver descriptor. Vector patterns may contain vector or
map patterns, and map patterns admit the familiar explicit keyword mapping:

```clojure
(let [[id [name active]] value] ...)

(let [{{:keys [name]} :profile} user] ...)
```

The latter is the Clojure-shaped binding-pattern-to-lookup-key direction; it
does not introduce dynamic keys. Flat `:keys`, `:or`, and `:as` remain
compatible. The source value and every intermediate nested value are bound once
before projection.

Homogeneous vectors select `vector-at`/`vector-get` or their f64 equivalents.
Heterogeneous vectors select `hetero-vector-at` and preserve the exact child
descriptor. Records select `record-get`. Legacy maps retain `map-get`.

## Missing values

A record field and a required heterogeneous position are structurally present.
A typed map lookup is not. Typed-map destructuring therefore requires an `:or`
default for each direct symbol binding rather than silently manufacturing a
payload or changing the local to an option. The default must have the declared
map value type and is evaluated only on a miss.

Heterogeneous `& rest` remains outside this slice because it needs a new sliced
descriptor. Homogeneous vector rest keeps the established `vector-drop`
behavior. `:strs`, `:syms`, and dynamic lookup keys remain outside the closed
keyword identity model.

## Evidence

- `type-directed-access-test` covers nested heterogeneous vectors, nested
  records, typed-map defaults, exact accessor erasure, and missing-default
  rejection.
- `frontend-destructuring-loop-test` retains legacy map/vector behavior and
  malformed-pattern diagnostics.
- `:nested-typed-destructuring` executes the composed surface on KIR and
  `wasm32-kotoba-v1`.
