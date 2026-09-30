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
