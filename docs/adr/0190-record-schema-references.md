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
gate executes. Worth a follow-up check that no other namespace under `test/` is
missing from the runner.

## Evidence

- `record-projection-sugar-test` — 14 tests, 17 assertions, 0 failures
  (4 new: ref in parameter annotation, ref in return annotation, ref as a record
  op type argument, undeclared ref fails closed)
- `clojure -M:conformance` → **52 / 52 passed (47 pure-product, 5 portable)**
- `clojure -M:test` → **730 tests, 6121 assertions, 0 failures**

## Related

- `docs/adr/0189-record-projection-sugar.md`
- kotoba-lang `ADR-reliability-record-access-and-bool-comparisons`
- murakumo `ADR-260730-w6-t53-plan-lr-record.md` (the four remaining pack families)
