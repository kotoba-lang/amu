# ADR 0191: language profile 5 — bool-typed predicates, inferred results, keyword accessor

- Status: Accepted
- Date: 2026-07-30
- WBS: closes the bool half of kotoba-lang `ADR-reliability-record-access-and-bool-comparisons`
- Breaking: yes — language profile 4 → 5, `version-policy.edn` deprecation window

## Context

Profile 4 made comparisons and predicates `:i64`, so booleans were arithmetic
values and `(+ (zero? x) (pos? x))` was admitted. The consequence was that no
predicate could be written the way Clojure writes one — `and` / `or` / `not`
could not compose, and every product predicate degenerated into nested
`(if (= flag 0) 0 …)` over bit-packed i64 flags.

Owner decision (2026-07-30): break it. Keep the writing surface Clojure-shaped so
an LLM writing Clojure produces valid Kotoba; add to Kotoba only what safety and
static lowering force.

## Decision

### 1. Comparisons and predicates are `:bool`

`= < > <= >=` infer `:bool`, and so do `zero?` / `pos?` / `neg?` / `empty?` /
`not` / `not=` / `some?` and comparison chains. The whole boolean layer had been
expressed as integer comparison against `0`, so four desugars changed with it:

| Site | Was | Now |
|---|---|---|
| `not` / `not=` | `(= x 0)` | `(if x false true)` |
| `if-not` / `when-not` | `(= test 0)` | swap the branches |
| `desugar-comparison-chain` | folds to `1` / `0` | folds to `true` / `false` |

`if` accepts a boolean **or** a legacy 0/1 integer test, so an
integer-conditioned program keeps working.

### 2. `:bool` is a plain 0/1 word — it does not promote the value profile

This was the real blocker, and it is a representation decision, not a version
one. Before: one `:bool` anywhere moved a module from `:kotoba.value/i64-v1` to
`:typed-v1`, and `typed-v1`'s Wasm emitter does not qualify `pair-first` /
`pair-second` — so **a module could not use a boolean and a list at the same
time**, and a `:bool`-declared export failed to compile at all.

`:bool` is now excluded from the typed-values promotion set. Paired changes:

- `kotoba-wasm` — the i64-v1 emitter emits a `true` / `false` literal as the
  same `i64.const 1/0` the comparison sequence already produces
- `kotoba-kir` — `:bool` runtime validation accepts the 0/1 word as well as a
  host boolean (`document-bool` and the other typed-value carriers still need a
  real boolean, so literals stay booleans there)

Measured after: pair operations + a bool, and a `:bool`-returning export, both
compile and run on wasm32.

### 3. An unannotated `defn` infers its result type

An absent annotation used to mean `:i64`, so an unannotated function could not
return a predicate — which is most of the stdlib, the examples and the test
fixtures. `infer-absent-results` now gives it the body's inferred type, in two
passes because one function's result feeds the next one's inference. A body whose
type cannot be resolved keeps the `:i64` provisional so `check-value-types!`
reports the real error rather than a spurious one.

This is the Clojure reading (no annotation means no constraint) and it is what
keeps **one** dialect: annotations are for boundaries, not for every function.

### 4. `(:field r)` — the Clojure keyword accessor

Desugars to the 2-arity `record-get` (ADR 0189), which the projection rewrite
resolves against the value's inferred type, including through a `[:ref :ns/name]`
schema reference (ADR 0190). **No new head reaches validation, inference or any
backend** — the accessor exists only in the desugar.

## What this makes writable

```kotoba
(defn eligible? [node model]
  (and (:has-engine node)
       (or (not (:has-checkpoint node)) (:holds-checkpoint node))
       (>= (:free-bytes node) (:min-free model))))
```

The same function under profile 4, in `kotoba-lang/murakumo`:

```kotoba
(defn bit? [flags :i64 mask :i64] :i64
  (if (= 0 (rem64 (quot flags mask) 2)) 0 1))
(defn eligible? [flags :i64 free-bytes :i64 min-free :i64] :i64
  (let [has-engine (bit? flags 1) has-ckpt (bit? flags 2) …
        ckpt-ok (if (= has-ckpt 0) 1 (if (= holds 1) 1 (if (= can-fetch 1) 1 0)))]
    (if (= has-engine 0) 0 (if (= ckpt-ok 0) 0 mem-ok))))
```

## Migration

Mechanical, and it moves **toward** Clojure: where a number was wanted from a
predicate, write `(if p 1 0)`. In Clojure `(+ (zero? x) (pos? x))` is a type
error too, so the idiom profile 4 admitted was the non-Clojure one.

Six source sites in this repo's own tests were migrated, and the property-corpus
generator now wraps a comparison used as a *value* (as an `if` *test* it needs no
wrapper). T1.5 goldens regenerated — the desugar changed, so the digests did.

`lang/version-policy.edn` records profile 4 as deprecated on 2026-07-30 with
`removal-not-before 2027-01-26` (the 180-day window), release 0.4.0 → 0.5.0.

## Every target boxes `:bool` at its own boundary

An earlier note in this series claimed three irreconcilable requirements -- a
word inside wasm, a JS boolean at the host boundary, a JS boolean in ESM -- and
concluded the design was blocked. **That was wrong.** It read a validation bug
as a design conflict. The requirements are not in tension; they belong to
different layers, and each was a missing conversion at one boundary.

The resolved rule is a single sentence:

> `:bool` is a plain 0/1 word **inside** a target and a host boolean at every
> point where a value **leaves** it.

Inside is what makes `and`/`or`/`not`, `if` tests, locals, branches and indirect
calls typecheck. Outside is what the shared corpora demand: reference,
restricted-ESM and wasm32 must return the *same* value for the *same* function.

| target | boundary | conversion |
|---|---|---|
| wasm32 | aggregate element slot (`hetero-vector`, record field, typed-map value) | `i32.wrap_i64` → `typed-bool`; read back through `typed-bool-value` |
| wasm32 | `document-bool` | same box -- it takes an externref |
| wasm32 | export | a thin wrapper function; the export section points at it |
| reference (KIR) | `execute` return | 0/1 → boolean when the function's result is `:bool` |
| restricted ESM | function result | `assertBool`, including in an **untyped** (v3) module |

`typed-bool-value` (externref → i32) is the one new host surface the whole
change required. `get-i64` could not serve: the slot holds a boolean, not a
bigint.

Two consequences worth stating plainly:

- `requires-host-runtime?` is now true for a module with a `:bool` export. It
  has to be -- the wrapper calls `typed-bool` -- and it is simply accurate: the
  value crossing the boundary *is* a host value. Gated on `(not native-bool?)`,
  since the canonical-scalar Component adapter lowers `:bool` to i32 in the
  signature and emits no wrapper.
- An **untyped** KIR module can now carry a `:bool` result, because comparisons
  infer `:bool` and an unannotated `defn` takes its body's type. `kotoba-script`
  forced every v3 result to `:i64`, so it wrapped a boolean in `assertI64` and
  every such export threw `invalid-i64` on its first call -- including
  `(defn test-pure [] (= (+ 20 22) 42))`, which is what a Kotoba test looks
  like.

### Migration

Where a predicate legitimately became a bool, the expectation moves with it:
`(defn same? [l r] (= l r))` now answers `true`, not `1n`. **Only where the
result actually became `:bool`.** `hetero-vector-equal`, `typed-set-equal` and
`record-equal` are a separate family that stays `:i64`; three call sites were
changed by an over-broad substitution earlier and had to be reverted. Check each
site; do not pattern-match on the name.

T1.5 goldens drift on the **wasm digest only** -- all 52 changed lines are
`:wasm-sha256` / `:wasm-byte-count`, and **not one `:kir-sha256` changed**. That
is a useful confirmation that this is an emission change and not a language-level
one.

### The negative corpus was not testing its own name

`:floating-literal` `(defn main [] 1.5)` stopped failing closed here, which
looked like a safety regression. It was not: that case only ever rejected
because an absent annotation meant `:i64`, so the body mismatched.
`(defn main [] :f64 1.5)` has always been accepted, and there is an extensive
f64 suite. Its sibling `:floating-descriptor` was rejected by **"main must take
zero arguments"**. Neither excluded floating point, because nothing does.

Replaced with the rule each one really exercises -- `:floating-set-item` (a
direct float in a `:set`, which *is* excluded) and
`:entry-point-takes-arguments` -- so the id and the rejection agree.

## Evidence

| state | compiler suite |
|---|---|
| bool-as-word alone | 18 failures |
| + aggregate element boxing | 12 |
| + `document-bool` boxing | 9 |
| + export wrappers | 4 |
| + KIR return boxing, ESM v3 result, expectation migration, goldens | **0** |

Final: `clojure -M:test` **749 tests / 6158 assertions / 0 failures / 0 errors**;
`clojure -M:conformance` **52 / 52 dual-backend** (47 pure-product, 5 portable).
Siblings: `kotoba-wasm` 83/397, `kotoba-kir` 59/258, `kotoba-script` 51/183 --
all 0 failures, and all three now have CI, so those runs are checked rather than
asserted.

## Evidence (frontend change only, superseded by the section above)

- `clojure -M:conformance` → **52 / 52 dual-backend** (47 pure-product, 5 portable)
- `clojure -M:test` → see the PR; the only residual failures are the wall-clock
  perf budgets that also fail on pristine `main` under load
- `kotoba-kir` 59 tests / 258 assertions, `kotoba-wasm` 83 / 397 — both 0 failures
  (all three repos have CI as of 2026-07-30, so this is no longer the gate)

## Related

- `docs/adr/0189-record-projection-sugar.md`
- `docs/adr/0190-record-schema-references.md`
- kotoba-lang `docs/adr/ADR-reliability-record-access-and-bool-comparisons.md`
- kotoba-lang `lang/surface-status.edn` `:bool-is-a-type-not-a-number`
