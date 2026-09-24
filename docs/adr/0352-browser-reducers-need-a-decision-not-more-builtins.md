# ADR 0352 — kotoba-lang/browser's reducers need a language decision, not more builtins

- Date: 2026-09-25
- Status: Proposed (needs an owner decision; nothing below is decided)
- Related: aiueos ADR-0226 and its desktop maturity floor `:browser-component`
  (`os/aiueos/contracts/desktop-maturity-floors.edn`), ADR 0005 (closed module
  linking, explicit `:export`), ADR 0028 (document values: no coercion, no
  truthiness), ADR 0201 (inferred `option-or`), ADR 0214 ("Kotoba does not have
  a dynamically shaped record boundary"), superproject ADR-2608650000 (what
  "cannot write" means: permanent vs temporary).

## Context

The aiueos desktop floor `:browser-component` asks for kotoba-lang/browser's
`browser.surface`, `browser.input` and `browser.text-edit` to compile
**unchanged** for `x86_64-aiueos-kernel-v1` and `aarch64-macos`, so the
kernel runs the same reducers the hosted engine runs instead of mirrored
objects. The floor recorded eight walls on 2026-09-25 (amu `2dcaac74`,
browser `6cbc1ee`). This ADR records what happened when they were worked one
at a time.

`amu check` is target-independent (`bin/amu`: `targetIndependentCommands`
holds `check`), so "on both targets" is one measurement: the refusals below
are the frontend's, identical for every target.

### Walls that were builtins and are now landed

Three walls were ordinary Clojure forms the frontend had not lowered. Each
has a sound meaning in the typed profile and needed no new KIR head:

| wall | form | now | kotoba-sema | amu |
|---|---|---|---|---|
| 3 | `(:k m)` / `(:k m d)` on the bounded map or a typed map | means `get` | `110cb48e` | #1088 |
| 4 | `(conj v x ...)` on a `:vector-i64` / `:vector-f64` | `vector-conj`, folded left | `45913acc` | #1089 |
| 7 | `(remove pred v)` | filter's loop, predicate negated | `05d8bd8a` | #1092 |

Each has a sema test (`keyword-lookup-on-maps-test`, `conj-on-a-vector-test`,
`remove-test`) and an amu project test in `test/nbb/project.cljk`, red at the
previous pin with the named reason and green at the new one.

### The walls that are one decision

Everything else is the same wall seen from different forms. Measured with
single-form probes (`amu check`, amu `2dcaac74` + the three changes above,
2026-09-25), and by checking a scratch copy of the three modules with an
export attr-map added so the checker reaches their bodies:

1. **Unannotated parameters are `:i64`.** A parameter's type comes from its
   annotation or from its use inside the body (`(string-length s)` makes `s`
   a string). Callers do not inform it. `(defn f [m] (:a m))` is refused
   (`record-get ... requires a record value; got :i64`), and so is
   `(defn f [k] (case k :a 1 0))` (`equality operands must have the same
   value type`). Every function in the three modules takes an unannotated map.
   Wall 3 as recorded (a literal all-i64 map) was the narrow case of this.
2. **A keyword map is a closed record or the bounded keyword->i64 map.** There
   is no open map. So: a `nil` value has no type (wall 2,
   `text_edit.cljk:6 :text/composition nil`); `assoc` of a new key, `dissoc`,
   `merge` and `select-keys` on a record are refused or unknown; a vector of
   records is refused (wall 5, `expected i64, got [:record ...]`). ADR 0214
   states the reason as a property: no dynamically shaped record boundary.
3. **No dynamic value, so no runtime type test.** `browser.surface`'s
   `render-content!` dispatches on `nil?` / `string?` / `vector?` /
   `sequential?` / `map?` over hiccup whose items are keywords, maps, strings,
   nested vectors and seqs. `string?` is `unknown operation`. The only
   dynamically shaped value amu has is `:document` (ADR 0028), which is
   bounded (depth 8, 256 nodes), has no functions, and forbids coercion and
   truthiness by decision.
4. **Truthiness on non-bool values.** `(or n lo)` on an i64 compiles; the
   reducers also write `(when (:shift? event) ...)`, `(if-let [f (:app/document-fn app)] ...)`
   and `cond->` over optional keys, i.e. nil-punning over open maps.
5. **Functions stored in data.** `:app/document-fn` is called out of a map.
   `(let [m {:f (fn [x] (+ x 1)) :n "a"}] ((:f m) 1))` exits 70 with
   `internal compiler error` (`:kotoba.error/internal-operation-failure`) --
   that one is a defect regardless of this decision: it must refuse, not
   crash.
6. **Strings.** `count` of a string is refused **by decision**, with the
   reason in its message: UTF-8 bytes vs characters would give two answers the
   same spelling. `browser.text-edit` counts UTF-16 code units (its surrogate
   pair logic depends on it) and reads them with host interop under
   `#?(:clj (.charAt ...) :cljs (.charCodeAt ...))`, with no `:kotoba` or
   `:default` branch -- interop is a permanent refusal, so that function reads
   as empty. `subs` is unknown.
7. **Vocabulary clashes decided elsewhere.** Two-argument `some` is refused
   because `some` is the option constructor here (the refusal says so).
8. **Missing sequence heads.** Measured unknown or refused: `for`, `concat`,
   `reverse`, `nth` (vector destructuring of a parameter), `vec`, `merge`,
   `select-keys`, `string?`. Not probed: `reduce-kv`, `comp`, `val`,
   `some` as a predicate over windows. Each is a builtin in isolation,
   but each of them is used here over open maps or record vectors, so
   lowering them does not move the reducers without (1)-(3).
9. **Wall 8, the dependencies.** `browser.surface` (and through it
   `browser.input`) requires `cssom.layout` and `kotoba.wasm.dom`
   (kotoba-lang/dom-gpu). Supplied on the source path (cssom `9224d359`,
   dom-gpu `f2d0eba9`), the link stops before any semantics: `source exceeds
   1 MiB admission limit` -- `cssom/layout.cljk` alone is 1,083,132 bytes and
   `cssom/core.cljk`, which it requires, 546,205. That cap is ADR 0005's
   linked-source bound, a decision, not a missing lowering. Past it, both are
   written in the same open-map style (DOM data with string colours), so their
   admission is the same question as (1)-(4).
10. **Wall 1, exports.** ADR 0005 requires an explicit export vector on every
    project module. The ns attr-map spelling `{:kotoba/export [...]}` exists so
    dual-runtime source can declare it (SCI refuses an `(:export ...)` clause).
    Declaring it is a browser change -- not a bug fix, so it was not made
    here. Deriving exports from public `defn`s would change ADR 0005.

So "admit browser unchanged" is not a list of missing builtins. The reducers
are dynamically typed Clojure over open maps and hiccup; amu's application
profile is closed and static on purpose. One of them has to move.

## Options

**A. A dynamic Clojure-data value in the application profile.** A tagged
universe with nil, open maps, truthiness, runtime type predicates and
function values, lowered on every native target. Admits browser unchanged.
Contradicts ADR 0028 (no truthiness, no coercion) and ADR 0214 as written,
needs a native runtime representation and GC-free allocation story for
unbounded persistent maps, and weakens the closed-KIR property the typed
profile exists for.

**B. Caller-driven, monomorphizing inference.** Infer a parameter's type from
its call sites and specialize per call-site type; infer `[:option T]` for a
record field that is `nil` in one construction and `T` in another (ADR 0201
is the local version of this); treat a keyword map literal whose keys vary
by construction as a row-polymorphic record specialized per shape. Stays
static and closed. Plausibly admits `browser.text-edit` (after its
interop branch gets a `:default`) and most of `browser.input`. Does **not**
admit `browser.surface`'s hiccup rendering, which is a sum over runtime
shapes -- that needs `:document` (with its bounds) or option A.

**C. One typed source for both engines.** Write the reducers once in the typed
profile (declared `:schemas`, annotated signatures, option fields, a
document-typed hiccup) and have the hosted engine run *that* source through
amu's JS / wasm32 targets. The floor's objection -- "a second copy of the
reducers" -- is about two copies; this is one copy, moved. It is a
whole-component migration of kotoba-lang/browser (superproject rule: the
unit of migration is the component), and it moves the hosted engine off
the Clojure source it runs today.

## Proposal

Owner decides between A, B and C (or B for text-edit/input plus C for the
surface's rendering half). Until then the floor stays blocked with the walls
above, and the three landed changes stand on their own as ordinary Clojure
surface the typed profile already had a meaning for.

Independently of the decision: the `internal compiler error` in (5) should
become a named refusal, and calling a stored closure from inside an inline
`filter` predicate -- `(let [p (fn [x] (< x 3))] (filter (fn [y] (not (p y))) v))`
-- traps `:division-by-zero` at run time on the KIR interpreter (kotoba-sema
`05d8bd8a`), which is a miscompile, not a refusal.

## Reproduce

In an amu checkout after `npm ci`, with a kotoba-lang/browser checkout at `B`:

```
bin/amu check $B/src/browser/text_edit.cljk --source-path $B/src
bin/amu check $B/src/browser/input.cljk     --source-path $B/src
bin/amu check $B/src/browser/surface.cljk   --source-path $B/src
```

All three exit 65 with `project module ... requires an explicit :export
vector`. With `{:kotoba/export [...]}` added after each ns docstring in a
scratch copy: text-edit stops at the `nil` field (line 5 of the copy), and
with that key left out, at the `#?(:clj ...)` interop body of
`code-unit-at` (`function body is empty ... no :kotoba or :default
clause`); input and surface stop at `required module cssom.layout is
missing from the explicit source paths`, and with cssom and dom-gpu on the
path at `source exceeds 1 MiB admission limit`. The single-form probes above are one `(ns p.x)` plus
one `defn main` each.
