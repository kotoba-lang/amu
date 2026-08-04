# ADR 0213: Contextual document boundaries

Status: accepted

## Context

ADR 0200 admitted `(document literal)`, but the declared `:document` type was
not used while desugaring ordinary literals. Authors therefore had to repeat a
wrapper even when a function result or a typed capability request already made
the intended value family exact:

```clojure
(defn policy [] :document
  (document {:action :actor/run :attempt 3 :ready true}))
```

The same loss of context occurred at `typed-cap-call`: request and result
descriptors were retained in HIR, but the request expression was desugared as
an untyped expression first.

## Decision

A closed, unambiguous literal in a `:document` result context elaborates to the
existing document constructor tree without requiring `(document ...)`:

```clojure
(defn policy [] :document
  {:action :actor/run :attempt 3 :ready true})

(typed-cap-call :http/post :document :document
  {:action :actor/run :attempt 3 :ready true})
```

Both keyword and numeric typed capability forms propagate their declared
request type during desugaring. This is semantic typed lowering; it does not
introduce another wire encoding or claim that compiler KIR document values are
physical `kotoba.value.v1` bytes. The bounded codec adapter remains the owner of
that separate serialization boundary.

Automatic elaboration admits scalar literals and recursively closed
map/vector/set literals. A namespaced symbol is inert document data because it
cannot name a lexical value in the admitted source profile. Simple symbols and
lists remain expressions, so parameters and calls returning `:document` are
never silently converted into symbol/list data. Authors use explicit
`(document symbol-or-list)` when those EDN forms are intended as data.

## Syntax assessment

The resulting data surface is concise and structurally familiar: the type is
written once and the value retains ordinary EDN shape. The code/data boundary
is still visible at the two genuinely ambiguous forms rather than being
guessed by the compiler.

`typed-cap-call` remains a compiler-level boundary form and is not the ideal
application syntax: it repeats physical request/result descriptors. Qualified
ability calls such as `(http/post request)` remain the authored direction.
They can omit request descriptors only when the language-owned capability
catalog can infer the request type from the argument or eventually declares an
authoritative request schema; this ADR does not guess one.

## Evidence

`document-edn-test` proves that bare contextual syntax, explicit contextual
syntax, and the constructor tree produce identical HIR and values on reference
KIR, restricted ESM, and browser Wasm. `typed-capability-test` proves that a
closed request reaches the provider as the same `:document` value and that a
document-typed lexical request remains a lexical value.

The full JVM suite passes 914 tests / 6,903 assertions. The JVM-free NBB Wasm
suite passes all 36 cases.
