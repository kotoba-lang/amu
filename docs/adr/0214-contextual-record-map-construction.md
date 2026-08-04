# ADR 0214: Contextual record map construction

Status: accepted

## Context

`map->Type` accepted only one literal map. That was exact and safe, but it made
ordinary computed construction needlessly repetitive: authors had to place the
constructor around every branch even though the constructor itself already
declared one nominal result type.

```clojure
(if enabled
  (map->Person {:name "Ada" :active true})
  (map->Person {:name fallback :active false}))
```

Accepting an arbitrary map expression would be the wrong correction. Kotoba
does not have a dynamically shaped record boundary, and guessing a nominal
identity or field types at runtime would weaken the closed KIR and Wasm value
model.

## Decision

The nominal context introduced by `map->Type` propagates through the result
positions of bounded, total control forms:

- `if`, `if-not`, `if-let`, and `if-some` with both branches;
- `cond` with a final `:else`;
- `case` and `condp` with a default;
- the final expression of `let` and `do`.

Every reachable result leaf must remain a literal map whose key set exactly
matches the declared record fields. Each leaf lowers directly to `record-new`
with values ordered by the declaration. Tests, binding values, dispatch
expressions, and non-final `do` forms retain their ordinary expression context.

```clojure
(map->Person
  (let [fallback "Grace"]
    (if enabled
      {:name "Ada" :active true}
      {:name fallback :active false})))
```

Missing branches or defaults, wrong key sets, and arbitrary map variables are
rejected. This ADR therefore admits computed control, not dynamic record
reflection. It supersedes ADR 0208's literal-only statement without changing
the positional constructor or callable ABI.

## Syntax assessment

The type and nominal identity are written once, at the boundary that owns
them. Branches retain ordinary EDN map shape, so the source reads as one value
selected by control flow instead of repeated conversions. The exact-leaf rule
keeps that concision honest: ambiguity is rejected rather than hidden behind
runtime coercion.

This is the aesthetically preferred bounded surface. A future general
map-to-record conversion would need an explicit checked operation and a
truthful dynamic-map representation; it must not silently broaden
`map->Type`.

## Evidence

`record-protocol-static-dispatch-test` covers heterogeneous typed fields,
`let`/`do`, every admitted conditional family, missing-totality and wrong-shape
rejection, exact `record-new` lowering, and execution on reference KIR,
restricted ESM, and browser Wasm.

The full JVM suite passes 918 tests / 6,921 assertions. The JVM-free NBB Wasm
suite includes a dedicated computed-record fixture and passes all 37 cases.
