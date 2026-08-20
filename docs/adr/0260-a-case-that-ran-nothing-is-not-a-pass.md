# ADR 0260: a case that ran nothing is not a pass

Status: accepted

## Context

ADR 0259 fixed a suite that could report success having executed nothing. This
is the same class one layer down, in `kotoba.compiler.lang-conformance`: there a
whole SUITE could pass over nothing; here a single CASE can.

`run-case` drives each required backend and folds the results:

```clojure
kir  (when (contains? required :kir) (run-kir ...))
wasm (when (contains? required :wasm32-kotoba-v1) (run-wasm32 ...))
kir-ok?  (or (nil? kir)  (and (:ok? kir)  (= expect (:result kir))))
wasm-ok? (or (nil? wasm) (and (:ok? wasm) (= expect (:result wasm))))
ok? (and kir-ok? wasm-ok?)
```

Each `(or (nil? …) …)` is correct on its own — `nil` means "this case does not
require that backend", which is a real and legitimate configuration, and it
would be wrong to fail on it. What was missing is the conjunction: **when every
backend is nil, `ok?` is true and the case asserts nothing while reporting
`:passed`.**

Reachable by a plain typo. Measured 2026-08-19 by driving it rather than
reasoning about it — giving a real case `:required-backends
#{:wasm32-kotoba-v1-TYPO}` returns

```clojure
{:ok? true :status :passed :kir nil :wasm32-kotoba-v1 nil}
```

and the case is **still selected into the suite**, because `pure-product-cases`
also matches on `:class :pure-product-run`, which all 61 cases carry. So a
renamed or mistyped backend converts cases into green no-ops **without moving a
single count** — no drop in `:total`, no drop in `:passed`.

The same function's suite level carried ADR 0259's other instance too:
`(run-suite {:cases []})` gave `{:ok? true :total 0 :passed 0}`, since
`(empty? failed)` is satisfied by having no cases.

## Decision

A case is a pass only if at least one backend actually ran, and only if every
name in `:required-backends` is one this runner knows. `:status` distinguishes
`:unknown-backend` from `:no-backend-ran`, because a typo and an empty
requirement want different repairs — the first is a name to correct, the second
is a case with nothing to assert.

`run-suite` reports `:status :measured` / `:no-cases`, and `:ok?` requires at
least one case.

## Latent, not active

All 61 cases declare exactly `#{:kir :wasm32-kotoba-v1}`, and the suite runs
61/61 green before and after. No green no-op exists today; what exists is a
mechanism that would produce one silently, which is why the evidence below is a
driven reproduction rather than a receipt.

## Evidence

`lang_conformance_test.clj`, three new tests:

| case | status | ok? |
| --- | --- | --- |
| `:required-backends #{:wasm32-kotoba-v1-TYPO}` | `:unknown-backend` | false |
| `:required-backends #{}` | `:no-backend-ran` | false |
| the real case, unmodified | `:passed` | true, ran both |
| `(run-suite {:cases []})` | `:no-cases` | false |

The third row is the floor's own floor: it must not cost a genuine pass.

Removing the two guards fails exactly three assertions, each `actual:` showing
`(not (false? true))` — the old verdict. Restored: 10 tests, 275 assertions,
0 failures in this namespace; 1,102 tests and 8,318 assertions across amu.

## What this does NOT claim

- that a green no-op was ever emitted — all 61 cases declare the full set
- that the other conformance scripts under `scripts/` share the shape; they were
  surveyed for skip vocabulary and only `android-ndk-conformance.cljs` has any,
  which is not yet examined
