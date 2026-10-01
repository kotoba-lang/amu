# Selfhost S3: the frontend's type model, signatures and env on the Kotoba route (2026-10-01)

Scope: `kotoba-sema/src/kotoba/compiler/frontend.cljk` (19.9k lines) checked by `amu check` on the
project route (`WALL_CP=/private/tmp/wall-cp-9.txt`). Continues `docs/selfhost-core-rewrite-plan-20260930.md`
(S3, slices 2 and 2b). Nothing here changes the JVM/nbb behaviour: every port is a `#?(:kotoba X :default Y)`
pair and `Y` is the byte-identical original.

## 0. What the wall actually is (measured)

`amu check frontend.cljk` on the project route is a sequence of **whole-module phases**, each walking the entire
file and stopping at its first refusal. The earlier reading ("first refusal at 4206") mistook one phase's first
hit for the frontier of the file:

1. read + reader conditionals (`:kotoba` feature);
2. a pre-pass that refuses a *type-descriptor literal with a computed part*
   (`[:record (keyword ...) fields]`) wherever it appears. Line 4206 was the first hit of this pre-pass.
   Clearing `map-literal-record-type` and `record-descriptor` (the only two such sites) moved the report to
   line 257 (a host regex): the bodies had not been walked yet;
3. desugar of every function (whole file): refuses `(map (fn [[k v]] ...) x)` (the item of a vector-i64
   source has no positions), `(quote (list))` literals, `doseq` binding shapes, atoms, ...;
4. per-function analysis **in file order**, names resolved against Kotoba builtins only.

Reported `:span` lines are unreliable (they fall back to an earlier known position, often 95-97 or 1341); the
reliable locator is the function. A temporary "current function" suffix on the host `reject!` message was used
to name it and is not committed.

**Where the frontier is now.** After this work phases 1-2 are clear for the whole file and phase 4 is clear for
the 57 ported definitions; the report is a phase-3 refusal, `map fn parameter destructures ([k v])`, the first of
92 such lambdas in the Kotoba view of the file (the view has 566 `defn`s, 737 `reject!`, 178 `{:keys ...}`
destructurings, 72 volatile/atom uses, 60 `binding`, 40 `^:dynamic` vars, 192 `doseq`/`for`, 52 `loop`, 119
`reduce`, 64 `catch`).

**Per-function probe (first blocker of each function taken alone; 400 of ~520 functions ran, then the probe
was stopped).** `analyze` on each function in isolation with a dummy export. Two classes are probe artifacts
(a function that calls another function of the module, or a Kotoba branch that uses the `form/` / `vt/` aliases,
cannot resolve them in isolation): they are shown so the real classes are not over-read.

| first blocker | functions |
|---|---|
| unknown operation: a host core function with no Kotoba meaning (`seq`, `meta`, `name`, `pr-str`, `keep`, `every?`, `tree-seq`, `nth`, `dorun`, ...) or `reject!` | 90 |
| `count` / `get` / `contains?` / `keys` on host data ("requires a bounded vector, a typed set or a canonical typed map; got :i64") | 60 |
| unbound symbol (other module functions and dynamic vars; part probe artifact) | 58 |
| fn / `map` callback / `doseq` destructuring | 31 |
| type mismatch, `case` constants, equality operand types | 22 |
| quoted list literals (`'(option-none)`): "quoted list has no literal spelling" | 10 |
| atoms / `swap!` / `deref` | 6 |
| `try` without an abortable body | 2 |
| qualified call, probe had no aliases (artifact) | 88 |
| admitted as written (tiny predicates) | 12 |
| other (juxt, `some` with a predicate, `into` with a transducer, regex literal, ...) | 19 |

The conclusion is structural, not a list of missing builtins: a host-style function is outside the typed Kotoba
subset from its first line, so every one of the ~566 functions is a rewrite over Forms, and ports cannot be
verified by the file-level check until the frontier reaches them. Hence the verification device in section 4.

## 1. Representation

### 1.1 One dynamic value: `:form/r`

Every host value the frontend passes around is a `:form/r` tree (`kotoba.form`, tags nil, bool, int, string,
keyword, symbol, list, vector, set, map, f64, bytes; `span` = line * 2^32 + column):

* **type descriptors** are Form vectors: `:i64` is a keyword Form, `[:option T]`, `[:list T]`,
  `[:record :ns/Name [[:f T] ...]]`, `[:fn ...]` are `form-vec` nodes. Equality of two descriptors is
  `form/eq` (structural; sets and maps unordered), which is what `=` is on the host. The descriptor
  predicates are `kotoba.compiler.value-type` (`option-type?`, `list-type?`, `record-type?`,
  `callable-type?`, `schema-ref-type?`, ...), exported so the frontend and `validate_expr` share them.
* **function signature maps** (`{:name :params :param-types :result :effects :body ...}`) are Form maps keyed by
  keyword Forms; a read is `(form/form-get m (form/keyword-form :result))`. The keyword constants are
  cheap (`keyword-form` allocates a leaf); a module that reads the same key in a loop hoists it.
* **fixed-key parts** (`{:name :type}` field parts, `{:types :names}` protocol parts) are also Form maps.
  They are not promoted to records: the host code destructures them with `:keys`, and a Form map keeps the
  port line-for-line with the original. A hot pass can later switch one to a `defrecord` behind the same
  accessor names.
* **builders** construct descriptors from Forms, never from a Kotoba vector literal with computed parts:
  `(form/form-vec (form/three-forms (form/keyword-form :record) id fields))`. This is why the
  pre-pass above refuses `[:record (keyword ...) fields]`: in a Kotoba expression, a vector headed by a
  type keyword *is* a type descriptor, and a descriptor's id must be a literal.
  Landed: `map-literal-record-type`, `record-descriptor`.

### 1.2 The analysis env is an explicit record

The host binds ~30 dynamic vars around each pass (`*schemas*`, `*local-types*`, `*local-option-types*`,
`*function-arities*`, `*loop-counter*`, `*lexical-bindings*`, `*abort-error-types*`, ...). A Kotoba function
cannot see a dynamic binding, and 40 of them are exported by name. The Kotoba route replaces them with one
record threaded through every pass, in the style `validate_expr.cljk` already uses (`:vx/env`):

```
:fe/env [[:schemas   Form]   ; *schemas*            keyword -> descriptor map
         [:locals    Form]   ; *local-types*        symbol  -> descriptor map
         [:options   Form]   ; *local-option-types*
         [:arities   Form]   ; *function-arities*   symbol  -> arity map
         [:contracts Form]   ; callable result/param contracts
         [:counters  ...]    ; loop / lambda / synthetic counters as :i64 fields
         ...]
```

A pass is `(env, Form) -> (env', Form)` when it advances a counter, `(env, Form) -> Form` otherwise. `binding` becomes
`assoc` on the record for the extent of the call (a value, so no unwinding). Counters (`volatile!`) become
`:i64` fields returned with the result: the host's `(vswap! nodes inc)` is `(+ nodes 1)` passed on. Done
already in `value_type.cljk` (node counter through `:vx/r`) and as `validate-value-type-counted!`.

The env is *not* exported as vars. The exported dynamic vars become the env's field names on the module
interface; the host keeps its vars.

### 1.3 Refusals are aborts, with a discipline

`reject!` cannot throw on this route, and 45 of the 68 `catch` sites are probes (try to infer, fall back
to `nil`), so a trap-and-exit model would remove the probes rather than port them. The language already has
the tool: typed `throw`/`try`/`catch` (ADR 0007), elaborated to `[:result T E]`. The frontend uses one error type:

```
:fe/err [[:msg :string] [:code :string] [:form :form/r] [:phase :string]]
```

`fe-error` / `fe-read-error` build it. The ADR's restrictions become the porting discipline:

* a throw (or a call of an aborting function) is in **tail position or a `let` binding value**. A host
  statement `(when-not ok (reject! ...))` becomes `(let [_ (when-not ok (throw ...))] rest)`; a `doseq` that
  rejects becomes a recursion.
* **no throw inside `loop`**. A loop that may reject is split: the loop *answers* (a bool or a code), and
  the caller throws. Example landed: `reader-depth-exceeded?` (loop, answers) + `check-reader-depth!` (throws).
* **an exported function cannot abort** (its interface would be `[:result T E]`, which the wire ABI does not
  carry). Exported entry points (`read-forms`, `analyze`, `lint`, `validate-expr`, `interrupt-entry-vector`)
  catch at the boundary and return a record (`ok` / value / `:fe/err`). The internal `!` functions abort.
* a probe `(try (infer x) (catch _ nil))` is `(try (infer x) (catch [:fe/err] e <none>))` with the
  none value of the probe's result type (a Form nil, an option, or `-1`).

### 1.4 Text

`string-length` is **UTF-8 bytes** on this route, an index is a byte offset, and `string-code-point-at` refuses
an interior byte. A scan that must visit every code point steps by `code-point-width`; a scan that stops at the
first non-ASCII byte (hex, digits) needs no stepping. Host regexes are ported as scans (`hex-text?`,
`guid-text?`, `interrupt-entry-vector`, ...).

## 2. Module boundary

New helpers live in `frontend.cljk` under `#?(:kotoba ...)` (a Kotoba-only helper is
`#?(:kotoba (defn- ...) :default nil)`), because the host must not require Kotoba-route modules. Shared
descriptor logic lives in `value_type.cljk`, which the frontend requires as `vt` under `:kotoba`. The
frontend and `validate_expr.cljk` therefore agree on the predicates by construction.

Signature convention for a ported function: every dynamic parameter is `[:ref :form/r]`; scalars stay
`:i64`/`:bool`/`:string`; the return is a Form, a scalar, or (aborting) the same. Where the host returns
`nil` for "none" the Kotoba branch returns `(form/nil-form)` and callers test `form/is-nil?`.

## 3. Port order (dependency order, each step ends with a measured frontier and a nbb load check)

1. Descriptor **builders** (`map-literal-record-type`, `record-descriptor`) - landed (kotoba-sema 7064083).
2. Descriptor **predicates** over `vt` (`callable-type?` ... `structured-type?`, `callable-clauses`,
   `slice-element-type`) - landed.
3. `validate-value-type!` as `validate-value-type-counted!` over `vt/validate-type` - landed.
4. Bounded readers and literal predicates (`integer-literal?`, `hex-text?`, `rodata-literal-content?`,
   `alloc-region-bytes`, `interrupt-entry-vector`, `heterogeneous-vector-*index!`, `check-reader-depth!`) - landed.
5. `:fe/env` and the dynamic var block (`*schemas*` ... ): declare the record, port `resolve-ref-type`,
   `record-field-type`, `option-vector-type?`, `absence-type`, `resolve-option-type` on it. Landed so far:
   `resolve-ref-type`, `record-field-type` (schemas as an explicit Form argument) and `option-vector-type?`; the
   record itself and `absence-type` onward are not.
6. `read-forms` over `kr/read-forms` (the typed reader twin already returns `:form/r`).
7. desugar (`desugar-expr` family, ~4000 lines), then `infer-expression-type-impl` / `infer-call-type-impl`
   (~1800 lines, the table-driven core), then the abort and loop passes, then `analyze`.

## 4. Verification

* Host: `node --stack-size=4096 .../nbb/cli.js --classpath "<wt-A src>:$(cat wall-cp-9.txt)" -e "(require 'kotoba.compiler.frontend)"`
  after every step, plus the sema suite against the pre-change tree (same classpath, old `src` first): see the commit
  notes for the numbers.
* **Per-definition differential (landed): `scripts/selfhost-wall/tm-diff.sh`.** `tm-gen.py` expands the reader
  conditionals of frontend.cljk with the `:kotoba` feature, picks the definitions named in `tm-names.txt` and appends
  `tm-tail.cljk` (a case dispatcher `tm-run`). The resulting stand-alone module is checked by `amu check` (this is how
  the ported definitions are verified while the file-level frontier is still far away: it passed `OK`) and run on the KIR
  interpreter; `tm-diff.cljs` calls the host functions on the same corpus and compares one line per case. Descriptors
  are compared inside the guest with `form/eq`, so the host data is printed to EDN and read back as a Form.
  First run: 958 cases (hex/guid/ucs2/bytes literal content, interrupt entry names, alloc-region pages, record
  descriptor builders, 16 descriptor predicates over 45 type shapes, `callable-clauses`, `slice-element-type`,
  reader depth over 15 sources, `validate-value-type!` over 60 types, heterogeneous index/slice refusals,
  `resolve-ref-type` and `record-field-type` over 5 schema maps), 958 agree, 0 disagree.
  Not in the corpus: non-ASCII text (the EDN hand-off), and `[:fn 1]` (the host dies with an internal
  "1 is not ISeqable"; the guest refuses with the callable-type message, a host defect on malformed input).
* File level: `amu check frontend.cljk`; the frontier is the function/phase named by the refusal.

## 5. Next walls, in order

1. **Phase 3 (desugar) over the whole file**: 92 destructuring `map`/`mapv` lambdas, the quoted-list literals, `doseq`
   binding shapes and atoms. Each is inside a function that needs its Form port; the order is dependency order
   (section 3, steps 5-7). Every function ported moves one site out of the view.
2. **The env (`:fe/env`) and the dynamic var block** - required by every pass that reads `*local-types*`,
   `*schemas*`, `*function-arities*`, ... (lines ~1390-1620). Until this lands a ported function has to take its
   dynamic inputs as explicit arguments, as `resolve-ref-type`/`record-field-type` now do.
3. **`reject!` call sites as tail/let throws.** 737 sites; most are statement-position `(when-not ok (reject! ...))`
   and need the `(let [_ ...] ...)` rewrite, which moves code rather than translating it.
4. **Speculative `try`/`catch`** (45 probe sites) on the abort type.

## 6. Desugar on the Kotoba route (2026-10-01): the env, the dispatcher, the differential

Continues section 3 step 7. The desugar half of `frontend.cljk` (`desugar-expr*` and the `desugar-*` family) is ported
function by function under `#?(:kotoba ... :default <host text>)`; every host body is byte-identical, only wrapped.

**The env (`:fe/env`, section 1.2) now exists.** One record threaded by value: the synthetic-name counter
(`*synthetic-counter*`), the contextual closure result type (`*contextual-closure-result-type*`, `nil-form` for none),
the absence mode, the module's function arities (`*function-arities*`), lexical bindings (`*lexical-bindings*`), local
types (`*local-types*`), document-returning functions, the loop counter, schemas, the lazy/abort context, the used
capability set, and `tbl`: the constant tables the dispatch reads, parsed ONCE per env (a Kotoba table accessor re-reads
its EDN text on every call, so a per-head lookup is a parse). A pass is `(env, Form) -> :fe/dr {env' form'}`; a list of
forms is `:fe/drs`. `binding` is `with-result` / `with-lexical` on the record for the extent of the call, restored on
exit, exactly the dynamic extent of the host's `binding`. The counter is threaded in the host's evaluation order (the
order of `synthetic` calls is part of the output: `__kotoba_and_2` ... names), which the differential pins.

**Refusals** are `:fe/err` throws (section 1.3): `require-k` is the `(when-not ok (reject! ...))` statement as an
aborting function bound in a `let`. Two discipline points found the hard way: an `if` whose branches abort cannot be a
`let` VALUE (hoist the `if` into a helper function so the aborting call is in tail position), and `odd?`/`even?` do not
exist (`rem`); a type error in any function hides behind "call to aborting function ... neither catches it" because
abort-error-type inference skips a function whose body fails to type.

**Ported (Kotoba bodies over `Form`):** `desugar-expr`, `desugar-expr*` (atoms, keyword accessors, beta redexes, vector
literals, the whole contextual-argument table chain, the ordinary-call fall-through, named operations, namespaced
`clojure.core/X`), `desugar-result-expr` / `desugar-expected-value` (with `canonical-closure-result-type`,
`closure-result-type?`, `closure-default-value-expr` as `default-kind`), `desugar-bool-expr`, `desugar-tail-expressions`,
`desugar-and/or/do/cond/condp/cond-thread/thread/as-thread/some-thread/comparison-chain/case/binding-if`,
`desugar-vector-i64-source`, `desugar-binding-some`, `desugar-quoted-datum`, `desugar-list` (as `desugar-list-arm`), `desugar-ordinary-call`, `sequenced-body`,
`thread-form`, `synthetic`, `chain-temp`, `absence-marker?`, `absence-marker-form`, and the arms of the host's `case op`:
`if do let (symbol patterns) not not= = < > <= >= zero? pos? neg? empty? first second rest cons some some? nil? bytes get
contains? dissoc assoc select-keys merge assert str string-length string-from-i64 inc dec rem mod when when-not if-not
if-let when-let throw try catch vector-i64 vector-f64 xorshift32 record record-new record-get record-assoc
hetero-vector(-new/-assoc) typed-list-new typed-set(-new) typed-map-new variant-new match-variant variant-match
match-result result-match-of option-match match-option`, and the 30 table-driven typed operations
(`typed-list-nth ... option-or`, one spec table `typed-op-specs`: arity, message, operand kinds).
22 of the 31 `desugar-*` definitions (`quoted-datum` partly: a symbol, a vector of symbols, an atom; the other nine:
`lexical-call`, `map`, `map-against-record`, `match`, `dotimes`, `doseq`, `dataspace-form`, and the template expander's
`desugar-template-parts`).

**Scaffolding that shrinks:** `unported-heads` is the set of the host's `case op` heads without a port; such a head is
refused as `kotoba.fe/unported` (never treated as an ordinary call). Everything outside that set and outside the
ported arms is an ordinary call, exactly as the host's final clause.

**Not ported, and why it is one wall, not a list:** `fn` (lift-lambda), `loop` (recur helpers), `dotimes`/`doseq`/`reduce`/
`map`/`filter`/`into` (all lower through `loop` and the lifted-helper registries `*pending-lambdas*`,
`*pending-loop-helpers*`, `*loop-helper-shapes*`, which are atoms/volatiles on the host and have to become env fields
returning appended helper definitions), the map/set literal lowering (`desugar-map`, sorted by `pr-str` on the host, i.e.
a printer-order dependency), quoted data, document-context lowering, `destructure-binding` (vector/map patterns in
`let`), and `match`. Those are the destructuring lambdas that keep the file-level frontier where it was.

**Differential (`scripts/selfhost-wall/ds-diff.sh`).** `ds-gen.sh` expands the `:kotoba` view of `frontend.cljk`
(tm-gen.py with `TM_NAMES`/`TM_TAIL`/`TM_HEADER`), which `amu check` accepts as a stand-alone module and the KIR
interpreter runs. `ds-diff.cljs` takes every `(ns ...)` program embedded as a string in kotoba-sema's tests plus the
`.kotoba` programs under `DS_EXTRA`, reads each with the frontend's reader, and makes every list form inside a
function a case (deduplicated, `DS_MAX` per program, `DS_TOTAL` sample). The host runs `desugar-expr` (with
`*synthetic-counter*` and `*function-arities*` bound); the guest runs its port and compares with `form/eq` against the
host's printed answer (or the refusal message). A guest answer of `UNPORTED <head>` is counted, never compared, so the
figures are "agreement where the port claims to answer" and "coverage".

**Measured (2026-10-01).** 523 forms (every list form inside the functions of the sema test programs and of the
kotoba-lang `lang/stdlib`, `examples`, `bench`, `lang/migration-pilots` programs, `DS_MAX=300 DS_TOTAL=1500`): 462
compared, **462 agree, 0 disagree**, 61 unported (24 map/set/f64 literals, 17 `invoke`, 7 `:document` context, 5
document-head lowering, `eval`, `map`, `char`, `assert!`, `map-indexed`). Host behaviour unchanged: the sema suite
(`run-tests.cljk` on nbb) has the same 77 failures / 25 errors, the same tests, before and after.

## 7. The registries as env fields; the rest of the desugar half (2026-10-01)

Section 6 ended on one wall: the heads that lower through `loop` or lift a lambda need the state the host keeps in
dynamic vars. That wall is gone; the state is `:fe/env` fields and the heads are ported.

**The fields** (every module that declares the `:fe/env` schema carries the same line): `helpers` (a Form vector of the
synthesized definitions `*pending-loop-helpers*` collects: loop helpers, lazy-map/lazy-filter helpers), `shapes`
(`*loop-helper-shapes*`: helper name -> `{:bindings n :declared-result t :known-types m}`), `loop-result` and
`loop-known` (`*loop-result-type*`, `*loop-known-types*`), `lambda-counter` and `lambdas` (`*lambda-counter*`,
`*pending-lambdas*`: `{:id :arity :captures :helper {...}}`), `dispatchers` (`*required-closure-dispatchers*`, a set of
`[result arity]`), `uses-apply`, `uses-lazy`. A pass returns the grown env exactly as it returns the synthetic counter, so
the order of `__kotoba_loop_N` / `__kotoba_lambda_ID_arityN` / `__kotoba_*_N` names is the host's evaluation order, and the
caller of the whole analysis reads the helper definitions back from the final env. `binding` of the loop overrides, the
absence mode, the lexical set and the abort context is "set the field for the extent of the call, restore it after".

**Ported over Form** (host bodies untouched): `loop` (free-variable capture, `recur` replacement, the parameter ceiling
message), `dotimes`, `doseq` (binding-vector parser, modifiers, the 16-wide unrolled blocks, the pair-sequence cursor walk
and the counter the host advances for the pair form it builds even for a vector), `filter`/`remove`, `reduce` (with and
without init; primitive, named, inline and stored callbacks; map chains; list and document sources), `map` (1-5 sources,
packed sources, stored callbacks), `map-indexed`, `mapv`, `filterv`, `into` (and its transducer rewrite), `fn` (fixed and
variadic clauses, multi-arity, captures), `fn-ref`, `apply`, `invoke`, direct calls of a local closure, `take`/`drop`,
`lazy-cons`/`lazy-first`/`lazy-rest`/`lazy-empty?`/`lazy-map`/`lazy-filter`, `char`, `string-join`, `match`, `let` with
vector/map destructuring (`destructure-binding`: `:keys`, `:ns/keys`, `:or`, `:as`, explicit entries) and the `:i64` /
`:document` local-type tracking of the `let` arm, `assert!`/`retract!`/`observe!`/`facet-enter!`/`facet-leave!`,
`cap-call`/`typed-cap-call`/`eval`, closed document literals (`document`, and any closed literal in a `:document` context),
the collection heads over a document, map literals (pair map, closed anonymous record, typed map, the record named by the
context), set literals and f64 literals. `unported-heads` is empty.

**Discipline found on the way.** (1) A `:bool` record field must hold a real boolean: a comparison's 0/1 is accepted by `if`
but not stored, "value is not a boolean" (`with-none` normalizes through `if`). (2) An aborting call may not be an argument of
another call (not in tail position, not a `let` value): bind it first; an `if` whose branch aborts cannot be a `let` value, so
hoist it into a helper. (3) `form/is-nil?` on an absent key is `nil-form`, so "absent" and "present and nil" must be told
apart with `form-has?`. (4) A name defined both under `#?(:kotoba ...)` and as a plain host `defn` in the same module is two
definitions on the Kotoba route: either wrap the host text as `:default` or give the Kotoba function another name.

**Still refused by name** (never an ordinary call): a dispatcher family over a structured result type (its name is a SHA-256
of the descriptor), an `:f32` context for a float literal (the exact-or-refused narrowing), quoted symbol sets / maps and the
refusals of quoted data, and the float-literal reader shape that the host recognizes by reader metadata (a Form cannot carry it).
`desugar-template-parts` is the template expander's, in `namespace_defs`.

**Differential** (`scripts/selfhost-wall/ds-diff.sh`). A case now agrees only when the form AND the five side registries
(`helpers shapes lambdas dispatchers uses-apply uses-lazy`) are equal; the host binds each var to a fresh atom/volatile on
its owning module (the facade's dynamic vars are snapshots after the split). Integers printed by the host as
`#object[BigInt N]` used to drop a case before the comparison (roughly half of the corpus did not reach it); `norm` fixes
that. `let` and `loop` forms are cases again. A trapping batch is rerun case by case and the trapping case named.
`scripts/selfhost-wall/ds-corpus/*.kotoba` are programs written for the differential, each with its refusals.

**Measured (2026-10-01, guest from kotoba-sema 89a0e79).** `ds-diff.sh` over every list form of kotoba-sema's test programs, kotoba-lang
`lang/stdlib`, `examples`, `bench`, `lang/migration-pilots` and `scripts/selfhost-wall/ds-corpus` (`DS_MAX=200 DS_TOTAL=900`): 900
forms, **899 compared, 899 agree, 0 disagree**, 1 unported (`(eval (quote (+ 40 2)))`: the refusals of quoted data). Before the ports
of this section the same figures were 818 of 900 compared (section 6's coverage was measured on a corpus that lost roughly half of
its forms to the BigInt printing, 462 of 523). `ds-corpus` alone: 345 of 345 agree, 0 unported. Host behaviour unchanged:
`amu refactor verify --runner run-tests.cljk` of the tree after the ports against the tree before them: 620 tests, 2147 passed,
77 failed, 25 errors on both sides, 205 outcome lines each, differences 0.

Of the 31 `desugar-*` definitions, 28 are ported (`lexical-call`, `dotimes`, `doseq`, `match`, `map`, `map-against-record`,
`dataspace-form` joined section 6's 22; `quoted-datum` is complete except sets / maps / refusals), left: `desugar-template-parts`
(the template expander's, in `namespace_defs`) and the quoted-data refusals. The first whole-file refusal of the facade is no
longer in the desugar half: `amu check` of `frontend.cljk` stops at `frontend/base.cljk:689` (`ex-info-data-argument`: "fn value
requires unique arities with zero to four unique parameters"), the first module the facade requires.
