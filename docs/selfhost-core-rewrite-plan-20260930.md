# Selfhost core rewrite: staged plan (2026-09-30)

Status at writing: 66 of 162 sources reachable from `nbb/*_cli.cljk` pass `amu check` on the
project route (`--source-path` every src root + `lang/compat`). Measured with the harness
described in `docs/selfhost-status-20260930.md`. Bootstrap numbers (GraalVM/JVM/nbb) are
reference only (`docs/selfhost-priority.md` rules 2 and 4).

## What the count does and does not say

The peripheral walls (host regexes, `js/*`, `set/*`, atoms, IO exports, `valid-seal?`,
`cbor/encode`) are a long tail of per-module Kotoba readings. Clearing all of them lifts the
count toward roughly 80-90 of 162 and produces no native compiler, because the walls that decide
selfhost are the compiler's own core:

| module | lines | what blocks it |
|---|---|---|
| `kotoba-sema/src/kotoba/compiler/frontend.cljk` | 20704 | walks source forms as host data; 219 uses of the reserved `__kotoba_` prefix as symbols; dynamic vars; `volatile!`; regexes |
| `osaho/src/kotoba/kir.cljk` (interpreter) | ~6000 | dynamically typed host values (`operand-tag?`, `shallow-typed-value!`, 76 call sites) |
| `kotoba-verifier/src/kotoba/verifier.cljk` | ~3300 | dynamic maps, `ir/execute`, `artifact/valid-seal?`, x86 emit |
| `kotoba-mir/src/kotoba/mir.cljk` | 3364 | host-map validation, register allocation |
| `compiler/definition_identity.cljk` | 749 | dynamic walks, `try`/`catch` control flow, CBOR |

Counting files that pass only because `lang/compat/kotoba/kir.kotoba` refuses `lower`,
`execute` and `eval-expr` by name would overstate progress: they check, they do not run.

## Representation decision

One dynamic value type carries compiler data on the Kotoba route: the recursive `Form` record
(`kotoba-hir/src/kotoba/form.cljk`, tags nil/bool/int/string/keyword/symbol/list/vector/set/map).
Gaps to close first, because every stage needs them:

1. metadata (source spans) - `Form` has no slot; add `[:span :i64]` (packed line/column/offset)
   or a side table keyed by node index.
2. f64 and bytes leaves - needed by KIR values; extend tags (10 f64-bits, 11 bytes).
3. symbols with the reserved prefix - the reader must produce them as data without tripping
   `reject-reserved-source-symbols!`; the rule stays for authored source, and compiler-synthesised
   names are minted through a `synthetic` function, not written as literals.
4. dynamic bindings (`*local-types*`, `*schemas*`, ...) become an explicit `env` record threaded
   through the passes (the affine port already did this for `*linear-returning*`).
5. `try`/`catch` around host failures becomes result-returning functions (`[:result T E]`), since
   a capability failure traps and cannot be caught.

## Stages (each ends with a measured count and a differential check against the host route)

- **S0 harness + fidelity.** Check the harness classpath into the repo (it was lost with
  `/private/tmp` once); add a differential runner: same input through the host route and the
  Kotoba route, compare canonical output.
- **S1 Form v2** (items 1-3 above) with tests; port `kotoba_reader` twin to emit spans.
- **S2 value and KIR data model:** typed `Value` record; port `kir.cljk` `lower` (validation and
  oracle sealing) before `execute`; then the interpreter as a Kotoba module. Removes the refusals in
  the `kotoba.kir` twin one by one.
- **S3 sema passes** in dependency order (desugar, type inference, abort passes, elaboration,
  rewrite-record-projection); each pass takes `(env, Form) -> Form` or a result.
- **S4 project linker, verifier, mir**, then the CLI shells (`nbb/*_cli`).
- **S5 bootstrap:** amu-built compiler compiles itself; compare bytes to the stage-N compiler;
  only then run Embench on it.

Every stage must keep the JVM/nbb behaviour identical (existing suites) and must not add a
JVM/GraalVM/Node fallback on the selfhost path.

## Landed in this pass (all local, unpushed)

Frontend: `fs/app-data-bytes` (wire 35 `:bytes`), two-argument write frame, default results for
`fs/app-data` in statement/`try` position, `(catch :default e ..)`, `:bytes` record fields,
`rem`/`mod`, `str` over i64 literals/params/let and loop locals, `record-get` inference in the
abort passes, capability calls in a `def` refused by name. Ports: `nbb/io`, `schema`, `affine`,
reader twin, `kir` twin (partial), `cli_support`, `kir/value` (subset), artifact `core` and
`runtime_identity`.

## Finding: the frontend's quoted data tables (2026-09-30, after the reserved-prefix fixes)

With the reserved-prefix wall cleared (kotoba-sema 3b9126d, 18afab9), `frontend.cljk` next stops at
`quoted symbol-key map values are not one scalar kind`. It is not one site: the frontend quotes host
data pervasively - symbol -> integer / vector / set tables (`kernel-memory-operations`,
`kernel-base-positions`, `contextual-*-argument-indexes`, `document-fixed-operations`, ...), quoted
code lists (`closure-default-value-expr`, `lambda-dispatchers`) and 3-4 dozen more. `quote` admits
only a symbol, a symbol set, a scalar-valued symbol-key map or a symbol vector by design.

A general `(quote datum)` -> `kotoba.form` literal (print the datum as EDN, call `form/edn-form`)
is feasible, and the frontend half is small (a dynamic `*quote-form-stub*` bound from analyze opts,
an EDN printer, two call sites in `desugar-quoted-datum`); the linker would pass the import stub of
`edn-form` when the module requires `kotoba.form`. It was prototyped and reverted: the probe did not
reach `analyze-module` (the check path of a single entry file with a `:require` takes a route I did not
trace), and the tables are mostly top-level `def`s, which are folded at analysis time and would have to
become zero-arity functions with their uses rewritten. That is S3 work, not a wall fix.

## S3 slice 2: `validate-expr` on the Form record (2026-09-30)

`validate-expr` (frontend.cljk, admission of one desugared expression) was the smallest pass that
could move independently: its inputs are the form, the locals in scope and the module's function
arities, and its only ambient state is the `budget` volatile. No dynamic var is involved, so the
port needs no env of dynamic bindings, only the explicit `:vx/env` record plus a `nodes` counter
threaded through `:vx/r` results (Kotoba cannot catch, and the host's `reject!` throws, so a
refusal is a value: code + message).

Module: `kotoba-sema/src/kotoba/compiler/validate_expr.cljk` (passes `amu check` on the project
route; entry `run-batch`). Operation tables come from `kotoba.compiler.frontend-tables` Forms,
folded once per batch into a 64-bucket name index (first table wins, as the host's `cond`).
`forbidden-heads` / `grammar-declared-heads` are resource-derived host values and are passed in.

Differential: `scripts/selfhost-wall/vx-diff.sh` (needs `WALL_CP`, `WALL_K`, `KTEST`, see the
script header). Corpus: every string literal in `kotoba-sema/test/**` is analysed with
`validate-expr` wrapped; each outermost call (desugared form, real locals, real arities) is a
case. Plus a hand-written refusal-probe set. Host = `frontend/validate-expr`; guest = the module
linked as a project and run on the KIR interpreter. Compared: `OK <nodes charged>` or
`<error code> <message>`.

Measured (nbb, this tree): 892 cases (781 from the sema tests, 111 synthetic probes), 760 agree,
0 disagree, 132 out of the slice (guest answers `vx/unsupported`, counted apart). In-slice
agreement 760/760, covering 108 distinct refusal messages. Not in the corpus: 7 cases with an
integer outside +-2^53 and 6 with non-ASCII text (the EDN hand-off), and a keyword over 512 bytes
(the Form reader's `keyword-from-string` traps before the pass can see it).

Out of the slice: heads whose first operand is a type descriptor (`option-*`, `result-*`,
`record-*`, `typed-list/set/map-*`, `hetero-vector-*`, `variant-*`, `typed-cap-call`) call
`validate-value-type!`. Its callable arm asks `closure-result-type?`, an inference-layer
predicate, so the descriptor pass is the next unit to move (with `closure-result-type?`), not part
of this one. `rodata-literal-content?` is the other missing helper. `grammar-declared-heads` is
empty under nbb, so the declared-but-unlowered refusal is written but not exercised.
