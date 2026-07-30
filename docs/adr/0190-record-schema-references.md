# ADR 0190: named schema references in record operations

- Status: Accepted
- Date: 2026-07-30
- WBS: follow-on to ADR 0189; unblocks T5.3 for widely-threaded records

## Context

ADR 0189 removed the descriptor from *projection* sites. It did not remove it
from **annotations**, and that is what blocks the remaining T5.3 lanes.

`murakumo`'s `infer_plan_core.kotoba` threads its `model-pack` value through
**16 signatures**. Converting it to a record with inline descriptors would put
16 copies of `[:record :plan/model [[:layers :i64] [:dense :i64]
[:dense-frac-milli :i64]]]` in one file — strictly *worse* to read than the
base-65536 pack it replaces. Applying the T5.3 pattern there was therefore the
wrong move until this was fixed.

The mechanism already existed and was simply unusable: `schema-ref-type?`
(`[:ref :ns/name]`), the `(ns … (:schemas {…}))` clause, and
`same-expression-type?`'s rule that *"a closed-schema reference and its fully
declared nominal descriptor are interchangeable by the same qualified
identity"*. Measured against `compiler@1ad763fb`:

| Form | Before |
|---|---|
| `[:ref :m/model]` as a parameter annotation | rejected — `record-get … got [:ref :m/model]` |
| `[:ref :m/model]` as a return annotation | rejected, same |
| `(record-new [:ref :m/model] …)` | `record field must be a declared keyword literal` |

Annotations parsed fine; the **record operations** were what refused to resolve
a reference.

## Decision

`rewrite-record-projection` resolves `[:ref :ns/name]` through the namespace's
closed `:schemas` map, in two places:

1. the 2-arity `(record-get value :field)` sugar, when the value's inferred type
   is a reference;
2. the **type argument** of `record-new` / `record-get` / `record-assoc` /
   `record-equal`.

Downstream passes therefore keep seeing only inline descriptors — validation,
inference and lowering are untouched, same containment property as ADR 0189.
Annotations in parameter/return position need no rewrite at all; nominal
equivalence already covered them.

An undeclared reference fails closed with
`:kotoba.error/record-projection-unresolved` naming the missing schema.

So a widely-threaded record now reads:

```kotoba
(ns plan (:schemas {:plan/model [:record :plan/model
                                 [[:layers :i64] [:dense :i64] [:frac :i64]]]}))

(defn layer-byte-at [weight-bytes :i64 mp [:ref :plan/model] i :i64] :i64
  (record-get mp :layers) …)
```

## A gap this uncovered: the test namespace was never in the gate

`clojure -M:test` runs an explicit list in `test/kotoba/compiler/test_runner.clj`
— both a `:require` vector and a second literal list inside `-main`.
`record-projection-sugar-test`, added by ADR 0189 (#441) and extended by #442,
was in **neither**. The suite reported an unchanged `716 tests / 6104
assertions` across both PRs, so those tests only ever ran when invoked directly.

Registered in both places. The suite now reports **730 tests / 6121
assertions** — exactly the 14 tests and 17 assertions that had been invisible.

This is the same defect class as the orphaned `:record-protocol-static-dispatch`
conformance case (kotoba-lang#343): a test that exists, passes when run, and no
gate executes it.

### The sweep, since one instance implied more

`test/kotoba/compiler/` holds 103 namespaces; the `-main` list named 90. **Twelve
were on disk and ungated.** Each was run before deciding what to do with it:

| Namespace | tests | pass | fail |
|---|---|---|---|
| `map-filter-vector-test` | 4 | 7 | 0 |
| `multi-map-test` | 3 | 3 | 0 |
| `named-hof-test` | 3 | 3 | 0 |
| `reduce-named-test` | 1 | 2 | 0 |
| `reduce-vector-test` | 2 | 4 | 0 |
| `schema-metadata-test` | 2 | 5 | 0 |
| `schema-test` | 3 | 9 | 0 |
| `test-profile-test` | 1 | 4 | 0 |
| `named-ability-elaboration-test` | 5 | 9 | **1** |
| `symbol-operation-test` | 2 | 4 | **1** |
| `w1-elaboration-test` | 7 | 36 | **6** |
| `string-literal-operation-test` | 2 | **0** | **4** |

The eight green ones are registered. The gate goes from 716 / 6104 to
**749 / 6158**.

The four red ones are **deliberately left unregistered** — registering them would
red the gate, and fixing 12 assertions across four areas I have not studied is a
separate slice, not a side effect of this PR. Recorded here so they stop being
invisible:

- `string-literal-operation-test` (0 / 4) asserts `string-substring` is
  **literal-only**: that a `:string` parameter is rejected with *"requires a
  literal string"*, that out-of-bounds and non-code-point indices are rejected at
  analyze time, and that literals fold during analysis. All four now return `nil`
  instead of throwing, and the fold assertion sees an unevaluated call. That is
  consistent with dynamic `string-substring` having landed (surface-status:
  *"dynamic string results use allocation-checked descriptors"*) — the test
  encodes superseded literal-only semantics. Same shape as the stale nbb
  diagnostic code fixed in #439.
- `symbol-operation-test` (1 failure) fails inside `runtime/browser-host.mjs`
  with a `KotobaHostError`, so it is a host/runtime issue, not a pure assertion.
- `named-ability-elaboration-test` (1) and `w1-elaboration-test` (6) are W1
  elaboration-contract tests and need study before touching.

## Evidence

- `record-projection-sugar-test` — 14 tests, 17 assertions, 0 failures
  (4 new: ref in parameter annotation, ref in return annotation, ref as a record
  op type argument, undeclared ref fails closed)
- `clojure -M:conformance` → **52 / 52 passed (47 pure-product, 5 portable)**
- `clojure -M:test` → **749 tests, 6158 assertions, 0 failures**
  (716 / 6104 before this PR: +14/+17 from registering the namespace ADR 0189
  added, +19/+37 from the eight green namespaces the sweep found)

## Related

- `docs/adr/0189-record-projection-sugar.md`
- kotoba-lang `ADR-reliability-record-access-and-bool-comparisons`
- murakumo `ADR-260730-w6-t53-plan-lr-record.md` (the four remaining pack families)
