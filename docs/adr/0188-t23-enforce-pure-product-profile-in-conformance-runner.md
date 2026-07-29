# ADR 0188: T2.3 — enforce the pure-product profile in the T1.3 runner

- Status: Accepted
- Date: 2026-07-29
- WBS: T2.3 (partial) / T2.1 / T1.3

## Context

The T2 exit criterion is *if it typechecks under pure-product, it runs on product
KIR + wasm*. T2.1 landed the admission check (`:language-profile :pure-product`,
compiler#411) and T1.3 grew a 52-case dual-backend suite. But the two were never
wired together: `run-kir` / `run-wasm32` call

```clojure
(compiler/compile-source source :wasm32-kotoba-v1 {} opts)
```

with policy `{}` — the profile is never applied. `pure-product-cases` selects on
`:class :pure-product-run` / `:required-backends`, so the label was decorative.

Checking all 52 cases against `check-source` with the profile shows the drift:

```
total 52 → admitted 47, rejected 5
  :portable-negative-and-advanced-threading-sugar  cond->>
  :portable-bounded-dotimes                        dotimes
  :portable-closed-world-multimethod               defmethod
  :portable-static-predicate-condp                 condp
  :thread-kit                                      ->
```

All five use heads in `pure-product-disallowed-heads`. They are legitimate
*portable* conformance cases; they are not pure-product surface. The headline
`52 / 52 pure-product dual-backend passed` therefore overstated pure-product
coverage by five cases.

`record-kit` is **among the 47 admitted** — records already compile and execute
under the profile on both backends. The gap flagged in root ADR-2607299400 is
narrower than stated there: it is `pure-product-profile.edn` documentation and
the untouched T5.3 rewrite, not compiler capability.

## Decision

1. Cases carry an optional `:language-profile`, defaulting to `:pure-product`.
   The five portable-only cases declare `:language-profile :portable`.
2. `run-case` calls `check-source` with the profile before executing a case
   labelled `:pure-product`. Rejection yields `:status :profile-rejected`.
3. `run-suite` reports `:pure-product-passed` / `:portable-passed` separately,
   and the CLI prints the split. One merged number hid the drift.
4. Admission runs as a **separate check**, not by threading the profile into
   `compile-source` policy, so artifact bytes and T1.5 goldens are unchanged.

## Evidence

- `clojure -M:conformance` → `52 / 52 passed (47 pure-product, 5 portable)`
- `kotoba.compiler.lang-conformance-test` → 7 tests, 222 assertions, 0 failures
  - `every-pure-product-case-passes-profile-admission` (47 / 5 split asserted)
  - `pure-product-label-on-forbidden-surface-is-rejected` (mislabelling condp as
    pure-product fails closed with `:kotoba.error/pure-product-forbidden`)
  - `suite-reports-profile-split`
- T1.5 goldens untouched (`digest-case` compile path unchanged).

## Scope

This closes the runner half of T2.3. The `examples/` CI job (every
`pure-product` example under `examples/` compiles + KIR-executes) is still open;
T2.3 should not be marked landed on the strength of this ADR alone.
