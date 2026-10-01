# selfhost-codemod

Form-rewriting codemods for the selfhost frontend port (`kotoba-sema/src/kotoba/compiler/frontend.cljk`, 22k lines).
The port is hundreds of mechanical edits of five shapes; this library does them from a syntax tree, not by hand and
not by regex, and proves on the host route that it changed nothing there.

    scripts/selfhost-codemod/codemod.sh <file.cljk> --rules a,b,d,e,f [--out f] [--report f] [--dry-run]
    scripts/selfhost-codemod/codemod.sh <file.cljk> --rules c --target dual|host-env [--observable-from <test-dir>] ...
    scripts/selfhost-codemod/test.sh                     # 17 tests / 132 assertions, incl. host equivalence by evaluation
    scripts/selfhost-codemod/pipeline.sh <frontend.cljk> <workdir>      # rewrite a scratch copy + kotoba-sema suite diff
    scripts/selfhost-codemod/diff-suite.sh <src-root> <workdir>         # the differential alone
    scripts/selfhost-codemod/kotoba-route-check.sh                      # amu check of fixtures/forms.cljk, 3 stages

Needs nbb (default `NBB_DIR=/Users/junkawasaki/github/kotoba-lang/amu-measure`). The tool never writes the file it reads
(`--out` names a copy). Comments, whitespace and every untouched byte are preserved.

## Design

* **`codemod.cst`** is a lossless concrete syntax tree (about 150 lines): every node has absolute offsets `[:s :e)` into the
  source; comments and whitespace are not nodes, so a rewrite is a list of text edits and the rest of the file is
  byte-identical. It understands what `kotoba.compiler.kotoba-reader` does not (regex, `^:dynamic`, `'x`, `@x`, `#()`,
  chars, `#_`) plus reader conditionals as structure (`#?(:kotoba X :default Y)`, kids alternate key and form). The repo
  reader reads the `.kotoba` grammar only, cannot read frontend.cljk, and drops comments; the CST mirrors its
  `:end-offset` contract. It parses frontend.cljk in 0.2 s into 912 top-level forms (same count as edamame).
* **`codemod.edit`**: edits are `{:s :e :text}`; a zero-width edit is an insertion. Conflicting (nested) edits keep the
  innermost, the outer one is re-found on the next pass (fixpoint, at most 8 passes). A finding is atomic: all of its
  edits or none.
* **Regions.** Every node is `:shared` (outside any `#?`), `:default` (host arm) or `:kotoba` (hand-written Kotoba arm,
  never touched). A finding inside the `:default` arm of a definition that already has a hand-written `:kotoba` port is
  counted as `ported` and not rewritten (`--include-ported` overrides). Exception: rule `c` with `--target host-env` applies
  there too (`:force-apply`): the host arms are part of the host call graph and a partial rewrite would be unsound.
* **Dual-runtime output.** A rewrite never replaces host text with Kotoba text. Either it is host-equivalent code
  (helpers `fe-nth`/`fe-get`... with a host and a Kotoba reading, inserted once after `ns`), or the host text stays
  byte-for-byte as the `:default` arm of a one-form-per-branch `#?(:kotoba NEW :default OLD)`.
* Rules are maps `{:id :find (fn [{:src :nodes :opts}] findings)}`; a finding is `{:status :auto|:human :reason :edits ...}`.

## Rules

| id | what | host effect |
|---|---|---|
| `a` | destructuring lambda parameters `(fn [[k v]] ..)`, `{:keys ..}`, nested, `& rest`, `:as`, `:or`, multi-arity -> plain param + `(let [k (fe-nth p 0) ..] ..)` | none: `fe-nth` is `(nth c i nil)`, `fe-get` is `get`, `fe-nthnext` is `nthnext`, exactly what Clojure's destructuring expands to |
| `b` | `reject!` -> the `:fe/err` typed abort (statement -> `(let [_ #?(:kotoba (require-k ok msg "code" form) :default (when-not ok (reject! ..)))] rest)`; tail / let value -> `#?(:kotoba (throw (fe-error ..)) :default (reject! ..))`) | none: the original is the `:default` arm |
| `c` | dynamic vars -> explicit env threading (target `dual`: `#?(:kotoba <fenv-threaded defn> :default <original defn>)` with the landed `env-X`/`with-X` accessors; target `host-env`: in-place, host-valid, `fenv` is a map built by `(fe-current-env)`) | none for `dual`; `host-env` is the differential experiment |
| `d` | keyword callbacks `(map :k xs)` -> `(map (fn [e] (:k e)) xs)` (`--lower-accessor`: `(fe-get e :k)`), `(juxt :a :b)` | none |
| `e` | (extension of a) destructuring in `let` binding vectors, flattened in place | none |
| `f` | (extension of a) `mapv`/`map`/`filter`/`filterv`/`reduce` with a one-lambda callback -> a loop over `kotoba.form` as the `:kotoba` arm | none: `:default` arm is the original call |

Order for a full run: `a,b,d,e,f` on the source, then `c` on that output (`c` replaces whole `defn`s and runs once).

### Automatic vs human, per rule (frontend.cljk at kotoba-sema 53888c7, 22484 lines, md5 be8c2abb)

Counts are on the ORIGINAL source (pass 1). "ported" = inside the host arm of a definition that already has a hand
port: nothing to do on the Kotoba route. "actionable" = the rest.

**(a) destructuring lambdas: 238 patterns** (216 shared, 22 host arm; 19 ported -> 219 actionable). 219 auto, 0 human.
By callback: map 61, mapv 38, reduce 37, keep 26, mapcat 23, first-truthy 13, every? 7, remove 4, filter 4, some 3,
keep-indexed 1, other 2. By pattern: `[k v]` pairs 130, `{:keys ..}` 62, nested 14, plain vectors 11, other 2. The refusal the doc names (`map fn parameter destructures ([k v])`) is removed everywhere.
Human attention is therefore not about the rewrite but about what comes next, measured with
`kotoba-route-check.sh` on `fixtures/forms.cljk`: as written the module is refused at the destructuring; after (a) alone it is
refused one layer down (`map` on this route takes a `vector-i64` source, items are `i64`, so `(map f (form/kids-of x))`
is "expected vector-i64, got [:list [:ref :form/r]]"); after (a)+(f) `amu check` says `OK`. Not rewritten, counted as out
of scope: other destructuring sites, `let` 361 (rule e covers 314 + 47 ported), `doseq` 69, `if-let` 26, `when-let` 1,
`for` 3, `defn` params 6.

**(e) let destructuring: 361 patterns**, 314 actionable, 314 auto, 0 human.

**(f) combinators as loops: 149 patterns on the original** (callbacks that are `(fn [p] ..)` over exactly one collection;
15 ported). 45 are plain-symbol lambdas and go straight through; 89 are destructuring lambdas that (f) reports as
human until (a) has run ("run rule a first") and that the combined run then converts, 161 applications over the passes.
Assumptions the tool cannot check (written in the rule header): the collection is a Form list/vector (a Form MAP is stride 2),
element results are Forms, a filter body is a bool.

**(b) `reject!`: 757 call sites** (559 shared, 198 host arm; 196 ported -> 561 actionable).

| | n | |
|---|---|---|
| auto: conditional statement in a body sequence | 286 | `(let [_ <require-k> ] rest)` |
| auto: tail position | 42 | `(throw (fe-error ..))` |
| auto: `let` binding value | 23 | |
| human: inside `loop`/`doseq`/`for`/`dotimes` | 70 | the design says split into "answer" + "caller throws" |
| human: inside a lambda | 51 | an aborting lambda needs its own result type |
| human: 4-arity `(reject! m f code data-map)` | 39 | `:fe/err` carries no data map |
| human: value position (argument of a call) | 25 | |
| human: unconditional `reject!` mid-body | 17 | dead code after it, or a missing branch |
| human: non-literal code argument | 6 | |
| human: inside `try`/`catch` | 2 | |

Note: `require-k` evaluates its message and form eagerly, the host `when-not` does not; the host arm is untouched, so this
only matters on the Kotoba route (where `reject!` args are pure).

**(d) keyword callbacks: 51 patterns**: 47 auto (map 20, mapv 10, filter 5, juxt 5, mapcat 3, remove 2, not-any? 1,
group-by 1), 4 human (`(comp :a :b)`-style composed callbacks). Multi-collection `(map :k a b)` (which is `get` with a
default) and `juxt` as a threading step are reported, never rewritten.

**(c) dynamic vars.** Inventory: 38 `^:dynamic` vars; symbol reads 171 shared / 142 host arm / 18 kotoba arm; `binding`
forms 28 / 30 / 5; 13 vars map to an existing `:fe/env` field, 25 need a new field (the report lists them), 4 of the 13 have
a different representation on the Kotoba route (`*synthetic-counter*`, `*loop-counter*` host volatile vs `:i64`;
`*absence-mode*` keyword vs bool; `*abort-lexical-context*` keyword vs string) and block the automatic rewrite.
Of the 392 shared-region `defn`s, 96 reach dynamic state (C). Target `dual`: 28 rewritten automatically; 68 blocked: 51 because they call a blocked function in C (the closure
property below) and 17 directly (10 mutate a counter/registry through a ref, which on the Kotoba route is a value returned
with the result, a hand port; 6 are used as values; 1 var with a different representation; 1 bare function as a `->>` step;
1 shadowed function name; reasons overlap).
Target `host-env` (host-valid, the differential): 47 functions rewritten in place, 22 entry-site functions touched
(`(f (fe-current-env) ..)`), the rest blocked (96 by callee closure, 3 public, 3 named by a test through `#'`).
Soundness: a rewritten function may only call rewritten functions of C, else a callee would read a var the caller no
longer binds; the rewritable set is the greatest subset of unblocked members of C closed under "callees in C".

## Differential check: the host route result is unchanged

`diff-suite.sh` runs kotoba-sema's `run-tests.cljk` on nbb twice, original `frontend.cljk` first on the classpath and then the
rewritten copy first, and compares per-test outcomes (FAIL/ERROR names, expected, the `:message` of actual; line numbers and
stack frames removed). Baseline is 620 tests, 2147 passed, 77 failed, 25 errors; the failing set is pre-existing and must be
identical, not merely equal in count.

| applied to a copy | result |
|---|---|
| a | identical |
| b | identical |
| d | identical |
| e | identical |
| f | identical |
| c (host-env, on the original) | identical |
| a,b,d,e,f then c (host-env) | identical (pipeline.sh, 3a and 3b) |

Negative control: breaking the `fe-nth` helper (`(nth c i :oops)`) in the rewritten copy turns the same check red
(`:oops is not ISeqable`, 100+ differing lines). The unit tests also evaluate `fixtures/equiv.cljk` before and after
(`load-string`, 12 functions, 21 inputs) and compare results and thrown `ex-data`. A second run over a rewritten file
applies nothing (idempotent).

Found while building (all fixed, kept as tests or comments): a keyword-headed vector in a parameter list is a Kotoba type,
not a pattern; `#(f % x)` is a call to `f`; a bare function in `->>` is a call; a body vector `[(f x)]` is not a param
vector; value references to a rewritten function must be `(partial f env)`; a private function reached by `#'ns/f` in a test
is public for the purpose of the signature (`--observable-from <test-dir>`).

## Limits

* Syntactic. No types: whether a collection is a Form map or a Form list, whether an element result is a Form, whether a
  var holds a ref, is decided by shape or reported.
* `c` resolves function names by symbol; local shadowing is tracked per `defn` (any local with the same name blocks).
  Macros, `resolve`, and vars captured in closures that run outside the `binding` extent are not modelled; the host-env
  differential is what covers them, for the tested paths.
* Output is correct, not pretty: the generated Kotoba arms are long single lines and the inserted `let` wrappers are not
  re-indented.
* The Kotoba arms are not type-checked as a whole (frontend.cljk does not pass `amu check` yet); only the shapes in
  `fixtures/forms.cljk` and the helper prelude were checked on the route (`OK`).
