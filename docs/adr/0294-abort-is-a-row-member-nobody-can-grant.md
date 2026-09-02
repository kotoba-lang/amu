# ADR-0294: `:abort` is a row member nobody can grant, so admission must not ask

- Status: accepted
- Date: 2026-09-02
- Consumes: kotoba-sema `e42b74ef` (typed abort ability slice 1 + type-directed
  arithmetic), kotoba-hir `ac8e7051` (`valid-effect?` admits `:abort`),
  kotoba-kir `1e00f830` (`effect-row-from-hir` adapter), kotoba-lang `9336e582`
  (`lang/guest-grammar.edn` with `:throw` / `:try` /
  `:type-directed-arithmetic` sugar, vendored here byte-for-byte).

## Context

Until today an inferred effect row had one kind of member, `[:cap/call <id>]`:
an authority the function exercises, which a `--policy` must grant. The typed
abort ability (kotoba-lang `lang/abort-ability.edn`, slice 1) adds a second
kind, the bare keyword `:abort`. It marks a function that may leave its
caller's scope through a typed abort. The frontend has already lowered that
function to return `[:result T E]` and rewritten every `throw` / `try` into
`result-err-of` / `result-match-of` before any consumer in this repository
sees the body; the keyword carries no error type and names no authority.

Measured 2026-09-02 at the pin bump, on this CLI's JDK-free route, before any
change to `src/`:

```
$ bin/amu compile abort-callee.kotoba --target wasm32 --jvm-free --output x.wasm
{:format :kotoba.cli-error/v1, :ok false, :error :admission,
 :diagnostic {:code :kotoba/admission-denied, ...},
 :message "capability policy denies required effects"}                 exit 65
```

for

```clojure
(ns abort.callee (:export [main]))
(defn- safe-div [a :i64 b :i64] :i64
  (if (= b 0) (throw "division by zero") (quot a b)))
(defn main [] :i64 (try (safe-div 10 0) (catch e (string-length e))))
```

a program that exercises no capability. Its module row is `#{:abort}` -- the
union of function rows, and `safe-div` aborts -- and every one of the seven
`kotoba.kir.admission/check` call sites here handed that raw row to admission.
`check` decides by `(set/difference required allowed)`, and its `:allow` only
admits `[:cap/call <int>]`, so the keyword can neither be granted nor be asked
for. The refusal read as "write a policy", and no policy could be written.

Two more sites did not throw only because no aborting program had reached
them: `kotoba.compiler.test-profile`'s `test-policy` called `(first %)` on
every row member and `capability-ids` destructured each as `[effect id]`.
Under a row holding `:abort` both throw before the first test runs.

The program whose `main` itself both throws and catches (`abort.one`) compiled
and ran unchanged, because `try` removes `:abort` from the row it contributed
and the module row was empty. That is why the gap is only visible across a
callee.

## Decision

`kotoba.compiler.effect-row` (`.cljc`, one namespace, both routes) is the one
place that knows a row has two kinds of member:

- `control-effects` is the closed set `#{:abort}`. It moves with kotoba-hir's
  `valid-effect?`, which admits exactly those keywords into a row.
- `grants` removes control effects and keeps EVERYTHING else -- including a
  member it does not recognise, which then reaches admission and is refused
  there. Narrowing by shape (dropping every non-vector) would turn a misspelt
  or newly invented member into a silent pass.
- `check` is `kotoba.kir.admission/check` over `(update hir :effects grants)`.

Every admission site routes through it: `core/admit!` (JVM `check` /
`compile`), `nbb/cli.cljs` (native), `nbb/wasm_cli.cljs` (three sites:
`check`, uncached and cached `compile`), and `receipt/create` / `verify`.
`test-profile`'s two destructuring sites use `effect-row/grants` and
`effect-row/grant?`.

Only the admission DECISION is narrowed. `check`'s printed `:effects`, the
HIR handed to provenance, `:kotoba.artifact/effects`, the interface report and
the logic manifest keep the row as inferred, `:abort` included; a reader of
those is entitled to know the function aborts. `capability-names/name-grants`
already passes a keyword through unchanged.

Not changed, on purpose: `kotoba.compiler.backend.evm` refuses any module
with a non-empty row, and so now refuses one that aborts. Its interface is
`[:result T E]`, which that backend cannot lower either way; a narrower
refusal would be a second decision with no program to justify it.

## Consequences

Measured after the change, JDK-free route unless noted:

| claim | measured |
|---|---|
| (a) `throw` / `try` across a callee compiles and runs | `abort-callee` → wasm32 2049 bytes, sha256 `d109dab3…`; `instantiateKotoba` `main()` = `16n`. `abort.one` = `7n`. `amu check` reports `:effects #{:abort}`, `:admission {:required #{} :minimal-policy {:allow #{}}}` |
| (b) unhandled abort at `main` | refused by the frontend, exit 65, `:code :kotoba.error/abort-unhandled-export`, message verbatim `unhandled abort at export boundary; catch it with try: main` |
| (c) type-directed `(+ a b)` on two f64 | compiles (was `expression type mismatch: expected i64, got f64` before the bump); emitted `.wasm` byte-identical to the `f64-add` spelling (sha256 `3ede03b8…`), both answer `1n` |
| (d) integer-only programs before/after the bump | `examples/todo-app.kotoba` (7144 bytes, `5cd9d995…`) and `examples/evm-answer.kotoba` (`17029431…`): `.wasm` AND `.provenance.edn` byte-identical |

The nbb corpus (`npm run test-nbb-wasm32`) gains the fixture on both wasm32
targets plus three hand-rolled claims, one of which pins that raw
`kotoba.kir.admission/check` STILL refuses the row with `:missing #{:abort}`.
That pin is what makes the seam necessary; the day it goes red is the day
the seam can go. `kotoba.compiler.effect-row-test` asserts the same on the
JVM, plus the two `test-profile` sites fed a row that holds the keyword.

Left as gaps, not papered over:

- kotoba-kir's `definition-identity/effect-row-from-hir` refuses a row
  holding `:abort` (`effect row member is not a wire capability call`). This
  repository does not call it yet; when it does, the bridge -- not this seam
  -- has to learn the keyword.
- Native targets: `nbb/cli.cljs` seals `(:effects hir)` into the kexe, so an
  aborting module's kexe would carry `:abort`. No such module reaches sealing
  today: `[:result T E]` is not a word-typed interface, and the native
  admission gate refuses it first. Not measured past that gate.
- `:abort` in `plan/inferred-effects` reaches `:requested-effects` as-is;
  `kotoba.abi.contract/valid-plan?` only asks for a set. Carried, not
  interpreted.
