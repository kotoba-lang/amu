# Selfhost frontend decomposition (2026-09-30)

Design only. No source is changed by this document. It refines stage S3 of
`docs/selfhost-core-rewrite-plan-20260930.md` (sema passes, one `(env, Form) -> Form` pass at a time)
for the one module that plan calls the wall: `kotoba-sema/src/kotoba/compiler/frontend.cljk`.

Subject, as measured on branch `agent/fs-app-data-bytes`: **20704 lines, 1,135,380 bytes, 711 top-level
forms** (`grep -c '^(def\|^(declare\|^(ns'`). Every number below was taken with `grep`/`awk` on that file;
the commands are in the appendix. Line ranges are approximate at the pass seams (a seam is the nearest
top-level form boundary), exact inside a pass.

## (a) Inventory by pass

Sizes are lines / comment-only lines / KiB. Comment-only lines matter: 3,520 of the 20,704 lines (17%) are
`;;` comments, and the docstrings are extra, so the code to port is roughly 14k lines.

| # | pass | lines | size | notes |
|---|---|---|---|---|
| 0 | head, operation and limit tables, capability catalog, registries | 1-1399 | 1399 / 754 / 78 | ~130 `def`s of symbol sets and maps (`arithmetic`, `string-operations`, `kernel-privileged-operations`, `max-*`). Loaded from EDN at load time (`load-capability-catalog`, `load-grammar-declared-heads`) with a cljs fallback. Consumed by other modules (`capability-registry`, `forbidden-heads`, `max-*` are re-exported by `kotoba.sema`). |
| 1 | type-descriptor validation | 1400-1699 | 300 / 53 / 15 | `validate-value-type!` (1488-1657) plus ~25 descriptor predicates (`record-type?`, `variant-type?`, ...). Descriptors are vectors, so this is a Form walk already. |
| 2 | reader glue | 1700-1821 | 122 / 63 / 6 | `check-reader-depth!`, `read-forms` (delegates to `kotoba-reader`, which now has a Kotoba twin), `form-span` (reads host `meta`). |
| 3 | pure-head rewrite | 1822-2049 | 228 / 76 / 11 | `rewrite-pure-application-forms` (`lam app ref perform`). Reads `*pure-definition-names*`, `*state-handlers*`. |
| 4 | diagnostics and ns header | 2050-2679 | 630 / 97 / 34 | `reject!` (2052; 757 call sites in the file), `internal-failure!`, `unbound-symbol!` + `edit-distance`/`nearest-names`, arity rejections, `namespace-*` attr-map parsing. |
| 5 | desugar: closure and lambda lifting | 2680-3659 | 980 / 172 / 48 | Declares 25 of the 38 dynamic vars. `lift-lambda`, `lambda-dispatchers`, `closure-apply-helper`, lazy take/drop helpers. |
| 6 | desugar: capability and synthetic names | 3660-3849 | 190 / 55 / 9 | `resolve-capability-keyword!`, `synthetic` (3825), `chain-temp`. |
| 7 | desugar: intrinsic helper injection | 3850-4134 | 285 / 57 / 15 | `reject-reserved-source-symbols!`, helper source **text** (3903), `expand-intrinsic-helper-forms`, `expand-app-data-bytes-writes`. |
| 8 | desugar: sugar, map literals, documents, match | 4135-6479 | 2345 / 187 / 113 | `and or cond condp dotimes doseq case some-> match`, map-literal typing (4856-5260), document literals and `document-hof->reduce` (5260-5800), `map-get`/`map-without` helpers, `desugar-match`, `destructure-binding`, lazy `map`/`filter`. |
| 9 | `desugar-expr*` | 6477-8412 (+ `desugar-ordinary-call`, `desugar-expr` to 8500) | 2020 / 451 / 118 | One 1,936-line `cond` over heads. Reads 12 dynamic vars, writes 5. The single largest function. |
| 10 | local-state elaboration | 8500-9048 | 549 / 56 / 24 | Source-level, before desugar. Rewrites `(atom ..)`/`swap!`/`reset!`/`deref` into rebinding chains (`__kotoba_cell_*`). |
| 11 | `validate-expr` | 9049-9759 | 711 / 48 / 38 | `validate-expr-impl` is 617 lines, 96 `reject!` sites, 37 `doseq`, **zero dynamic vars, zero calls into desugar or inference** (measured: only `value/*` limits, tables, `unbound-symbol!`, `reject-*-arity!`, `if-parts`, `let-body`). |
| 12 | type inference | 9760-11730 | 1971 / 231 / 97 | `infer-call-type-impl` 10293-10992 (700 lines), `infer-expression-type-impl` 11029-11731 (700 lines), numeric resolution, row operations (9978-10145). Reads `*absence-tail*`, `*schemas*`, `*state-handlers*`, `*row-op-schemas*`, `*numeric-resolution-final*`, `*abort-throw-types*`, `*loop-helper-*`. |
| 13 | elaborate-named-abilities | 11731-11959 | 229 / 20 / 10 | Capability calls to wire ids; interrupt entries. |
| 14 | loop-helper inference | 11960-12299 | 340 / 30 / 18 | `infer-loop-helper-results`, `check-loop-recur-argument-types!`. |
| 15 | absence resolution | 12300-12539 | 240 / 4 / 10 | `resolve-absences`, `resolve-function-absences`, `retire-absence-markers`. |
| 16 | `rewrite-record-projection` | 12539-13576 | 1037 / 296 / 58 | One function. 28 of the file's 124 `meta` uses; reads `*record-protocol-dispatch*`. Rewrites record access, constructors, options, `option-or`. |
| 17 | ownership and need checks, row-polymorphic parameters | 13577-14273 | 697 / 76 / 37 | `parameter-use-conflict!`, `check-eager-recursive-let-bindings!`, `specialize-row-parameters` (14110). |
| 18 | `type-literals`, absent parameter/result inference | 14274-14527 | 254 / 22 / 13 | |
| 19 | abort passes | 14528-15210 | 683 / 81 / 38 | `a-normalize-aborts`, `infer-abort-error-types` (fixed point), `elaborate-aborts` (14938). |
| 20 | state ability | 15211-15960 | 750 / 18 / 42 | `expand-state-ability-forms`, `specialize-state-abilities`, `thread-state-abilities`. |
| 21 | closure refinements | 15961-16369 | 409 / 35 / 23 | `infer-closure-refinements` (fixed point over facts). |
| 22 | linear, kernel-region, slice erasure | 16370-17380 | 1011 / 248 / 52 | `check-value-types!`, `check-linear-resource-ownership!`, `check-kernel-region-provenance!`, `erase-slice-values`. |
| 23 | effects, budget, affine | 17381-17699 | 319 / 25 / 15 | `infer-effects`, `check-lowering-budget!`, `check-namespace-capabilities!`, `check-affine-writes!` (uses `affine.cljk`). |
| 24 | defn parts, variadic, overloads | 17700-18216 | 517 / 145 / 28 | |
| 25 | constant folding | 18217-18630 | 414 / 110 / 24 | `fold-def-value!` **re-enters the driver** (`analyze-forms*` on a probe module, 18364). |
| 26 | defdesugar, multimethod, protocol and record expansion | 18631-19709 | 1079 / 73 / 55 | `expand-defdesugar-forms`, `expand-closed-multimethod-forms`, `expand-record-protocol-forms` (19555). |
| 27 | analyze driver | 19710-20619 | 910 / 227 / 58 | `analyze` (20587) -> `analyze*` (19710) -> `analyze-forms*` (20580, binds `*state-handlers*`) -> `analyze-forms**` (19744-20579). The 836-line `let` that sequences everything, then `hir/validate!` (20565). |
| 28 | lint | 20620-20703 | 84 / 16 / 3 | `(* 0 <call>)` findings. Independent of the rest. |

Host-isms that the port must answer (counts of lines, whole file): 84 `#?(` reader conditionals, 70 `(try`
(control flow through host exceptions), 22 `ex-info`, 6 regex uses, 124 `meta`/`with-meta` uses, 46
`tree-seq`, 81 `pr-str` (error text embeds printed forms), 48 `sort`/`sorted-map`, 18 `gensym`, 47
`(volatile! ...)` construction sites, 2 `(atom ...)` (lambda-infos, loop-helpers), 61 `vswap!`/`vreset!`,
23 `clojure.set` uses, 33 `str/` uses. The module has **no `defrecord`**: every intermediate is a host map.

## (b) Dynamic vars and mutable cells

### The 38 dynamic vars

38 `^:dynamic` vars (39 declaration lines; `(declare ^:dynamic *local-types* ^:dynamic
*local-option-types*)` is one line, two vars). 31 are also exported through the `ns` `:kotoba/export`
(line 2), but only `*numeric-resolution-final*` is bound from outside (`kotoba-sema/test/kotoba/compiler/
type_directed_arithmetic_test.cljk:184`). No other module reads a frontend var. `*linear-returning*` is
`affine.cljk`'s, not this file's.

Occurrence counts are non-comment lines; W is a `binding`/`vreset!`/`vswap!` writer, R a reader.

**Group M: module-static (bound once per pass or per source, never rebound inside a walk). 10 vars. Replaced by `ModuleEnv`.**

| var | first def | uses | who reads | driver binds at |
|---|---|---|---|---|
| `*schemas*` | 2685 | 13 | desugar (closure result types, `record-field-type`), inference, row-spec | 20106, 20187, 20280 |
| `*function-arities*` | 2761 | 20 | `desugar-expr*` (15 reads: call arity), variadic | 20008 |
| `*document-functions*` | 2762 | 2 | document helpers | 20009 |
| `*function-callable-result-contracts*` | 2876 | 4 | closure contracts | 20010 |
| `*function-callable-param-contracts*` | 2884 | 3 | closure contracts | 20012 |
| `*record-protocol-dispatch*` | 12301 | 4 | rewrite-record-projection, linear | bound at 16407 (per pass) |
| `*numeric-resolution-final*` | 9838 | 3 | inference, `check-value-types!` | 16419; test binds it true |
| `*pure-definition-names*` | 1824 | 3 | pure-head rewrite only | 2049 |
| `*abort-error-types*` | 2792 | 7 | abort passes (5 reads) and desugar; the per-pass fixed-point result, bound at 14829, 14848, 14968 | 14829, 14968 |
| `*row-op-schemas*` | 9996 | 3 | row ops in inference; set once by `(vreset! .. merged-schemas)` at 19830 | 19761 |

`*row-op-schemas*` is a volatile that is written exactly once, from a value the driver already holds; it is
a module-static in disguise.

**Group C: lexical context (rebound with `binding` at a `let`/`fn`/`loop`/`try` boundary, read-only inside
the subtree). 13 vars. Replaced by `Ctx`, passed as an argument and updated with `assoc`.**

| var | uses | passes | rebinding sites |
|---|---|---|---|
| `*lexical-bindings*` | 29 | desugar (`desugar-expr*` 20 reads) | 3473, 6785, 6986, 7016, 7968, 8167, 8311, 8367 |
| `*local-types*` | 20 | desugar | 3481-3485, 6983, 6993, 7089 |
| `*local-option-types*` | 9 | desugar (`resolve-option-type`) | 3486-3493 |
| `*lexical-callable-contracts*` | 9 | desugar | 6976, 7011, 7017 |
| `*expected-callable-contract*` | 5 | desugar | 3156, 8437 |
| `*contextual-closure-result-type*` | 11 | desugar | 3106, 3534, 6615, 6747-6749, 8475 |
| `*abort-lexical-context*` | 10 | desugar | 7088, 7187, 7188, 7970, 8169, 8313, 8369 |
| `*absence-mode*` | 5 | desugar | 3495, 3499, 20116 |
| `*absence-tail*` | 9 | inference only | 11004-11119 (10 binds, all inside `infer-expression-type-impl`) |
| `*loop-result-type*` | 7 | desugar | 7123, 8193, 8319, 8377 |
| `*loop-known-types*` | 7 | desugar | 7980, 8194, 8320, 8378 |
| `*lifting-lazy-thunk?*` | 6 | desugar | 6155, 6203, 6874, 3520 |
| `*loop-helper-names*` | 3 | inference | 12001 (one bind) |

**Group A: accumulators (a cell created by the driver or a pass, appended to during a walk, read after). 11
vars. Replaced by an `Acc` record that every desugar/inference function returns beside its Form.**

| var | cell | writes | readers after the walk |
|---|---|---|---|
| `*pending-loop-helpers*` | atom, fresh per defn (20066) | 6173, 6219, 7116, 7979 (`conj` a helper defn) | driver (`@loop-helpers`, appended to the defn's output) |
| `*pending-lambdas*` | atom `lambda-infos` (19996) | 3511 | lambda dispatchers, `preliminary-lambdas` |
| `*uses-apply?*` | volatile | 6849 | driver: injects `closure-apply-helper` |
| `*uses-lazy?*` | volatile | 8 sites (6873-6944) | driver: injects lazy take/drop |
| `*required-closure-dispatchers*` | volatile set | 3045 (`request-invoke-dispatcher`) | dispatcher construction (20200+) |
| `*loop-helper-shapes*` | volatile map | 7126, 7127 | `resolve-loop-helper-param-types`, `infer-loop-helper-results` |
| `*loop-helper-recorder*` | volatile map (11989) | 10956 | loop-helper inference |
| `*used-capability-keywords*` | volatile set | 3702, 3703 | `check-namespace-capabilities!` (17466), driver |
| `*local-state-used*` | volatile bool | 8937 | driver: whether `local-state` ran |
| `*abort-throw-types*` | volatile vector (11155, 14847, 14972) | 11149-11156 | `infer-abort-error-types` |
| `*state-handlers*` | volatile map; bound in `analyze-forms*` (20584) so a probe module analysed from `fold-def-value!` gets its own | 11127, 11137, 20141, 20150, 20319 (`vreset!`) | driver, `specialize-state-abilities`, `thread-state-abilities` |

**Group F: fresh-name counters. 4 vars. Replaced by `Fresh`, threaded like an accumulator.**

| var | scope | note |
|---|---|---|
| `*synthetic-counter*` | rebound to a fresh `(volatile! 0)` at 14630 and 14969 (abort), 15711 (state), 16408 (rewrite), 20014 (driver), 8563/9024 for local-state ids | Six independent restarts. Names stay disjoint only because each pass passes a different prefix. The port must keep six independent counters, not one global. |
| `*loop-counter*` | once per source (19980, 20001): "so loop-helper names stay unique across every defn" | Order of increment is traversal order; the differential test compares the names. |
| `*lambda-counter*` | once per source, seeded by `:lambda-id-base` (20003) | |
| `*local-state-ids*` | per `elaborate-local-state` call (9024) | |

Tally: M 10 + C 13 + A 11 + F 4 = **38**, every var in exactly one group.

Local (non-var) cells: 47 `(volatile! ...)` construction sites (driver 13, linear/kernel/slice 8, state
ability 6, abort 4, row-spec 3, the rest one each) and 2 `(atom ...)`. All 47 are local accumulators inside
one function and become `loop`/`reduce` state or a returned record. They are the easy half. The 38 dynamic
vars are the hard half because their scope is a dynamic extent across mutually recursive functions.

### The explicit env

Three records replace the four groups (`ModuleEnv` = M, `Ctx` = C, `Acc` = A and F). All are `(defrecord ...)` with types spelled out (Kotoba route
facts: `[:record :ns/N [[:f :type] ...]]`).

```clojure
;; kotoba.compiler.env  (Kotoba-only twin; the host route keeps the vars)
(defrecord ModuleEnv                       ;; group M, built once by the driver
  [schemas          [:list SchemaEntry]    ;; ns schema table + record schemas (one type: structural)
   function-arities [:list [:tuple :string :i64]]
   document-functions [:set :string]
   callable-results [:list [:tuple :string Form]]
   callable-params  [:list [:tuple :string Form]]
   record-dispatch  [:list [:tuple :string Form]]
   abort-errors     [:list [:tuple :string Form]]   ;; rebuilt per abort pass
   numeric-final    :bool])

(defrecord Ctx                             ;; group C, immutable, rebound by assoc
  [lexical      [:set :string]
   local-types  [:list [:tuple :string Form]]
   option-types [:list [:tuple :string Form]]
   callable-contracts [:list [:tuple :string Form]]
   expected-callable Form
   closure-result Form
   abort-context :keyword                  ;; :none | :loop | ...
   absence-mode :keyword                   ;; :legacy | :none
   absence-tail :bool
   loop-result Form
   loop-known  [:list [:tuple :string Form]]
   lifting-lazy :bool])

(defrecord Acc                             ;; group A + F, threaded, returned
  [loop-helpers [:list Form] lambdas [:list LambdaInfo]
   uses-apply :bool uses-lazy :bool
   dispatchers [:set :string] loop-shapes [:list [:tuple :string Form]]
   capabilities [:set :keyword] local-state-used :bool
   throw-types [:list Form] state-handlers [:list [:tuple :string Form]]
   loop-counter :i64 lambda-counter :i64 synth-counter :i64 cell-counter :i64])
```

Signatures: `desugar-expr : (ModuleEnv, Ctx, Acc, Form) -> DesugarOut{form, acc}`; inference is
`(ModuleEnv, Ctx, Acc, Form) -> InferOut{type, acc}`. A `binding [*x* v] body` becomes `body` evaluated
with `(assoc ctx :x v)`; a `vswap!` on a counter becomes `(assoc acc :synth-counter (+ n 1))` with `n` read
from the incoming acc, and every recursion returns the acc it produced (state passing).

Two consequences to plan for, both measured above:

1. `desugar-expr*` is one 1,936-line `cond` and 12 of its dynamic reads sit inside it. Threading `acc`
   through it means every branch's `mapv`/`map` over sub-forms becomes a fold. That is the real cost of S3,
   not the `Ctx` argument. Splitting it by head family first (one function per branch group, on the host
   route, byte-identical output) is the enabling refactor and can land on the host route before any port.
2. The abort and state-ability passes rebind `*synthetic-counter*` on purpose; a single `Fresh` record would
   change names. Keep them as separate `Fresh` fields (`synth-counter` per pass) and assert equality of names
   in the differential test.

The Kotoba-route facts that shape this: "aborting calls cannot precede recur" means tree walks must be
recursion (not `doseq`/`loop`), "if-branches must have equal types" means a `DesugarOut` is one record type
for every branch, and `atom`/`volatile!` may not be parameters or return values (status doc), which is why
`Acc` is a value, not a cell.

## (c) Dependency order and the first slice

### Order of the passes, from the driver (`analyze-forms**`, line numbers are the call sites)

```
read-forms (1735)
 -> rewrite-pure-application-forms (19763 region)         needs *pure-definition-names*, *state-handlers*
 -> reject-reserved-source-symbols! (19768)               unless :admit-linked-synthetics?
 -> check-pure-product-source-forms! (19770)
 -> expand-app-data-bytes-writes, expand-intrinsic-helper-forms (~19773)
 -> expand-state-ability-forms (19782)                    writes *state-handlers*
 -> expand-record-protocol-forms (19794), expand-closed-multimethod-forms (19799), expand-defdesugar-forms (19801)
 -> namespace-info, schema merge (19805-19830)            writes *row-op-schemas*
 -> constants: resolve-constant-aliases! / fold-def-value! (19847-19870)   RE-ENTERS analyze-forms*
 -> expand-defn-parts, variadic, check-affine-writes-module! (19898-19925)
 -> per defn: elaborate-local-state -> desugar (20050-20135)   Acc: loop helpers, lambdas, apply/lazy, capabilities
 -> specialize-state-abilities (20141)
 -> preliminary-lambdas (infer-absent-results on helpers) -> dispatchers (20160-20255)
 -> erase-slice-values (20262) -> loop-helper param types / results / recur check (20263-20270)
 -> type-literals (20279) -> specialize-row-parameters (20281) -> infer-absent-parameter-types (20288)
 -> a-normalize-aborts "abort_thrown" (20307) -> infer-abort-error-types -> check-state-abort-interaction!
 -> resolve-function-absences -> a-normalize-aborts "abort_operand" -> elaborate-aborts -> check-no-abort-before-recur!
 -> thread-state-abilities -> rewrite-record-projections -> retire-absence-markers -> infer-absent-results
 -> validate-interrupt-entries! -> elaborate-named-abilities -> infer-closure-refinements (20331)
 -> exports (20345-20360) -> slice/export check, capability check (20403), schema-ref checks
 -> validate-expr per function (20432)  + check-eager-recursive-let-bindings!
 -> check-value-types!, check-linear-resource-ownership!, check-kernel-region-provenance!, check-lowering-budget!
 -> infer-effects (20494) -> hir/validate! (20565)
```

Static dependency (which pass needs whose output): desugar needs Group M/C/A; every later pass needs the
types desugar left; abort and state passes each need the result types from the previous inference; the two
fixed points (`infer-abort-error-types`, `infer-closure-refinements`) need inference callable as a function
of `(functions, ModuleEnv)`. `validate-expr` and the seven `check-*` passes at the end are *sinks*: they take
the finished functions and return nothing, so they can be ported before anything they observe is produced by
the Kotoba route (they can be fed host-produced, serialized function bodies).

### Recommended port order

1. **Foundation (no pass):** `Refusal` record and `reject!`; `Sig`/`Env` records; tables that validation
   needs (from pass 0); `validate-value-type!` (pass 1); `edit-distance`/`nearest-names`.
2. **Slice 1: `validate-expr`** (below).
3. **Sinks:** `check-value-types!`, `check-linear-resource-ownership!`, `check-kernel-region-provenance!`,
   `check-lowering-budget!`, `infer-effects`, `check-affine-writes!` (passes 22, 23). These read Form and
   answer refusal or a summary; they need `ModuleEnv` but not `Ctx`/`Acc`.
4. **Independent pure rewrites:** pure-head rewrite (3), `lint` (28), `type-literals` (18), state-ability
   expansion (20). Each is `Form -> Form` with at most `Fresh`.
5. **Inference as a function** (12, 13, 14, 15): needs `ModuleEnv` + `Ctx(absence-tail, loop-*)`. Precondition
   for the two fixed points and for everything downstream.
6. **Abort passes** (19), **closure refinements** (21), **rewrite-record-projection** (16), **row-spec** (17).
7. **Desugar** (5-10) last: it needs the most env and produces every `__kotoba_` name. Split
   `desugar-expr*` on the host first.
8. **Driver** (27) plus constant folding (25) and expansion (26).

### The first slice: `validate-expr` over `Form`

Why this one, measured:

- 711 lines (pass 11), the smallest complete pass with a public API (`kotoba.sema/validate-expr` is
  exported at line 2 and re-exported).
- No dynamic vars, no calls into desugar/inference (checked by intersecting the 685 top-level names with
  the identifiers used in lines 9139-9759). Its dependencies are all leaves: tables (~40 `*-operations`
  sets and the `max-*` limits), `validate-value-type!` and 10 descriptor predicates, `unbound-symbol!`,
  `reject-call-arity!`, `reject-operation-arity!`, `let-body`, `if-parts`, `heterogeneous-vector-index!`,
  `rodata-literal-content?`, `refuse-reader-tagged-host-literal!`, `kotoba-integer?`, and
  `value/{bounded-string!, bounded-keyword!, *-limit}` (already ported as a subset in `kir/value`).
  Total closure is about 1,400-1,500 lines, 7% of the file.
- It is a pure predicate: `(form, locals, functions, depth, budget)` -> refuse or return. 96 `reject!` sites
  give 96 checkable refusal messages, which is the richest differential oracle in the file.
- It is called *after* everything else, so it can be run on the Kotoba route against forms the host
  route produced, with no other pass ported. The dump point is `analyze-forms**` line 20432: `(validate-expr
  body (set params) signatures 0 budget)`.

Interface (types spelled for the Kotoba route; `Form` is `kotoba.form` `:form/r`, tags 0-11, `span` packed
`line*2^32+column`):

```clojure
(defrecord Sig [name :string params [:list :string]])       ;; the `functions` map entry
(defrecord ValidateEnv [functions [:list Sig] locals [:set :string]])
(defrecord Refusal [message :string code :keyword span :i64 operation :keyword
                    form Form data [:list [:tuple :keyword Form]]])
;; Host `reject!` = (throw (ex-info message {:phase :subset :form .. :kotoba.error/code ..}))
;; Kotoba `reject` = (throw (Refusal ...)): the abort ability, [:result T Refusal] on the export.

(defn validate-expr [form Form  env ValidateEnv  depth :i64  nodes :i64] [:result :i64 Refusal])
;; Ok value is the node count consumed (`budget` was a volatile; it is now threaded:
;; each recursive call returns the new count).
```

Concrete rewrites inside the slice (each is a Kotoba-route fact from the task background):

- `(doseq [arg args] (validate-expr arg ...))` occurs **37 times** in `validate-expr-impl`. `doseq` lowers to
  a `loop`, and an aborting call cannot precede `recur`, so each becomes a call to one helper,
  `validate-all` (recursion over the kids list, threading `nodes`). That is a mechanical replacement of 37
  sites by one helper.
- `charge-node!` and the `budget` volatile become the threaded `nodes` counter.
- The two `(try (value/bounded-string! ...) (catch ...))` sites become a `[:result ..]` return of the ported
  `kir/value` functions. A capability call cannot be wrapped in `try`, but these are pure.
- `internal-failure!` (the `try ... catch Throwable` wrapper around the whole pass) is dropped on the Kotoba
  route: there is no host exception to translate; a trap is the internal error.
- The `Long/MIN_VALUE` reader conditional (`#?(:clj .. :cljs ..)`) gets a `:kotoba` branch: the literal is an
  `int` node, i64 by construction; the out-of-range case is decided by the reader.
- `(re-find #"[.]" (name op))` becomes `(string-contains? (symbol-value op) ".")`.
- `(count (get functions op))` becomes a scan of `functions` (a `[:list Sig]`, small).
- Dot-separated set membership (`contains? forbidden-heads op`) uses `[:set :string]` typed sets, which
  `contains?` supports.

Follow-on: the same `ValidateEnv` shape extends to `check-value-types!` and the other sinks without change.

## (d) The 219 `__kotoba_` uses

219 source lines, 87 distinct spellings (`grep -o '__kotoba_[A-Za-z0-9_$]*' | sort -u`). Classification by line,
from the full list (`grep -n '__kotoba_'`). Classification is by role, not by pattern, so counts are
approximate to about +-3 lines (a few template-binder lines could be argued either way).

| class | lines | what they are | how each becomes strings/Form |
|---|---:|---|---|
| **Prose** | 43 | Comments, docstrings and refusal messages that *mention* the prefix (e.g. `"symbol uses the reserved __kotoba_ prefix"`, the `__kotoba_cell_*` example at 8535-8540). | Nothing to do. Comments are not read; a message is a string literal, and the reserved-symbol rule refuses *symbols*, not strings. |
| **Helper source text** | 79 | Bodies of synthesised functions: closure apply (3595-3614), lazy take/drop (3617-3651), the string-source intrinsic helpers (3903-3995, already a string), `string-from-i64`/`char` (5399-5430), document helpers (5474-5524), `map-get`/`map-without` (5724-5777). The first two families and the map/doc families are quoted forms; the intrinsic family is already a string parsed by the reader. | One mechanism for all: keep them as **strings** (`helper-source-text`), parse them with the Kotoba reader twin at injection time, tagged as linked synthetics (the existing `:admit-linked-synthetics?` path skips the reserved-symbol scan; the scan already runs before injection, at 19768). The 47 lines of quoted-form helpers are converted to text; the intrinsic family (`intrinsic-helper-source`, 3903) is the pattern. Cost: one `read-forms` call per injected family per module. Ordering hazard: helpers parsed after `expand-intrinsic-helper-forms` must not be re-scanned. |
| **Literal marker heads** | 65 (about 30 distinct heads) | Internal ops that desugar *writes* and later passes *read*: `__kotoba_absent` (10), `__kotoba_present`/`some_bind`/`some_last`, `__kotoba_destructure_get`, `__kotoba_document_of` (10), `__kotoba_pair_sequence`, `__kotoba_closure_apply`, `__kotoba_match_has`, the eight `__kotoba_state_*` heads, `__kotoba_recur_position__`, and template binders (`hof_acc`, `hof_x`, `sel_m`, `kept`). | A `kotoba.compiler.synth` module of **constructor/recogniser pairs over Form**, e.g. `(absent-form mode)` -> `(form-seq [(sym "absent") ...])` and `(absent-form? f)` -> `(and (is-seq? f) (sym-is? (first-of f) "absent"))`, with `(defn sym [tail :string] (symbol-form (str (reserved-prefix) tail)))` and `(defn reserved-prefix [] "__kotoba_")`. The prefix is a *string* in the module, so the frontend's own source never spells a reserved *symbol*. Every `(= '__kotoba_x (first form))` (about 30) becomes `sym-is?`. `case` on these symbols (11066, 11125) becomes a `cond` on `symbol-value`. |
| **Synthetic minting** | 21 | String concatenations that build a fresh symbol: `synthetic` (3827, the single counter-based mint), `chain-temp` (3802), invoke/lambda/closure names (3019, 3515, 3552, 3554), loop helpers (7094, 15555), cells (8661, 9039), state clones (15232, 15566), slice names (17133, 17136), rest args (3456, 17973), template params (18761), protocol impls (19638), inference stand-ins (20167-20168). | `Fresh` counter plus `(mint tail n)` -> `(symbol-form (str prefix tail "_" (int->str n)))`, i64 in `str` is supported. Two are not counter-based (`__kotoba_invoke` + arity/type key, `__kotoba_state_<f>_under_<h>`); those keep a deterministic key, and the differential test checks the spelling. `(gensym ...)` fallback (18 uses; taken when no counter is bound) must not survive: on the Kotoba route there is always a counter, so the `if *synthetic-counter*` branch collapses to the counted branch. |
| **Prefix tests** | 11 | `starts-with?` on `"__kotoba_map_source_"`, `"__kotoba_filter_v_"`, `"__kotoba_reduce_v_"`, `"__kotoba_mapindexed_v_"` (3136-3140), `reserved-binding-name?` (3831), `intrinsic-helper-name?` (4006), cell decode (8677-8678), invoke regex (16001), generated-name test (16034), loop-name regex (18396). | Plain string ops on `symbol-value`. Three of them use regexes (`#"(\d+)_(\d+)_(.+)"`, `#"__kotoba_invoke(?:_.+)?\$arity[0-4]"`, `#"__kotoba_loop_\d+"`); those are hand-rolled scanners (split on `_`, parse int), 10-20 lines each, under the same regex wall as elsewhere in the file (6 regex lines total). |

Consequences for the plan: (1) the plan's item 3 ("synthetic function, not written as literals") is met
by `synth` alone; no reader change is needed for the frontend's own source, because after this table no
`__kotoba_` *symbol* is left in it (all uses are prose, string literals or helper text). (2) The reserved-
symbol scan stays exactly as is for authored source. (3) `admit-linked-synthetics?` must be carried
through the driver signature unchanged because the differential test uses it (linked modules contain
synthetic names).

## (e) Differential-test design: host route vs Kotoba route

Goal: for every input, the Kotoba-route frontend and the host-route frontend agree on the accept/refuse
decision, on the refusal (message, code, span, operation), and on the HIR, byte for byte after
canonicalisation. It is run per slice (so a divergence localises to a pass) and end to end.

**Oracle.** The host route (`kotoba.sema/analyze` on nbb and JVM) is the specification. Nothing in this
document changes it.

**Three comparison levels.**

1. *Slice level (from slice 1).* Input `(form, locals, functions)` serialised as EDN; output `ok nodes` or a
   refusal map. For `validate-expr` the input corpus is every function body at the dump point
   (`analyze-forms**` line 20432), collected by wrapping `frontend/validate-expr` on the host while the
   suite runs.
2. *Pass level (later slices).* Input the function list before pass P, output after it, as canonical EDN,
   captured by a host-side tap after each `parsed (...)` binding in the driver (about 25 taps). The tap is a
   `tap>` in a test-only wrapper so the production driver is untouched.
3. *End to end.* `analyze(source, opts)` returns HIR or throws. Compare canonical HIR.

**Canonical form.** Recursively: maps sorted by `(pr-str key)`, sets sorted, symbols and keywords printed
with `pr-str`, integers as decimal, f64 by IEEE bits, and metadata dropped except `:span`. Both routes
serialise through the *same* function (host: `pr-str` on the canonicalised value; Kotoba: `Form` printed
by the Kotoba printer, which must be byte-identical). Known noise to normalise on the host side instead of
hiding: hash-ordered iteration (48 `sort` sites exist for a reason; any `(keys m)` or set-to-seq that
reaches a message or a vector is a bug the differential will find, not something to mask), `gensym`
fallbacks (must not appear), and the `:form` in an `ex-data` (compare `pr-str` of the form's Form).

**Corpus (measured).**

| source | size | use |
|---|---:|---|
| `kotoba-sema/test/kotoba/compiler/*_test.cljk` | 80 files, 876 `deftest`, 384 `analyze` call sites | Accept and refuse cases with a known reason. Extract each analysed string by wrapping `frontend/analyze` (record source, opts, result-or-refusal) and running the suite once on the host: the recording is `corpus/analyze.edn`. Suite time is unchanged; the recording is a side effect of a tap. |
| `.kotoba` sources across the workspace | 8,687 files, **3,646 distinct** by md5 (excluding worktrees: 3,658 with) | Accept-path bulk. Each is run through host `analyze`; the ones that pass become accept cases, the ones that refuse become refuse cases with the host refusal as expected value. |
| compiler's own sources that already `amu check` on the Kotoba route | 57-66 modules | End-to-end smoke: the frontend, once ported, must analyse them identically. |
| mutations | generated, seeded | For each accepted program: delete one token, swap two adjacent tokens, rename a bound symbol to an unbound one, add one argument to a call, change an integer to `2^63`. 20 mutants per accepted case gives about 70k refusal cases, mostly one `reject!` each. This is the coverage source for the 757 `reject!` sites: measure which sites were hit (a `reject!` wrapper that records `(code, message-prefix)`) and report the uncovered set. |

**Runner.**

```
diff-run <corpus.edn> [--level slice|pass:N|e2e]
  host   : nbb  (node --stack-size=4096 nbb/cli.js ... -e (analyze ..))      -> canonical bytes H
  kotoba : amu-built frontend module, run on the Kotoba runtime, same input  -> canonical bytes K
  compare: H == K per case; on mismatch print the case id, the first differing path,
           and the pass tap where the two traces first diverge
```

It sits beside the wall harness: `wall-one.sh` measures *compiles*, the differential measures *agrees*. A
module counts as ported only when both hold. The metric per slice is `agree / total` over the corpus with
zero tolerated mismatches; the wall count alone (66/162) is not accepted as progress on the frontend.

**Gates per stage.**

| stage | must agree on |
|---|---|
| slice 1 (`validate-expr`) | all body forms from the corpus (accept) and all 96 refusal sites reached by mutation |
| sinks | every `check-*` refusal; `infer-effects` result |
| inference | every function's `:result`, `:param-types`, `:effects` after the pass |
| abort/state | function lists after `elaborate-aborts` and `thread-state-abilities` (names included) |
| desugar | function lists after desugar, **including every synthesised name** (counter order) |
| end to end | canonical HIR for the full corpus |
| bootstrap (S5) | Kotoba-built frontend compiles itself; the HIR of `frontend.cljk` equals the host's |

**Known hazards, measured from the source.** (1) `pr-str` at 81 sites: messages embed printed forms, so the
Kotoba printer must match Clojure's for symbols, keywords, strings with escapes, nested collections and
`nil`; treat the printer as its own slice-0 item with its own 1-to-1 test. (2) Hash order of sets and maps
in messages. (3) `meta`-carried spans: 124 uses, 28 in `rewrite-record-projection`; the Form v2 `span` slot
is packed `line*2^32+column`, and end line/column/offset (`form-span` reads six keys) are not in it. The
differential's span comparison decides whether Form needs a wider slot before pass 16. (4) Integer literals
above i64 (`BigInt` on the host); the reader decides, so the slice-1 corpus needs its own boundary cases.
(5) The `analyze` wrapper turns a host stack overflow into a refusal (`host-nesting-exhausted`); on the
Kotoba route the stack limit is different, so `max-reader-depth` cases are compared on the refusal code only.

## Appendix: commands used

```
wc -l frontend.cljk                                   # 20704
grep -c '__kotoba_' frontend.cljk                     # 219
grep -n '__kotoba_' frontend.cljk                     # per-line classification (kb.txt)
grep -c '^(def \^:dynamic\|^(declare \^:dynamic' ...  # 39 declaration lines, 38 vars
grep -c '(volatile! ' ...; grep -c '(atom ' ...       # 47 construction sites; 2 atoms
sed -n 9139,9759p frontend.cljk | grep -o '\*[a-z?-]*\*'   # no output: validate-expr reads no dynamic var
grep -c 'doseq' <validate-expr-impl>                   # 37
grep -c '(reject! ' frontend.cljk                      # 757 ; 96 inside validate-expr
find . -name '*.kotoba' | xargs md5 -q | sort -u | wc -l   # 3,646 / 3,658
```
