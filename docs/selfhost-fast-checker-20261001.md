# A fast `amu check` for development, and what it takes to build it with Amu (2026-10-01)

Premise (owner, 2026-10-01): the product depends on no nbb, no Node and no JVM
(`docs/selfhost-priority.md`, `docs/selfhost-bootstrap-boundary-20261001.md`). nbb, Node, the JVM and
GraalVM are **bootstrap references**. This page does two things:

1. records a **BOOTSTRAP-REFERENCE** fast checker (a GraalVM native image of the JVM-compiled sources) that
   exists only as the development feedback loop for `amu check`; and
2. writes down exactly what must exist before the fast checker can be a native binary **built by Amu
   itself**, so that the reference can be deleted.

Nothing here is a product artifact, and no number here is a selfhost claim. A file that prints `OK` from
`check-native.sh` is a lead for the Kotoba route, not a proof of it.

## 1. Use

    WALL_CP=/private/tmp/wall-cp-11.txt WALL_K=/private/tmp/wt-K-kotoba-lang \
      scripts/selfhost-wall/build-native.sh [probe.cljk ...]       # once; ~7-12 min, peak RSS ~4.5 GB, one at a time
    WALL_CP=... WALL_K=... WALL_AMU_SRC=<this repo>/src scripts/selfhost-wall/check-native.sh <file.cljk>

`check-native.sh` has the interface and output of `check-one.sh` (`<file>\tOK`, or the first refusal message).
It looks for the binary at `$AMU_NATIVE`, `build/native-image/amu-native`, then
`/private/tmp/amu-native-build/amu-native`. `CHECK_NATIVE_DEFINITIONS=1` also computes the per-definition CIDs
(ADR 0300), as nbb `check` always does; see section 3 for why the default skips them.

The binary is the JVM CLI `kotoba.compiler.cli` (the one `bin/amu check` runs on the JVM route), not
`nbb/wasm_cli.cljk`; the two share `kotoba.sema`, `project/link-source`, `effect-row` and the frontend, and
differ only in the host glue around them. The classpath is the wall classpath (`wall-cp-N.txt`), staged by
`scripts/build-native-image.py` (`.cljk` copied to `.cljc`, JVM-hostile spellings repaired, see section 5),
AOT-compiled by Clojure on GraalVM, traced once by the native-image agent for reflection, then compiled with
`native-image -O2`.

Rules it follows: it adds no dependency to anything on the product path; it is invoked only from
`scripts/selfhost-wall/`; it never runs in CI as a gate; the output of `build-native.sh` lives under
`build/` (ignored) or `/private/tmp`.

## 2. Measured (this Mac, under load average 40-130 from other agents, so read as upper bounds)

| check | nbb (`wall-one.sh`) | native (`check-native.sh`) |
|---|---|---|
| 1-line module (`(defn f [x :i64] :i64 x)`) | 2.3 s | 0.3 s |
| `kotoba/kir/xml.cljk` (OK, 3 modules linked) | 47.8 s | 1.15 s (13.3 s with `CHECK_NATIVE_DEFINITIONS=1`) |
| `nbb/wasm_cli.cljk` (refused at the first module that fails) | not measured | 7.4 s |
| `kotoba-sema/.../frontend.cljk` (refused) | not measured | 5.0 s |
| all 162 files of `reach-list4.txt`, 3 processes | est. 45 min (34 files took 9 min 54 s, 40 s of CPU each) | 2 min 19 s (2.0 s of CPU each) |

About 20x less CPU per file on average, and 40x on a module that passes. The gain is not mostly the
engine. Profiling the JVM build with JFR on `xml.cljk` (1307 samples): **89% of a check is
`check-definitions`** (`definition-identity/describe`: lowering, a canonical DAG-CBOR encoding of every
definition and, for every strongly connected component, the hex of every permutation via
`kir.definition-identity/bytes->hex`, which is `(apply str (map byte->hex (seq bs)))`); only 5% is the
frontend. The human line of `check` never prints definitions, and `check --json` prints them only because
ADR 0300 wants them there. Two follow-ups that are **not** done here and that speed up nbb as well (the host
code is shared):

- nbb `check!` (`nbb/wasm_cli.cljk`) computes `definition-identity/describe` unconditionally. A
  `--no-definitions` there (the JVM CLI now has it) would remove most of the 48 s with no change to any
  verdict. Left alone because the wall-cache work is editing that file.
- `compile-group` (`compiler/definition_identity.cljk`, the `:default` host reading) builds `:hex` for every
  candidate permutation, even when a component has exactly one. A lazy hex, and a `StringBuilder` loop in
  `bytes->hex` (`wt-D-osaho` `kir/definition_identity.cljk`), keep the CIDs and cut the cost for
  `compile`, `check --json` and `definition-cids`.

## 3. Equivalence against nbb

The gate was: run all 162 files of `reach-list4.txt`, compare with nbb, re-run every disagreement with nbb on
the current tree (the saved `wall-scan-21.tsv` predates edits to `kotoba-sema`, so 24 of its rows were stale).

Result, current trees: **92 OK** on native, 97 on nbb; 152 of 162 files give the same first refusal on both.
10 differ:

| files | nbb | native | root cause |
|---|---|---|---|
| `diagnostic`, `nbb/cli_support`, `nbb/project_source`, `nbb/test_cli`, `nbb/trust_cli` | OK | `invalid local binding` | `diagnostic.cljk:161` binds a local named `binding`. The frontend's forbidden-head set is a literal plus `load-catalog-forbidden`, which reads `guest-grammar.edn` `:forbidden-heads` (`binding`, `var`) on `:clj` and is `#{}` on `:cljs` (`frontend/namespace_defs.cljk:25-41`). The Kotoba reading, `frontend_tables.cljk` `forbidden-heads`, contains `binding` ("as the JVM frontend computes it"). Minimal case: `(let [binding (+ x 1)] binding)`. |
| `nbb/output_set_cli`, `nbb/package_authoring`, `nbb/package_lock` | a later wall (`support/parse-policy-material`; linked project function limit) | `invalid local binding` | the same cause, reached first because the JVM analyses the dependency `diagnostic.cljk` before the linked-project checks. |
| `object/macho64`, `packaging/pe32plus` | a later wall (line 123 / `\c`) | `host literal bigint is not admitted` at `macho64.cljk:64` | `18446744073709551616`: the JVM reader makes it a BigInt, the JS reader a double, so nbb walks past it. |

The five false OKs are the whole of the verdict disagreement: nbb OK 97, native OK 92. In every row the
native answer is the right one (the Kotoba tables agree with it, or the literal really is out of range), so
**the two engines never disagree on a refusal that nbb gets right; every difference is nbb being more
lenient than the JVM frontend**. The first row's real fix belongs in `kotoba-sema` (`:cljs` should return the
set `tables/forbidden-heads` returns); it is not done here because that checkout is another agent's working
tree and the fix changes the wall counts (five files stop printing OK).

Not covered by this gate: the `:definitions` CIDs (the default skips them). Parity of the CIDs between the JVM
and nbb routes is `scripts/test-definition-cid-parity.cljk`'s job; `CHECK_NATIVE_DEFINITIONS=1` is there to
run it against the native binary.

## 4. What must exist for the fast checker to be built by Amu

Target: `amu check` as a native binary produced by `amu compile` from the Kotoba reading of
`nbb/wasm_cli.cljk` and its closure, no JVM, no nbb, no Node at run time. The same wall classpath says what
is in the way. Status of the compiler path on the Kotoba route, from the 162-file native scan above
(confirmed by nbb for every row that matters):

**Gate 0, one construct, blocks 18 modules.** `kotoba-sema/src/kotoba/compiler/frontend/base.cljk:689`
(`ex-info-data-argument`, its `entries` closure) passes `(fn [[k v]] ...)` to `mapcat`. A destructuring
parameter of an `fn` value is refused ("fn value requires unique arities ..."). Every module that links the
frontend inherits it: `frontend`, `sema`, `core`, `project`, `project_files`, `effect_row`,
`effect_classification`, `interface`, `receipt`, `capability_names`, `ipld_adl_source`, `test_profile`, the
`nbb/*_cli` entries, `nbb/wasm_cli`. Spelling it with `key`/`val` (tried in a scratch copy, 4 s per
iteration with the fast checker) moves the wall to **Gate 1**: `base.cljk` `expand-intrinsic-helper-forms`
holds a `volatile!` cell (`used`) that is `deref`'d from a closure ("deref expects a let-bound atom cell").
Behind that is the rest of `frontend/*` (desugar 629 definitions, infer, analyze, ...), not yet measured
because it is masked; `docs/selfhost-frontend-decomposition-20260930.md` is the plan for that part. The fast
checker turns each of these into a 4 s experiment instead of a 50 s one, which is the actual use of it.

**Leaf libraries the checker links, failing today** (first refusal per module):

| module | first refusal | kind |
|---|---|---|
| `lang/coll` | variadic `deep-merge` used as a value | spell as a fixed-arity function |
| `lang/edn`, `json/core` | function body empty (host-only body under `#?(:clj ...)`) | add the `:kotoba` body |
| `lang/text` | `Math/abs` | `abs` builtin |
| `lang/json`, `json/data_json` | constant alias; variadic export | language/spelling |
| `kotoba/io/{reader,writer}`, `copy`, `reader_buffer`, `reader_seq`, `buffer_writer` | module exports nothing / referred record name not exported | export declarations (`.cljc` modules) |
| `io/{byte_buffer,len,put}`, `io/file` | atom slice 1 (`atom` as a non-let value, `swap!` on a parameter), variadic as value | rewrite state as let-rebinding or records |
| `kotoba_reader`, `io/to_bytes` | odd `let` binding vector | spelling |
| `wasm/core`, `wasm/tools` | two-argument `some`; `re-pattern` | spelling; regex has no Kotoba reading |
| `component/{artifact,core,wit}` | `re-pattern` (was `edn/read-string`) | same |
| `sha2/core`, `ed25519/core` | `count` of an i64; vector-i64 vs string | typing |
| `native/{aarch64,x86_64,machine_ir}` | `js/Number` | host numeric call under no `:cljs` guard |
| `object/{macho64,elf64,pe32plus}`, `packaging/pe32plus` | >i64 literal; `ex-info` key; `doseq` pair; `\c` | spelling |
| `nbb/host/{clock,env,entry}` | `js/Date.now`, unbound symbol, `js/setImmediate` | these are the host seam: the capability call replaces them (section 4.3) |
| `kir`, `verifier`, `script` | unexported import `value/operand-tag?`, `ir/oracle-inconclusive-trap`; quoted set mixing kinds | export/spelling |
| `nbb/run_cli`, `native_package`, `linux_static_handlers` | missing module / no defn | not on the check path |

**Order to remove them**, smallest closure first, each step verified by `check-native.sh` on the whole list
and by nbb on the files it moved:

1. Gate 0 and Gate 1 in `frontend/base.cljk` (unblocks 18 modules to show their next wall).
2. The leaf libraries the checker links: `coll`, `text`, `edn`, `json`, `bytes` readers/writers, `io/*`. These
   are small, independent and already have `.kotoba` twins in `lang/compat` for the rest.
3. The frontend proper (`desugar`, `infer`, `analyze`, `validate`), pass by pass as
   `selfhost-frontend-decomposition`. This is the multi-day part; nothing else gates the checker's
   *admission* verdict.
4. `project`, `project_files`, `effect_row`, `effect_classification`, `interface`, `receipt`, `core`,
   `capability_names` (the compile driver).
5. `definition-identity` + `kir.definition-identity` + `sha2` + `cbor` + `ed25519`, **last**: they only
   produce the CIDs. A checker that answers the admission question without them (`--no-definitions`) is
   already useful, and it is where 89% of the time goes. Do not put them on the critical path.
6. The entry: `nbb/wasm_cli` `check!` and its host glue (`nbb/io`, `nbb/host/*`, `cli_support`,
   `project_source`) as capability calls (`fs/app-data-bytes`, env, clock) behind `#?(:kotoba ...)`, then
   `amu compile` of that entry for the host target. The launcher (`bin/amu`, a Node script) is replaced by the
   resulting binary (stage S6 of `selfhost-core-rewrite-plan-20260930.md`).

**What the native-image reference cannot tell you** (so do not read it as a selfhost result): it runs the
host `:default` reading of every file; it proves the *frontend*'s verdict, not that the Kotoba reading of the
frontend (the thing selfhost needs) agrees. That is what `ds-diff.sh`, `tm-diff.sh` and `vx-diff.sh` measure.

## 5. JVM route defects found and repaired while building the reference (all `:clj`-only; nbb unaffected)

The JVM route had not been built from current sources since the Kotoba migration; these broke it silently
because the selfhost work is verified on nbb only. They are the cost of keeping a JVM reference alive and
are the argument for retiring it:

- `kotoba.lang.edn` (since `daf0e7a`, "character literals as one-character strings"): the JVM lexer compares
  `(.charAt s i)` (a `Character`) with strings, so no `;` `"` `#` is ever recognised and any EDN with a
  comment fails with "EDN token exceeds limit". Loading the capability catalog fails. Repaired in the stager
  (`scripts/build-native-image.py`): `.charAt` is wrapped in `str` for that file only. The right fix is in the
  `edn` repo.
- `{:kotoba/export #?(:kotoba [...] :default [...])}`: the stager only quoted a literal vector; it now quotes
  a reader-conditional value too, and only inside the `(ns ...)` form (a later `{:kotoba/export [..]}` in the
  frontend builds the fold-probe module at run time and must stay evaluated).
- `(catch js/Error ...)` in shared sources (`native/machine_ir`, from codemod `556605b`): the stager maps it
  to `Throwable`.
- `project_files/real-path` called `clojure.java.io/file` on a `java.nio.file.Path`: `amu check --source-path`
  threw on the JVM (fixed in `src/kotoba/compiler/project_files.cljk`).
- A native image has no reflection by default: the file readers and the project loader reflect. The agent
  trace is recorded by `build-native.sh` and `clojure.core.server__init` is removed from it (its class
  initialiser sets a root binding and aborts the build).
- The compiler recurses deeply: the shell stack must be raised (`ulimit -s 65500`, as `nbb --stack-size=4096`
  does). `check-native.sh` does it.

## 6. Retiring the reference

Delete `check-native.sh`, `build-native.sh`, `bin/build-native-image`, `scripts/build-native-image.py` and
this page's section 1 when `scripts/selfhost-wall/` can run `amu check` from an Amu-built binary and the
table in section 4 has no row left in steps 1-4. Step 5 may still be open at that point; nothing else needs
the JVM.
