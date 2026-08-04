# ADR 0203 — Contextual result inference for computed closure calls

## Status

Accepted, 2026-08-04.

## Context

Kotoba uses ordinary `(f x)` application when `f` is a lexical closure. A
genuinely computed closure head uses `invoke` so the dynamic boundary remains
visible and statically bounded. The compiler previously required an explicit
result descriptor for every non-i64 computed call:

```clojure
(string-length (invoke :string renderer 42))
```

That descriptor duplicated information already supplied by a typed consumer,
function result annotation, or another closed elaboration context. It made the
rare dynamic boundary more verbose than necessary without adding authority or
runtime validation.

## Decision

When `invoke` has no explicit result descriptor, reuse the canonical closed
result type supplied by its elaboration context. Thus the example becomes:

```clojure
(string-length (invoke renderer 42))
```

The rule applies uniformly to scalar, document, numeric, vector, nominal
record, and parameterized result descriptors already admitted by the closure
dispatcher profile. An explicit descriptor remains accepted and remains
necessary when the surrounding expression does not determine a result family.
With no descriptor and no result context, `invoke` retains its historical
`:i64` default.

This is elaboration only. KIR still names a result-family-specific bounded
dispatcher, malformed closures and wrong-family lambdas still trap, and no
runtime type guessing or ambient dynamic dispatch is introduced.

## Consequences

- typed consumers and annotated return positions do not repeat descriptors;
- genuinely ambiguous computed calls remain explicit;
- existing source is unchanged and existing explicit descriptors remain valid;
- restricted ESM and Wasm receive the same typed KIR and fail-closed checks.

## Verification

`kotoba.compiler.callable-values-test` covers contextual string, document,
f64, vector, record, and typed-function-return calls, the context-free i64
default, wrong-family trapping, restricted ESM execution, KIR parity, and
deterministic Wasm bytes.
