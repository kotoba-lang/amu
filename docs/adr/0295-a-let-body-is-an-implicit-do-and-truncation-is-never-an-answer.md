# ADR-0295: a `let` body is an implicit `do`, and truncating a core form is never an answer to an unexpected shape

- Status: accepted
- Date: 2026-09-02
- Consumes: kotoba-sema `c14ca39e` (the frontend collapses a multi-form `let`
  body into a `do`; six `let` consumers and three `if` consumers routed
  through one refusing contract), kotoba-kir `0fd7e259` (`lower` and `execute`
  refuse a core form whose shape they would otherwise have truncated),
  kotoba-lang `4adda169` (`:core-form-shapes` / `:implicit-body-forms` in
  `lang/guest-grammar.edn`, `docs/lang/semantics-ssot.md` §4).

## Context

A `let` whose body had more than one form compiled with `:ok true` and kept
only the **first**. Measured against this repository at `b1fdaad2` with
kotoba-sema `8b2cb10`, `--jvm-free`, wasm32 artifact executed under Node's
`WebAssembly`:

```
(ns letbody (:export [run]))
(defn run [n :i64] :i64
  (let [x (+ n 1)]
    (+ x 10)
    (+ x 100)))
```

`amu check --jvm-free` → `{:ok true …}`. `run(5)` → **16**, which is
`(+ x 10)` with `x = 6`. The correct answer is 106. The analysed HIR body was
`(let [x (+ n 1)] (+ x 10))`: the second form was not mis-ordered or
mis-typed, it was **not in the program**.

Effects went the same way. A `let` body of four `kernel-store-u8` calls
emitted **one** store. On both kernel targets the object for one, two, three
and four stores was byte-identical — 72 bytes on `x86_64-aiueos-kernel-v1`,
64 on `aarch64-aiueos-kernel-v1` — and the immediates 66, 67 and 68 appeared
nowhere in it.

Found by the QWEN-RUNTIME stream of the K16 pure-Kotoba programme, where the
dropped form carried the high word of a 64-bit offset cursor.

### Why nothing caught it

Three facts, each individually defensible:

1. `desugar-expr` emitted **every** body form onto `let` —
   `(list* 'let bindings body…)` — a head that takes one.
2. `rewrite-record-projection` and `elaborate-named-ability` destructured
   `(let [[bindings body] args] …)` and **rebuilt the form from `body`
   alone**; four further passes read it the same way.
3. `validate-expr` carried the rule — *"let requires one result expression"* —
   and ran **last**, so it measured the already-shortened form and admitted
   it.

The rule existed and could not fire. That is superproject `adr-2608136000`'s
shape: a check that could not measure returned the value of a check that
measured and found nothing.

### The same shape, next door

```
(defn run [n :i64] :i64 (if (> n 0) (+ n 10) (+ n 100) (+ n 1000)))
```

`:ok true`; wasm32 answered **15**. `if` survived desugaring with whatever
arity the source wrote, `elaborate-named-ability` rebuilt it from
`[test then else]`, and `validate-expr`'s `if requires test, then, else` then
measured the rebuilt three. In Clojure that source is an arity error.

### What was not affected

Measured, not assumed. `when`, `when-not`, `when-let`, `when-some`, `doseq`
and `dotimes` all answered correctly with several body forms — they desugar
through `do`, which no pass rebuilds from a prefix. `defn`, `fn` and `loop`
**refuse** several body forms with pinned messages. `let` was in neither set.

## Decision

Adopt the upstream fix and pin the compiled evidence here.

- A `let` body is an implicit `do`; the collapse is `do` and never nested
  `let`s, because a non-final form encoded as a binding is an *unused*
  binding and dropping those is legal — the forms that must survive are
  exactly the effectful ones.
- Core `if` is exactly ternary.
- A consumer meeting an unexpected core-form shape **refuses**. Emitting a
  shorter program that compiles clean is not an admitted response.

`test/kotoba/compiler/let_body_sequencing_test.clj` measures this at the
object, not at the HIR: for one through four kernel stores on both kernel
targets, the `let` body emits byte-for-byte what the explicit `(do …)` emits,
the object grows by a constant amount per store, and every store's immediate
is present. A one-form body is byte-for-byte what it was before the change,
so no existing program's emitted bytes move.

## Consequences

- Source that relied on the truncation changes meaning. That source was
  already wrong — it contained forms that never ran. The workaround the
  defect taught authors is in the tree: `aiueos/os/aiueos/kotoba/sha256.kotoba`
  binds each store to a `let` name and adds `(* 0 (+ s0 (+ s1 s2)))` to the
  result to keep them alive. That idiom is now redundant rather than
  load-bearing.
- A four-argument `if` that compiled before now refuses with
  `:kotoba.error/if-arity`. This widens refusal, not admission.
- `test/kotoba/compiler/aggregate_abi_test.clj`'s kotoba-kir pin assertion
  moves with the pin.

## Evidence

Both suites run with only `kotoba-sema/src/kotoba/compiler/frontend.cljc`
reverted to `1acb9f83` — every other dependency at the merged pin — so the
red is attributable to one file:

| assertion | reverted frontend | merged frontend |
|---|---|---|
| object sizes, 1..4 stores, x86_64 | `[72 72 72 72]` | `[72 135 198 261]` |
| object sizes, 1..4 stores, aarch64 | `[64 64 64 64]` | `[64 116 168 220]` |
| immediates 66 / 67 / 68 present | absent on both targets | present on both |
| `(let [x 6] (+ x 10) (+ x 100))` | 16 | 106 |
| `(let [x 6] (+ x 10) (+ x 100) (+ x 1000))` | 16 | 1006 |
| `(let [x 6] (let [y (+ x 1)] y) (+ x 100))` | 7 | 106 |
| `(if (< 0 1) 10 100 1000)` | compiles | refused, `:kotoba.error/if-arity` |
| `(let [x 1])` | `value type is outside the safe profile` | `let requires at least one body expression` |

7 tests / 28 assertions: 20 failures with the reverted frontend, 0 with the
merged one.
