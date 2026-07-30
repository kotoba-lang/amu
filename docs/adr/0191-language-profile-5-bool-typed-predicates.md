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

## Status: not landed — the remaining work, measured

Do not read the Evidence section below as the current state. It described the
frontend change alone. With `kotoba-wasm` carrying bool-as-word, the compiler
suite is **749 tests / 6158 assertions, 18 failures, 0 errors** and conformance
is 52/52. Four of the 18 are the wall-clock perf budgets that also fail on
pristine `main` under load, so **14 are real**, and they are not one problem.

An earlier note in this series claimed three irreconcilable requirements (word
inside wasm / JS boolean at the boundary / JS boolean in ESM) and concluded the
design was blocked. **That was wrong** — it read a validation bug as a design
conflict. The requirements are not in tension: they belong to different layers.
A bool is a word *inside* a module and a host boolean *at a boundary*, and
boxing at the boundary is one operation that already half exists.

### A. Aggregate element slots typed `:bool`

    (hetero-vector [:vector [:i64 :string :bool]] 7 "safe" true)

fails with `invalid-module`, not with a wrong value: the element is now an i64
word where the container's slot expects an externref. Same shape for a `:bool`
record field and a `:bool` typed-map value.

- write: `i32.wrap_i64` → `typed-bool` → store as a ref. The host keeps
  validating the slot as a real JS boolean (`browser-host.mjs`: *"typed boolean
  is invalid"* unless `typeof value === "boolean"`), so nothing there changes.
- read: needs **one new intrinsic**, `typed-bool-value` (externref → i32), then
  `i64.extend_i32_u`. `typed-get-i64` will not do — the slot holds a boolean, not
  an i64. This is the only genuinely new host surface the whole change requires,
  and it needs an implementation in `browser-host.mjs` and in the JVM/Chicory
  host.

### B. Export boundary

    (defn strings-match [] :bool (if (string=? "same" "same") true false))

`wasm_typed_test.clj` calls `h.instance.exports['strings-match']()` — the raw
instance, not a host wrapper — and requires `=== true`. A host-side wrapper
therefore cannot fix this; the exported function itself must return the boxed
value. Emit a wrapper per exported function whose declared result is `:bool`:
call the internal (i64-word) function, `i32.wrap_i64`, `typed-bool`, return
externref; export the wrapper under the original name. Params typed `:bool`
unbox the same way on the way in.

`typed-bool` already exists in the import table as `[0x60 1 0x7f 1 0x6f]`
(i32 → externref) and the host already implements it. A and B are the same
operation in the two directions.

### C. Migration, not repair

    (defn same? [left :option-i64 right :option-i64] (= left right))

now returns a bool, so `x['same?'](…)` is `true` rather than `1n`. That is the
point of the profile, and the expectation moves with it — but only where the
function's result actually became `:bool`. `hetero-vector-equal`,
`typed-set-equal` and `record-equal` are a **separate family that stays `:i64`**;
three call sites were migrated by an over-broad substitution earlier and had to
be reverted. Check each site, do not pattern-match on the name.

T1.5 goldens drift on the **wasm digest only** — every `kir-sha256` is
unchanged. That is a useful confirmation that this is an emission change and not
a language-level one, and it is why regenerating them is safe.

### Order

A (unblocks the corpus and document parity), then B (unblocks the typed
control-flow tests), then C (mechanical, and pointless before A and B settle the
emitted bytes).

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
