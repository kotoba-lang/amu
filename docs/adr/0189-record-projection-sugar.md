# ADR 0189: `(record-get value :field)` — type-directed projection sugar

- Status: Accepted
- Date: 2026-07-29
- WBS: follow-on to T4.4 / T5.3

## Context

`record-get` takes the schema descriptor as its first argument because lowering
is static. That forced every projection site to repeat the whole literal.
`kotoba-lang/murakumo`'s T5.3 rewrite ended up with **13 copies** of
`[:record :rebalance/lanes [[:text :i64] [:media :i64] [:postproc :i64]]]` in
one module:

```kotoba
(defn seats-of-text [total :i64 wt :i64 wm :i64 wp :i64 floor :i64] :i64
  (record-get [:record :rebalance/lanes
               [[:text :i64] [:media :i64] [:postproc :i64]]]
              (seats-record total wt wm wp floor) :text))
```

The type of the value is already known during inference, so the descriptor is
derivable rather than something the author must retype.

kotoba-lang's `ADR-reliability-record-access-and-bool-comparisons` recorded that
this needs a type-directed rewrite point, and that unlike bool-typed
comparisons it is **contained to this repo** — no `kotoba-kir` / `kotoba-wasm`
change. That holds: the rewrite emits the canonical 3-arity form.

## Decision

`(record-get value :field)` is admitted. `rewrite-record-projections` runs
between named-operation elaboration and validation, and rewrites it to
`(record-get SCHEMA value :field)` using `infer-expression-type` on the value.

- `let` is the only binding form that survives to this stage (`loop` / `fn` are
  already lowered to helpers), so it is threaded explicitly; everything else
  recurses structurally. Vectors — including type descriptors — are returned
  untouched because they are not seqs.
- Only modules that declare param types are rewritten. An untyped module
  cannot resolve the sugar and fails closed in validation exactly as before.
- A non-record value is rejected with `:kotoba.error/record-projection-unresolved`
  naming the inferred type.
- Field validation is unchanged: the rewrite supplies the schema, then the
  existing "field must be a declared keyword literal" check runs.

`validate-expr`, `infer-call-type`, lowering and every backend continue to see
only the 3-arity form.

## Evidence

- `kotoba.compiler.record-projection-sugar-test` — 8 tests, 10 assertions, 0
  failures: let-bound record, record parameter, call result, repeated
  projection inside one expression, 3-arity unchanged, and three fail-closed
  cases (non-record value, wrong arity, undeclared field).
- `clojure -M:conformance` → **52 / 52 passed (47 pure-product, 5 portable)** —
  unchanged.
- `clojure -M:test` → 716 tests, 6104 assertions, **1 failure**:
  `dual-renderer-soft-performance-workload`, a wall-clock soft budget that also
  fails on pristine `main` under load.

Follow-up (2026-08-11): in-process KIR and host-value performance gates now use
current-thread CPU time while retaining wall time as diagnostic output. This
keeps the original 5s/3s/2s computational budgets without treating unrelated
scheduler pauses as compiler regressions; subprocess ESM remains wall-clock.

## Not in scope

The other half of the kotoba-lang ADR — making `<`/`<=`/`>`/`>=`/`=` return
`:bool` so predicates can be written with `and`/`or`/`not` instead of i64
arithmetic — is a `compiler` + `kotoba-kir` + `kotoba-wasm` slice and is
deliberately untouched here.

`record-assoc` and `record-equal` keep their explicit descriptors; only the
projection had the repetition problem worth solving.
