# ADR 0205: typed `defrecord` fields

Status: accepted

## Context

ADR 0204 made nominal records pleasant to author, but its declaration surface
assigned `:i64` to every field. The lower compiler, KIR, restricted ESM, and
Wasm record paths already preserve complete field descriptors, so authors still
having to drop to `[:record ...]` for strings, booleans, options, and other
admitted value types was frontend-shaped plumbing rather than a backend bound.

## Decision

`defrecord` uses the same alternating name/type spelling as typed function
parameters:

```clojure
(defrecord Reading [label :string ok :bool value :i64])
```

An all-symbol field vector remains the concise `:i64` profile. A vector that
contains type descriptors must consist entirely of alternating field names and
admitted value types. Both generated constructors preserve the complete nominal
descriptor:

- `(->Reading "sensor" true 7)` has typed parameters;
- `(map->Reading {:value 7 :ok true :label "sensor"})` keeps exact literal-map
  admission and lowers its values in declaration order.

Projection remains type-directed through `(get record :field)` or
`(:field record)`. This decision does not introduce structural record matching,
dynamic heterogeneous maps, reflection, or runtime type guessing.

## Bounds and safety

The existing five-field constructor bound and unique-field rule are unchanged.
Every declared type passes the canonical value-type validator, constructor
arguments are checked against the descriptor, and malformed or partially typed
field vectors fail closed during declaration expansion.

## Evidence

- `record-protocol-static-dispatch-test` covers string/bool construction,
  literal `map->Type`, projection, and a wrong-type rejection.
- `:typed-defrecord-fields` executes the authored surface on KIR and
  `wasm32-kotoba-v1`.
