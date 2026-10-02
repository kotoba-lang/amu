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
- **S6 bootstrap removal** (decision 2026-10-01: the product must not depend on nbb either): native
  launcher, compiled entry points, nbb demoted to an optional bootstrap reference. Section
  "S6" below.

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

## S3 slice 2b: `validate-value-type!` and the type-descriptor heads (2026-09-30)

`kotoba-sema/src/kotoba/compiler/value_type.cljk` ports `validate-value-type!` and its predicates over
`:form/r` (a value type is data, so it is a Form tree): the node/depth accounting (`max-type-nodes`,
`max-type-depth`; the host's volatile counter is threaded through `:vx/r`), the callable, slice, result,
option, list, stream, task, heterogeneous vector, set, map, record and variant arms with the host's messages
and codes. `closure-result-type?` (the callable arm's dependency) moved here as the `{}`-schemas call the arm
makes: `closure-default-value-expr` reduces to `default-kind` (none / false / truthy) because the host reads
the result and variant arms through `if-let` / `when-let`, where the `:bool` default (`false`) counts as none.
`validate_expr.cljk` requires it and now answers every descriptor-first head (`typed-list/set/map-*`,
`record-*`, `hetero-vector-*`, `option-*`, `variant-*`, `result-match-of`, the parametric result family,
`typed-cap-call`) in the host's order: shape, descriptor, descriptor kind, operands. Both modules pass
`amu check` on the project route. Only the rodata literals (`rodata-literal-content?`) still answer
`vx/unsupported`; none is in the corpus.

Differential (`vx-diff.sh`, `--descriptors` adds ~650 probes: every descriptor head with an operand dropped,
added, the descriptor replaced by a bad / wrong-kind / bad-inside one and the last operand unbound, plus 90
descriptor shapes through `typed-list-new` and `typed-cap-call`): 1543 cases (787 from the sema tests, 756
synthetic), 1543 agree, 0 disagree, 0 unsupported, 202 distinct refusal messages. `--only-file F` reruns just
the cases a previous results file left unsupported or in disagreement.

One deliberate non-match: a callable clause that is not a vector (`[:fn 1]`). The host computes the clause
arities before its shape check and dies with an internal "1 is not ISeqable"; the guest refuses with
`kotoba.error/callable-type`. That is a host defect on malformed input and is not probed.

## S6: bootstrap removal (2026-10-01)

Decision: the product must not depend on nbb, Node or the JVM. They are bootstrap references. The
end state is a native `amu` built by `amu` that runs `check`, `refactor`, `compile` and
`kotoba ...` with no node/nbb/JVM process. Today the product path is nbb-only in four places, all
counted by `scripts/selfhost-wall/bootstrap-boundary.sh` (snapshot
`docs/selfhost-bootstrap-boundary-20261001.md`): the launchers (`bin/amu` is a Node script that
spawns nbb, `bin/kotoba` is an nbb script), the `nbb/*_cli.cljk` entry points (11 files, 7 without a
`:kotoba` reading and 4 whose reading is nil or a named refusal), `refactor_cli.cljk` and the
refactor library, and the host-only requires under `src/` (13 files, 36 unguarded tokens).

What must exist first (S6 starts only when these are measured, not hoped):

1. S2-S4 done enough that the compiler core (frontend, KIR, verifier, mir, project linker) passes
   `amu check` on the project route with real, not refusing, bodies (`docs/selfhost-real-vs-hollow-20261001.md`
   shows REAL, not just OK).
2. A native runtime for the abilities the CLI shells use: `cli/args`, `io` (read/write/error),
   `fs` (tree, atomic write, app-data), `process/spawn` (only if a command still needs it),
   `env`, `clock`, `entropy/draw`, `hash/sha256`, exit codes. Each already has an `nbb/host/*`
   forward; the native side is the missing half.
3. S5 reached: an amu-built compiler compiles itself, byte-identical at stage N and N+1.

Steps (each ends with a bootstrap-boundary.sh count and a differential against the nbb route):

- **S6.1 Entry points as Kotoba.** Give every `nbb/*_cli` and `refactor_cli` a real `:kotoba`
  reading (`main` over `cli/args`), replacing the 7 no-arm entries and the 4 nil/refusal ones
  (`refactor`, `test`, `trust`, `evm`). `refactor_cli` first: it is how every later step is made.
- **S6.2 Host requires out of `src/`.** Move the 13 files with unguarded `node:*`/`js/*`/`java.*`
  tokens to per-module Kotoba readings or abilities; what stays host-only moves behind
  `#?(:cljs ...)` in a file flagged `;; bootstrap-tooling`.
- **S6.3 Native launcher.** A single native executable replaces `bin/amu` and `bin/kotoba`:
  argv parsing, classpath/lock resolution (`resolveWithLock`, `--source-path`, `--package-lock`),
  target selection, and in-process dispatch to the compiled entry points. No `spawnSync` of
  node, nbb, java or python. `bin/amu.cmd` and `bin/kotoba-compiler` become thin or disappear.
- **S6.4 Self-run.** The amu-built binary runs `check`, `refactor plan/apply/verify` and
  `compile` over its own `src/`, under `scripts/selfhost-wall/no-host-processes.sh`, with an
  identical outcome set to the nbb route (differential per file, like the wall harness).
- **S6.5 Demote nbb.** `bin/amu` no longer contains an nbb route. nbb stays only as an optional
  bootstrap reference (reproduce the first stage from a clean checkout, regression
  differentials) in clearly flagged BOOTSTRAP-TOOL files. `package.json`, `nbb.edn` and
  `node_modules` leave the install and release path.

Exit criteria (all of them): `bootstrap-boundary.sh` reports PRODUCT = 0 in sections 1, 2, 3b
and 4; `no-host-processes.sh -- <amu check/refactor/compile on amu's sources>` exits 0 with no
node/nbb/java/python exec; the binary hash is recorded and its numbers are selfhost numbers
(`docs/selfhost-priority.md` rule 4). Until then, nothing on this plan lets a new nbb, Node or JVM
dependency join the product path (rules 8-10).

## Memory strategy (2026-10-02)

The Form route's heap is the self-build's other wall: desugar keeps 616 B per source byte, which is 16-30 GB for the
whole pipeline in one process (`docs/selfhost-native-memory-20261002.md`). The owner's five ideas are measured, and
ordered, in `docs/selfhost-memory-plan-20261002.md`. The decisions it supports:

1. **Pair hash-consing in the loader** (`KEXE_HASHCONS`, spike landed, off by default), not an intern table in
   kotoba.form. Kotoba has no global state, and the loader does the sharing with no port changing. On the desugar
   guest it takes 616 -> 148 B and 30.6 -> 4.4 pairs per source byte, with byte-identical output. A self-build driver
   turns it on.
2. **One loader process per pass**, text at the boundaries (the study's option B). With step 1 the peak is one pass,
   about 0.5 GB and 14.5 M pairs, inside today's `KEXE_PAIR_MAX`.
3. **The seed backend via compile-kir** for the self-built compiler (seed design 5.2). This removes the ADR 0089
   KIR-as-Forms backend cost and takes machine_ir, mir, gmir and codegen (23% of the reach set's nodes) out of the
   self-build. The memory that remains is the frontend's Forms and pass state (`:fe/env`, `:ie/ctx`, the lexical and
   type maps).
4. `record-assoc` rebuilds only the prefix of the pair chain, and the hot env fields come first: a cheap
   kotoba-native change.
5. Definition CIDs serve incremental builds: a median 99.2% of definitions are unchanged per commit. They do not lower
   a cold self-build's peak. Flat Forms are deferred until a pass measured natively (infer, analyze) needs them.
   kotoba.form's `kids-of` is a typed list that ports index directly, so a flat Form touches every port.

Re-measure with `KEXE_ARENA_USE=1 KEXE_HASHCONS=1` as each S3 pass starts to run natively. Infer's per-byte cost is the
main unknown in the projection.
