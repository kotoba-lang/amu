# ADR 0217: Closed-world `extend-protocol`

Status: accepted

## Context

The canonical compiler already lowers record-local protocol implementations
and `extend-type` to private static functions. It rejected
`extend-protocol`, although the admitted grammar and primary runtimes expose
that familiar grouping form. Copying the primary runtime's dynamic default
would be wrong: an unknown tag currently falls through to a zero sentinel,
which is neither a value of every result type nor a truthful capability-safe
failure mode.

## Decision

Admit `extend-protocol` over records declared in the same closed module:

```clojure
(extend-protocol Value
  Special
  (value [this] (+ 100 (:x this)))

  default
  (value [this] (:x this)))
```

Named sections are equivalent to their `extend-type` spelling. A single
`default` section is statically copied to each declared nominal record that
does not already implement that protocol. Record-local, `extend-type`, and
named `extend-protocol` implementations take precedence by being explicit;
duplicates remain compile errors.

The default is not emitted as runtime fallback code. Calls still require a
statically inferred nominal receiver and resolve directly to one private
implementation. An integer, unknown type, unimplemented record, or record from
outside the sealed module is rejected instead of receiving zero or an invented
value. A default without any declared record specialization target is rejected
as meaningless in this profile.

Every section must implement every protocol method exactly once with the
declared bounded arity. Each specialized default body is checked against the
target record descriptor, so field access must be valid for every record to
which the default applies.

## Consequences

- Authors may group implementations by protocol using ordinary Clojure-shaped
  syntax without adding reflection or runtime tag dispatch.
- `default` is convenient closed-world source sugar, not an open-world object
  fallback. Adding external nominal types requires recompiling the sealed
  module and rechecking the specialization set.
- The legacy primary zero-sentinel path remains a parity defect to remove; it
  is not adopted by the canonical language.
- Expansion introduces no KIR, Wasm, host ABI, effect, or capability primitive.

## Evidence

`record-protocol-static-dispatch-test` executes named sections and explicit
precedence over a default, proves deterministic Wasm output, rejects a dynamic
non-record receiver, and covers malformed defaults. The JVM-free
`static-extend-protocol` NBB fixture compiles the same form to browser Wasm.
