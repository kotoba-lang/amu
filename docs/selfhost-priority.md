# Selfhost is the top priority for the Amu compiler

Decision updated by the owner on 2026-10-22. It outranks new features, new
targets and benchmark publication. This contract supersedes the earlier
CLJK syntax-sugar retention, hosted bootstrap exceptions and C-loader pinning
requirements. Historical checkpoints below record earlier work, not current
instructions or proof of completed migration.

## The goal

**Canonical source is `.kotoba`. Amu builds and rebuilds its own native
compiler, CLI, project/build graph, packager and operational tooling without
CLJK/CLJC/CLJS, NBB, KBB, Clojure, Java/JVM, GraalVM, Node.js, or a C
compiler, loader or runtime.** CLJK is a migration input, not a final authoring
surface or acceptance requirement. Port required behavior into Kotoba and
retire the old source, launchers and dependency declarations.

Emitting machine code or naming a file `.kotoba` does not prove this closure.
Record the compiler generations, pinned sources/locks, artifact hashes,
packaging and actual process execution. A selfhost-produced loaderless native
artifact is the product route; CDCI uses only `x86_64-linux-static` ELF for
Amu selfhost and Kotoba native. Browser/Worker Wasm and JavaScript are generated
targets executed in the declared user host, not permission to keep a Node/NBB
compiler host. Shared client-runtime and per-operation consent rules still
apply to end-user apps.

## Rules

1. **Selfhost first.** When work competes for time, the item that moves the
   compiler toward building itself wins. Walls on the selfhost scoreboard are
   fixed in the language / frontend / backend or ported into canonical Kotoba
   without narrowing supported behavior to make the scoreboard green.
2. **Only a selfhost-built compiler is selfhost evidence.** A compiler
   executable counts only if Amu selfhost produced it through the qualified
   native build closure. Hosted builds, GraalVM Native Image and C-loader
   receipts describe historical provenance only. Do not publish them as
   current selfhost, Q9 or CDCI qualification.
3. **Remove legacy build and execution dependencies.** Replace hosted compiler
   seams, C loaders, seed/image launchers and packagers with Kotoba / Amu
   selfhost implementations. Do not pin a C loader as the solution, retain
   CLJK as syntax sugar, or keep GraalVM builders for a required comparison
   route. Missing native functionality is an explicit blocker.
4. **Benchmarks follow selfhost.** Embench and other compiler measurements are
   published as selfhost results only when taken with a selfhost-built
   compiler, on a quiet host, with the compiler binary hash recorded. Results
   from a bootstrap compiler are published as bootstrap-reference numbers,
   never as selfhost numbers.
5. **Fail closed.** No legacy host, C loader, wrapper or hosted packaging
   fallback is added to make a selfhost stage pass. `--jvm-free` alone is
   insufficient: it does not exclude Node/NBB/C. An unreachable component
   stays on the scoreboard as refused or blocked, with its reason.

## Migration gates

The final graph contains canonical `.kotoba` implementations. Existing CLJK
fixtures, readers and host-specific branches are migration inventory; they
do not establish a requirement to retain the old surface. Preserve recorded
behavior, semantic identity, authority and resource boundaries while porting
the whole component. Source admission is distinct from execution and full
self-reconstruction.

The migration proceeds through these gates:

1. **Port the language and component boundary.** Migrate required source and
   fixtures to `.kotoba`, preserving recorded semantics, Definition CIDs and
   named refusals. Remove the requirement for a permanent paired CLJK surface.
2. **Grow the native Kotoba compiler closure.** The adopted seed is a 16-module
   compiler and has separate source-only x86_64 Linux support; neither covers
   the complete Amu frontend, project system, verifier, and command surface.
   Extend it from Kotoba source and require each generation to compile and
   verify the next without the forbidden hosts or C loader/runtime. A
   historical subset fixed point does not qualify the full compiler.
3. **Move the CLI and build graph.** Once the native compiler covers the
   complete public command surface, build and run it from pinned native
   artifacts. Include seed/image bootstrap, input resolution, orchestration,
   packaging and launchers in the native dependency closure. Historical host
   tooling must not remain a required step.
4. **Qualify and retire the old routes.** The native path must pass the same
   positive, refusal, project-link, artifact-verification, and command-level
   conformance corpus, then replace the legacy source, runtime and dependency
   declarations. Remove unused old routes directly. Record source changes,
   runtime qualification and any live cutover separately; this document does
   not authorize stopping existing services or a production cutover.

Tracking: JUN-200 (loaderless bootstrap), JUN-202 (native selfbuild inputs and
fixed point), JUN-199 (product entry), KOT-13 (Kotoba core), JUN-198 (Kotoba
CLI/build) and JUN-162 (the two-gate native CDCI controller).

## Historical checkpoints (superseded contract; evidence only)

Statements below about retained CLJK syntax sugar, hosted routes and pinned
C loaders describe the contract at the time. They grant no current exception
to the 2026-10-22 goal or migration gates above. No dependency removal or
runtime qualification is implied by this policy update.

## Migration checkpoint: 2026-10-16

Canonical Kotoba implementations for `decimal_text`, `text_bytes`,
`target_names`, `posix_path`, and `source_path` now live in `*_core.kotoba`
modules. Their public `.kotoba` facades and Kotoba-reader `.cljk` branches
delegate to those cores; host compatibility adapters remain in the `.cljk`
sources. `amu definition-cids --jvm-free` compared the exported definitions
after factoring, using isolated source roots. All 22 exported public
definitions match pairwise:

| Module | Matching exports |
| --- | ---: |
| `target_names` | 1 / 1 |
| `decimal_text` | 3 / 3 |
| `text_bytes` | 10 / 10 |
| `posix_path` | 4 / 4 |
| `source_path` | 4 / 4 |

This uses the Node/nbb bootstrap with `--jvm-free`; CID identity establishes
the same normalized definition, not runtime execution. Private/generated
entries previously differed in `decimal_text` and `text_bytes`. The `.cljk`
host branches still contain helpers such as
`host-i64` and `utf8-text-lossy`, so those compatibility runtimes remain in the
bootstrap source. A closed project fixture importing `posix_path` linked to
an AArch64 macOS artifact through `--jvm-free`; that run used the Node/nbb
bootstrap compiler, so it proves module selection and native linking, not Amu
self-reconstruction.

The adopted native Seed compiler also resolved and compiled a separate
`source_path` project for each spelling. The `.cljk` graph selected
`source_path.cljk` and the `.kotoba` graph selected `source_path.kotoba`; both
included `source_path_core.kotoba` and the `kotoba.lang.text` compatibility
closure. With `--unpinned` for these isolated scratch sources, the Seed emitted
a 151,479-byte AArch64 macOS KSEED for `.cljk` (SHA-256
`fd578d7c79a0f3f3beb11b08837968926f7bff41a831845a0ec4a94321f8bb2f`) and a
147,863-byte KSEED for `.kotoba` (SHA-256
`e417d7f20f99ed31b89dcdffa6ccc9afcd4dc6e1545bb63517c9c88c64e2e770`). Neither
artifact was executed.

The five local `.kotoba` modules `target_names`, `decimal_text`, `text_bytes`,
`posix_path`, and `source_path_core` now each pass `amu check --jvm-free`
through the Node/nbb bootstrap; `source_path_core` uses explicit Kotoba
language compatibility sources. This is source admission/type-check evidence,
not an Amu-built compiler result. Artifact PR [#68](https://github.com/kotoba-lang/artifact/pull/68)
adds the `core.kotoba` counterpart: its five exported Definition CIDs match
`core.cljk`, and bootstrap `amu check` passes with an explicit
`[:cap/call :hash/sha256]` policy. It remains unmerged and is not yet pinned
by Amu.

The optional x86_64 Linux source-only seed still excludes the project linker
and full command driver. Its explicit driver refuses project/source-path routes
instead of falling back. The broader seed closure contains a separate project
linker and cross-compiler, but its presence is not yet qualification of the
source-only selfhost route. The main `bin/amu` launcher and its scripts still
depend on Node/nbb; no host runtime has been retired.

`source_path_core.kotoba` owns suffix classification, source admission, and
native artifact shape admission. Its public `.kotoba` facade and `.cljk`
Kotoba-reader branch expose the same four typed functions. `admit!` and
`admit-native-artifact!` return typed `Result` values with `:message`/`:data`
error documents. Exception-oriented adapters remain available to JVM/nbb
callers in the `.cljk` host branch; the Kotoba reader branch keeps only
non-aborting, private Result adapters and does not export them. The four public
Definition CIDs match, and both representations compile through the adopted
native Seed. This does not migrate callers such as `cli.cljk`,
`trust_cli.cljk`, `test_cli.cljk`, and `manifest_mode.cljk`, which still use
host-oriented convenience APIs or depend on other unported modules. The
project-wide CLI graph remains incomplete.

The shared source-kind vocabulary now labels `.cljk` as
`:kotoba-syntax-sugar` and `.cljc` as `:kotoba-compat-syntax` in both the
Kotoba core module and its host adapter. The core check passes with the
language compatibility root explicitly supplied. The suffix remains
discovery metadata and does not select a runtime.

`cli.cljk` now puts `:gen-class` behind the `:clj` reader feature, keeping this
bootstrap launcher clause out of Kotoba input. With explicit roots for Amu
`src`, Kotoba language compatibility sources, `kotoba.bytes`, Kotoba-sema, and
the artifact owner, the `manifest_mode.cljk` project check now gets past
`kotoba.artifact.core`. The `kotoba-hir` checkout now has an uncommitted
`src/kotoba/hir.kotoba` counterpart beside its `.cljk` source. A direct
`amu check` of that candidate with the explicit compatibility root refuses at
the exported `validate!` boundary (`unhandled abort`); the throwing host API
still needs a typed Kotoba error result. This used the Node/nbb bootstrap and
does not establish CLI parity or selfhost evidence. No JVM or Node/nbb
dependency has been retired.

The adopted native seed image recorded as `selfhostCompiler: true` in
`seed/adoption-20261012.json` matches its recorded SHA-256 and checked the
`target_names.kotoba` module through the project linker as a library; the
keyword-valued export is supported at that boundary. The `.cljk` form
`(-> 40 (+ 2))` and the direct `.kotoba` form `(+ 40 2)` compiled through this
same native compiler to identical 34-byte AArch64 artifacts
(`d9d93e2896184a1eff34a88f79cdfd9d51d96afd2af1f6d1b2020010ebc920bc`). This
confirms one admitted sugar lowers to the same core behavior in the seed. It
does not establish equivalence for all `.cljk` forms or that Amu's complete
compiler builds itself.

The current `target_names`, `decimal_text`, `text_bytes`, and `posix_path`
sources make that relationship explicit: each `.kotoba` public module and
each `.cljk` Kotoba reader branch delegates to a shared `*_core.kotoba`
implementation; the `.cljk` host branches remain for bootstrap compatibility.
The adopted native Seed compiler checked and compiled an isolated project
containing all four `.cljk` adapters and their Kotoba core modules into a
55,125-byte AArch64 macOS KSEED artifact (SHA-256
`2a87974e3102f7984f0eaba8d1815051d4b8ec5ddda08049d058ace7528c9557`). Its
`modules` readback selected every `.cljk` adapter and its matching core
module. A second isolated project using all four public `.kotoba` facades
compiled to a 25,015-byte AArch64 macOS KSEED artifact (SHA-256
`7114fe3ce1ac32db6e311ee50254c465faabfdcf4f50048f7732732d8d0fbd75`); its
readback selected each facade and core module. Neither artifact was executed.
These checks do not qualify the full Amu compiler or retire its JVM/CLJS
bootstrap dependencies.

The linker uses `kotoba.sema/read-forms`, whose host and Kotoba implementations
both route through the Kotoba reader; reader conditionals select `:kotoba` and
`:default`, so `.cljk` is parsed as Kotoba surface syntax rather than evaluated
with Clojure or ClojureScript reader semantics. Extending the explicit source
roots with `osaho/src` and the pinned `org-ietf-cbor/kotoba` tree advanced the
`manifest_mode.cljk` link past `kotoba.kir`, `kotoba.form`, and `cbor.core` to
the next missing module, `multiformats.core`. The pinned `io-multiformats`
revision provides `src/multiformats/core.cljk` but no
`kotoba/multiformats/core.kotoba` counterpart. A follow-up whole-closure check
including that host source ran for two minutes without output and was
interrupted; it established no compile result. This dependency still needs a
Kotoba core implementation or a smaller source closure before the command
graph can advance. These checks use the Node/nbb bootstrap despite
`--jvm-free` and do not establish Amu self-reconstruction.

Follow-up on 2026-10-16: an isolated `io-multiformats` worktree now has a
bounded Kotoba slice in `src/multiformats/cid_core.kotoba` and the public
`src/multiformats/core.kotoba` facade. The facade exposes only
`cidv1-dag-cbor`; the pure Kotoba core implements SHA-256, base32, and CIDv1
without JVM or JavaScript crypto APIs. `core.cljk` keeps the wider Clojure and
ClojureScript implementation in its `:default` reader branch and exposes a
small Kotoba syntax-sugar wrapper that delegates to the same core function.
The Kotoba reader check selected `cid_core.kotoba` and `core.cljk`, and the
exported `cidv1-dag-cbor` Definition CID matches the `.kotoba` facade
(`bafyreihjuze6ryrzappoojw2dmjauqgrycbj75nopw3xuc2mpveg5bebtq`). This check
used the Node/nbb bootstrap with `--jvm-free`; it did not run the output or
rebuild this final reader-conditional version with the adopted native Seed.
The candidate is uncommitted and the Amu lock still selects the older
`io-multiformats` revision, so it is not yet part of the pinned graph. The
last explicit-source closure check that included this candidate advanced to
the next missing module, `kotoba.form`. A focused Kotoba implementation now
exists in an isolated worktree. The project linker now carries dependency
schemas into importer analysis and can synthesize closed record/variant values
for temporary import stubs. A `--jvm-free` check of `kotoba.compiler.value-type`
with `kotoba.form` in the explicit source path linked both modules and passed
before the final schema-collision guard was added. After the guard, a
`--jvm-free` check of `kotoba.compiler.form-transform` also returned `:ok true`
with module order `kotoba.form` -> `kotoba.compiler.form-transform`. This used
the Node/nbb bootstrap; the Amu lock has not been advanced to the candidate.
Extending the `manifest_mode.cljk` closure through `multiformats.core` and
`org-nist-sha2` advanced the next missing source to
`kotoba.verifier.signing`; retrying with that owner source also ran for two
minutes without output and was interrupted.
No JVM, Clojure, ClojureScript, or Node dependency has been removed.

Follow-up native check (2026-10-16): `build-adopted.py --verify-only` passed,
and the pinned native Seed image matched the receipt SHA-256
`510599927df88117d22809f751593c6f38e8afbc4bb8881e0ce989549aae2e94`.
Through the C loader built from the pinned loader source, its `modules` command
resolved the candidate `form_pipeline.kotoba` closure in dependency order:
`kotoba.form`, `kotoba.compiler.form-transform`,
`kotoba.compiler.decimal-bits`, `kotoba.compiler.kotoba-reader`, and
`kotoba.compiler.form-pipeline`. The native Seed `check` command returned
`ok` for that closure when invoked with the three explicit source roots and
`--unpinned`, because these candidate files are not yet in the lock. This is
native compiler admission/type-check evidence for the candidate `.kotoba`
graph. It does not execute the generated code, establish lock-pinned
reproducibility, or retire the Node/nbb bootstrap. `.cljk` remains Kotoba
syntax sugar; this check exercised the `.kotoba` spelling of the form graph.

The native filesystem seam is moving the same way: a `.kotoba` sibling for
`kotoba.compiler.nbb.host.fs` now exposes `:fs/app-data` and `:fs/browse` via
typed capability calls, with no JVM or Node imports. A native Seed `modules`
readback of a Kotoba importer selected that `.kotoba` file, and `check` passed
for the linked importer with the Amu source root explicitly supplied and
`--unpinned`. This proves the capability adapter can join a native project
closure; the existing `.cljk` Node handler and `bin/amu` bootstrap still
remain, so this change alone removes no host dependency.

The native form pipeline now also has `syntax_sugar.kotoba`. `.cljk` is treated
as Kotoba surface syntax: this bounded lowerer maps `->`, `->>` and `as->` into
Kotoba core forms, leaves quoted forms unchanged, and keeps direct `.kotoba`
input on the reader-only path. It does not request Clojure or ClojureScript
evaluation; this is an admitted subset, not yet a frontend for every existing
`.cljk` file. On the adopted native Seed, `modules` resolved six modules through
`form_pipeline.kotoba`, `check --unpinned` returned `ok`, and
`compile --target aarch64-macos --unpinned` emitted a 175,779-byte KSEED
(SHA-256 `1142a70b776e4759d19e7fdbac6faf8dca54edfcbf3f7f3630b8e90f38f2c237`).
This is code-generation evidence for the unpinned candidate frontend; the
artifact was not executed, the candidate is not in Amu's lock, and no host
dependency has yet been removed.

The same lowering is now connected to the native expression/type frontend in
`native_frontend.kotoba`. Its adopted-Seed closure resolved eight modules
through `validate-expr` and `native-frontend`; `check --unpinned` returned
`ok`, and native compilation emitted a 318,246-byte KSEED (SHA-256
`e4327fc6b31c5f34fd7c2d6347190b202fbe0446121c39e9cd504f1f5745b788`). This
verifies native admission and code generation through the validator boundary;
the artifact was not executed and the candidate closure remains unpinned.

Follow-up on 2026-10-16 made that candidate boundary source-specific:
`native_frontend.kotoba` now exports `validate-cljk-expression-source` and
`validate-kotoba-expression-source`. Both use the Kotoba reader; the `.cljk`
entry lowers its admitted `->`, `->>` and `as->` syntax sugar before checking,
while `.kotoba` passes its canonical core form directly to the checker. On the
adopted native Seed, the eight-module closure resolved, `check --unpinned`
returned `ok`, and compilation emitted a 318,590-byte AArch64 macOS KSEED
(SHA-256
`0aceb1e6c3a91e88c793cc80a320cc75c1a675fb244520602a413a99f59f4ef4`). This
is still a bounded isolated frontend candidate: its artifact was not executed,
it is not in the source lock or complete Amu project CLI, it does not yet cover
all existing `.cljk` syntax sugar, and no JVM/CLJS/Node dependency has been
removed.

That same eight-module closure also built through Seed's separate-object mode:
each module compiled as a `.kso` in dependency order, then `seed link` produced
a 318,246-byte KSEED byte-for-byte identical to the in-process compile above
(the same SHA-256). This confirms parity between the two native project build
modes. It does not pin the source inputs. The adopted Seed driver dispatches
`modules`, `compile`, `check`, `extract-native`, and `link`, but has no
`module-lock` command; invoking it returns E1 usage. The CID-based source lock
is therefore still a native CLI/build-graph gap.

The same native path now admits the Kotoba branch of `affine.cljk`. Seed
rejected its exported multi-arity predicates with E2138, so the assumptions
variants are now private helpers behind single-arity Kotoba exports; the
default host branch keeps its existing API. The Kotoba thread-sugar scan also
leaves quoted data untouched. Native `modules` resolved
`kotoba.lang.coll` from the compatibility `.kotoba` source and the candidate
`affine.cljk`; `check --unpinned` returned `ok`, and
`compile --target aarch64-macos --unpinned` emitted a 133,175-byte KSEED
(SHA-256 `5054cd73a4d8d9354129009a0f431a1999dacf0715ece29e183135dc533a4cc3`).
This evidence is still unpinned and the artifact was not executed. The host
branch and Node/JVM launch paths remain, so these changes remove no runtime
dependency yet.

Current HIR Form follow-up (2026-10-16): the uncommitted
`kotoba-sema/src/kotoba/form.cljk` uses the newer `:data :bytes` Form ABI.
Its first native compile stopped with E2101 at `document-f64-value`, which the
pinned Seed explicitly does not admit. The Kotoba branch now reads the
canonical EDN spelling with `document-edn-print`, maps the expected `##NaN`,
`##Inf` and `##-Inf` spellings to IEEE-754 bit patterns, and parses finite
values with `decimal-f64-parse`. After regenerating an isolated `.kotoba`
source from the current HIR file, the adopted Seed compiled a small importing
Kotoba module to a 117,615-byte AArch64 macOS KSEED (SHA-256
`9e4b9a3750052cca113f7f5ee707e333dcdd15b8362b6193ed2b0061e8e13731`). This
advances the current bytes-based Form module through native parsing, checking,
and linking with an importer. A second compile used `kotoba-sema`'s actual
`form.cljk` as the first source root, with no `.kotoba` counterpart in that
root; Seed selected its `:kotoba` reader branch and compiled the importer to a
117,655-byte KSEED (SHA-256
`9762e8cee2c210c1dbbb79b99e3f9fa9770fc112a5da4f030fdc7f744aa2e6a5`). This is
direct native evidence that this `.cljk` module is read as Kotoba syntax
sugar. Both artifacts are unpinned and unexecuted, so runtime equivalence for
f64 values is not established. The earlier candidate `form.kotoba` uses a
different `:data :vector-i64` ABI and cannot stand in for this HIR module. No
JVM/CLJS/Node dependency has been removed.

The same current Form ABI now includes `with-children`, which rebuilds a form
with transformed children while preserving its tag, scalar payload, span, and
bytes. The Amu source tree now contains the native Kotoba reader, bounded
syntax-sugar lowerer, structural form transform, value-type/expression
validator, and native frontend boundary under `src/kotoba/compiler/`. Their
schemas use `:data :bytes`; the reader creates empty bytes payloads for leaves
in the admitted grammar. Seed resolved a seven-module closure using the actual
`kotoba-sema` `form.cljk` as its first source root and compiled the Amu
`native_frontend.kotoba` entry to a 339,294-byte AArch64 macOS KSEED (SHA-256
`16466b381f9507f4fe328ffce811af81ca0289d77c5d221a04d8a3837a31511d`). This
extends native compilation through expression validation with current Form
records and direct `.cljk` selection. The HIR Form is still uncommitted, the
source roots were explicit and unpinned, the artifact was not executed, and
the candidate frontend is not connected to Amu's public CLI or source lock.
This remains short of full compiler self-reconstruction; no host runtime has
been removed.

## Full semantic analyzer through the Native Seed: 2026-10-17

`src/kotoba/compiler/native_frontend.kotoba` now exposes the full
`kotoba.sema` analyzer and linter for both canonical `.kotoba` and `.cljk`
surface source. The result remains a typed `:ana/ir` HIR/error record across
the module boundary; the source extension does not select a Clojure or
ClojureScript runtime.

The adopted Seed's current dependency order contains 30 modules for this
frontend. Every module compiled as a separate KSEEDO1 object; the largest
object was `kotoba.compiler.frontend.desugar` at 1,654,374 bytes. Linking the
objects produced a 3,691,441-byte AArch64 macOS KSEED. Its SHA-256 is
`a47d0ccc37a53c592967c2945b6c9e7fef8f50fb36a38e417f88b1c553ddcff8`.
Separate-object generation advances beyond the 3 MiB single-output limit
that stopped the earlier monolithic compile.

A scratch-only caller imported this frontend, analyzed a `.cljk` module
containing `(-> 40 (+ 2))` and its canonical `.kotoba` spelling `(+ 40 2)`,
then compared both `:ok` fields and their HIR with `form/eq`. The linked image
was executed by the local AArch64 code loader with no capability grants; it
returned `0`, meaning both analyses succeeded and their normalized HIR was
structurally equal. This covers one admitted syntax form, not the complete
`.cljk` surface. The smoke KSEED was 3,694,945 bytes with SHA-256
`7d59ab434ce1923d09bef344930dfb9bfb05f77b8023cf5d71c69fafb0d0d072`.

This uses the adopted Seed bootstrap, explicit source roots, and unpinned
inputs. It proves native Seed admission, per-module code generation, linking,
and one executed analyzer path for thread syntax. It does not prove that Amu
built this compiler, that all `.cljk` sugar has equivalent `.kotoba` core
semantics, that the source graph is lock-pinned, or that Amu's public CLI is
selfhosted. JVM/CLJS/Node launch and build dependencies remain.

## Native single-file check CLI follow-up: 2026-10-17

`src/kotoba/compiler/native_cli.kotoba` adds a Native Seed `check <file>`
entry for `.cljk` and `.kotoba`. It gets arguments through `:cli/args`, reads
the file through `:fs/app-data`, calls the full analyzer, and writes results
through `:io/write` / `:io/write-error`. There are no Node, ClojureScript, or
JVM imports in this Kotoba source.

The 31-module closure passed Native Seed `check`, separate-object compilation,
and linking into a 3,693,129-byte AArch64 macOS KSEED (SHA-256
`5e8e61d6c3a62f4469375c02a3f9198a58da299950be1f0ce2262a7c71c44a26`). The
linked entry was run through the C loader with file read scoped to scratch:
valid `.cljk` and `.kotoba` inputs printed `ok` and exited 0; a type mismatch
printed the Kotoba diagnostic and exited 65; bad usage printed help and
exited 64.

This is a native single-file command slice built by the adopted Seed from
explicit, unpinned roots. It is not wired into `bin/amu`, does not link project
dependencies or read a module lock, and does not establish Amu self-rebuild.
The public CLI and its JVM/CLJS/Node bootstrap paths remain.

The next project-link slice could not import the existing shared
`kotoba.compiler.project` module directly into this Native Seed graph because
its source used Clojure regex reader literals. The working tree now replaces
those patterns with bounded string scans for synthetic aliases, dispatcher
names, loop helper names, and linked module IDs. This removes the known reader
syntax obstacle. Native Seed checks now pass through the project module's
limit and capability lookups, but `check --unpinned project.cljk` stops at
E6004 because `sema/namespace-attr-map->clauses` is not an admitted exported
import (byte 29693). Its Kotoba implementation returns
`[:list [:ref :form/r]]`; exporting a cross-module wrapper currently fails
with E2104 at that boundary. The full shared project module is still outside
the admitted Kotoba export surface. It also accumulates graph state with
`volatile!` / `vswap!`; those host-state operations need a Kotoba-native
implementation, not a runtime fallback. A Kotoba-native metadata reader and
source-graph resolver now exist. Later Native CLI work added source graph
discovery and semantic interface linking, but it does not yet replace the
shared project module or provide executable multi-module linking.

## Native project metadata stage: 2026-10-17

`src/kotoba/compiler/native_project.kotoba` reads source through the Form-based
Kotoba reader and returns a typed namespace, direct `:require` names, and a
diagnostic string. `native_cli.kotoba` calls it before the full semantic
analyzer. This path treats `.cljk` as Kotoba syntax sugar: the file extension
does not select Clojure or ClojureScript parsing or execution.

The Native Seed `--unpinned check` passed for the 32-module CLI closure after
this integration. A scratch-only runtime probe compiled to a 192,383-byte
AArch64 macOS KSEED, was extracted and executed by the C loader, and returned
0 after checking `app.main` and its `app.util` requirement.

The graph stage validates an explicit collection of namespace/source pairs,
checks the aggregate source-size and dependency-edge limits, discovers the
transitive `:require` closure, rejects missing modules and cycles, and returns
modules in dependency order. A public `resolve-graph-packet` wrapper uses
length-framed UTF-8 byte strings (`name-length\nsource-length\nname-source`)
because Seed does not admit typed-list function arguments across module
boundaries. The frame at this stage was `name-length\nsource-length\nname-source`;
the source-path integration below prepends a `.cljk` surface flag, making the
current frame `surface-flag\nname-length\nsource-length\nname-source`. A
separate-module Native Seed smoke imported that wrapper and
passed dependency ordering, missing-dependency, cycle, duplicate-namespace,
malformed and oversized length, and multibyte UTF-8 frame cases. Its 207,767-byte
AArch64 macOS KSEED ran through the C loader at the extracted `main` offset
197,000 and returned 0. The scratch-only inputs were explicit and unpinned.

The full semantic `native_cli` still does not gather project files into that
packet. Source-path discovery now exists in a standalone graph command, but is
not connected to semantic import rewriting or multi-module lowering. Export
and schema validation remain open. No JVM, CLJS, Node, or Nbb dependency has
been removed from the public `bin/amu` route.

## Native source-path graph CLI: 2026-10-17

`native_project_files.kotoba` now walks a project from an absolute entry path
and up to 16 absolute `--source-path` roots. It checks existence before file
reads, maps namespace dots to directories and hyphens to underscores, then
tries `.kotoba`, `.cljk`, and `.cljc` in that order within each root. Across
roots it accepts one candidate, or selects a unique `.kotoba` candidate;
other collisions are reported as ambiguous. It enforces the 256-module,
256-edge, and 8 MiB aggregate source limits, frames the sources, and delegates
missing-module and cycle checks to `resolve-graph-packet`.

The path resolver is exposed by `native_project_cli.kotoba`, a small,
standalone Native Seed command. Its Native Seed check passed; the adopted Seed
compiled a 221,175-byte AArch64 macOS KSEED. The extracted entry ran through
the C loader against scratch-only projects: a `.cljk` entry plus `.kotoba`
dependency and a UTF-8 Japanese source-path root each reported
`project graph ok: 2 modules`; a missing dependency and a cycle each returned
exit 65 with a specific diagnostic.

`native_cli.kotoba` consumes the graph, records whether each source is `.cljk`
or `.kotoba`, lowers only `.cljk` surface syntax, and feeds native Form trees
to the semantic analyzer. `kotoba.sema/analyze-forms` exposes that Form route.
`native_project_linker.kotoba` resolves `:require` specs against the preceding
dependency packet, checks explicit exports (or public `defn`s when no export
list exists), and rewrites imported calls to private typed interface stubs
before semantic analysis. It admits alias imports, `:refer [name ...]`, and
the combined `[namespace :as alias :refer [name ...]]` spelling. Imported
interfaces validate one or more arity clauses using the 16 flat value
types recognized by the native value-type checker: `:i64`, `:f32`, `:f64`,
`:string`, `:keyword`,
`:symbol`, `:map`, `:bool`, `:bytes`, `:option-i64`, `:result-i64`,
`:vector-i64`, `:vector-f64`, `:string-index`, `:disjoint-set-i64`, and
`:document`. The rewriter tracks lexical bindings in `let`-family forms,
function parameters, and `catch`. The current Native analyzer cannot represent
function-valued locals; when a local binding shadows a referred function and
the body calls that local, the linker deliberately turns the call into a
rejected computed head instead of resolving it as the imported function.
Schema-backed record types are admitted when their closed descriptor and every
field type fit the bounded stub-value profile; `:with` and unsupported schema
shapes still fail closed. Multi-arity stub generation is covered by the
follow-up below; runtime dispatch has not been verified.

The Native Seed `check` passed for the 34-module CLI source closure in explicit
unpinned mode. A monolithic compile still hits Seed's fixed 3 MiB output
buffer (`E5001`), so the same dependency order was compiled as separate KSEEDO
objects and linked. The resulting AArch64 macOS KSEED is 3,834,169 bytes
(3,834,136 code bytes; `main` offset 3,811,756; SHA-256
`b1bbc9ceba29f7722e1eda93b479af65c3cd3e92a39e03ee869e2a98b97686ed`). This
artifact was built by the currently adopted Seed bootstrap; it is not evidence
that `bin/amu` has been replaced by an Amu-built compiler.

The extracted artifact ran through the C loader on scratch fixtures. A
single-module `.kotoba` project returned `semantic ok: modules=1`. The current
artifact returned `semantic ok: modules=2` for alias, `:refer`, combined
`:as`/`:refer`, `.cljk` `(-> ...)`, and all 16 flat interface-type fixtures.
Arity and argument-type mismatches returned exit 65, as did referring to a
private function. A top-level definition colliding with a referred name
returned exit 65 with a collision diagnostic. Fixtures with a local `let`
binding or function parameter named like a referred function and calling that
local also returned exit 65, avoiding false success as a global import. This
verifies graph discovery and semantic interface checking for those forms. The
stubs are only for analysis: this command does not emit or execute a linked
multi-module program, support the full project import/export/schema contract,
or replace the public launcher.
JVM, CLJS, Node, and Nbb dependencies remain in `bin/amu`.

## Kotoba CLI source-name boundary: 2026-10-17

The Kotoba-selected reader branch of `src/kotoba/compiler/cli.cljk` now
resolves the diagnostic source basename through the pure
`kotoba.compiler.posix-path-core` module. The `kotoba.io` require is conditional
and remains selected by the JVM and ClojureScript readers; the Kotoba reader
does not need that host I/O repository for this call site. This removes one
direct host-module edge from the native CLI source graph. The existing Native
CLI candidate (raw image SHA-256
`5a1bd885984b506a818a83dd413dd7381ca35d12c92b1eaf185b912e5d871764`) trapped
against the adopted loader's 4,096-datom kgraph limit. A scratch-only loader
with a 262,144-datom arena then resolved `cli.cljk` past `kotoba.io` and exited
65 at the next missing module, `kotoba.verifier`. This confirms the Kotoba
reader selects the pure path branch for this call site, but the scratch loader
is diagnostic evidence only; the adopted limit and production source closure
remain unchanged. The verifier source lives under
`kotoba-lang/kotoba-verifier/src` and is not in the current Native CLI
capability scope. Full import linking, executable generation, and host-runtime
removal remain open.

## Native CLI graph-memory follow-up: 2026-10-17

`kotoba_reader.kotoba` now exposes `read-first-form-bounded`, and
`native_project.kotoba` uses it to inspect only the leading namespace form
during dependency discovery. The later semantic pass still reads the complete
source. The adopted Seed checked `native_project.kotoba` in explicit unpinned
mode. It also compiled the updated reader, project resolver, and Native CLI as
separate KSEEDO objects and linked them into a 3,834,817-byte AArch64 macOS
KSEED (code length 3,834,784; `main` offset 3,812,400). This build used the
scratch diagnostic loader with enlarged arena budgets; the object compiles
reached 20.8 million vector items. It is bootstrap build evidence, not a
qualified production artifact or an Amu self-rebuild.

Running this CLI on the real `cli.cljk` graph reached the missing
`kotoba.verifier` dependency and exited 65 before semantic analysis. A
`native_project.kotoba` graph run trapped with `SIGILL` during packet
validation at 1,089,132 pairs; the loader reported no budget cause. A
scratch-only trace variant reached `kotoba.compiler.decimal-bits` during graph
discovery and trapped later while validating packet headers, at 1,089,380
pairs. The exact trap site remains unresolved.
The full CLI graph, executable project linking, and removal of the Node/nbb
and JVM host routes remain open.

An experiment put header parsing inside `arena-scope` and returned source
offsets, but the adopted Seed checker documents that it lowers `arena-scope`
without reclaiming memory. The scratch loader also recorded zero scope
releases. That experiment was reverted; memory reclamation needs a Seed or
selfhost compiler that implements the arena-scope contract before this path
can rely on it.

## Native project-linker multi-arity follow-up: 2026-10-17

`native_project_linker.kotoba` now reads every typed clause from an imported
function signature and emits one analysis stub clause per source arity. The
adopted Seed `check --unpinned` returned `ok` for the linker, frontend, and
sema modules. Rebuilding the updated frontend and sema objects and linking
them with the Native CLI closure produced a 3,836,385-byte AArch64 macOS KSEED
(SHA-256
`fe21bce015f1d166322789938ad38bdda19eced34ca4c275c16bab29700550e4`). The
build used the adopted Seed and explicit unpinned source roots. It confirms
module admission, object generation, and candidate linking; the candidate was
not run, so runtime dispatch across multiple arities remains unverified.

`frontend.cljk` and `kotoba.sema` expose the Kotoba-side capability table,
scalar admission limits, and typed-record wrappers for namespace clauses.
The namespace-clause wrapper moved the `project.cljk` check past its previous
`sema/namespace-attr-map->clauses` import error. A new typed reader-result
boundary (`read-forms-result` plus `read-error`) now replaces the unexported
host reader call on the Kotoba route. The current Native CLI resolves the
`frontend/base.cljk` closure to eight modules, but its semantic pass exhausts
the vector table while analyzing `kotoba.form`; it has not returned `semantic
ok`. This remains a bounded-Seed frontend gate, not a successful whole-project
check. The public `bin/amu` still uses JVM/CLJS/Node/Nbb paths; no host runtime
dependency has been removed from that launcher.

## Native Seed and frontend validation: 2026-10-17

The Native project resolver now indexes each supplied source's namespace and
direct `:require` list once, then reuses that metadata for graph discovery and
topological ordering. This is intended to avoid repeatedly allocating reader
forms in Seed's non-reclaiming arena. The receipt-pinned source/bootstrap
verification passes, and `scripts/seed/build-adopted.py --generations 3`
recompiled the adopted 16-module Seed image through three generations. Every
generation was 2,547,352 bytes with SHA-256
`6b158aa8654706743462b8a730f189072ba05f364b00af28a3f6d23045add2eb`, matching
the adopted image. This proves Seed self-build repeatability for that pinned
closure; it does not qualify the new Kotoba frontend or public launcher.

The earlier R8 diagnostic used a scratch-modified loader with reduced arena
defaults and was not the receipt-pinned loader, so its standalone `SIGILL`
results are not authoritative. With the exact pinned loader, the minimal
two-form module compiles, and the Native reader/project/CLI objects build,
link, and extract. The new semantic CLI initially trapped because
`artifact/sha256` calls the typed `:hash/sha256` capability; `native_cli.kotoba`
now declares that capability. Native CLI returns `semantic ok` for the
two-module `target_names.kotoba` closure. A scratch `.cljk` module containing
`(-> x (+ 1))` also returns `semantic ok`, exercising thread-first lowering
through the Kotoba frontend; this is a semantic check, not runtime execution.
The larger reader closure resolves to eight modules, then exhausts the vector
table while analyzing `kotoba.form`: `4,194,304` handles at the adopted budget
and `8,388,608` at the raised diagnostic budget. The highest run used
12,881,975 pairs and 397,633,537 bytes of measured arena heap before refusal.
No semantic success is claimed for that closure; the next gate is reducing or
bounding frontend allocation for this module.

The Nbb bootstrap cross-check found a separate dependency mismatch while
checking the current Kotoba-sema `form.cljk`: the Amu lock pins sema at
`a330352`, whose closed schema profile omits `:bytes`, so the Form payload
record is refused as `schema descriptor is outside the closed profile`.
Passing the current sema worktree as `--source-path` does not replace the
bootstrap compiler's locked sema dependency. The `:bytes` admission exists in
local sema work only (`4066e8a`, based on `0871c22`); current sema `main`
was at local ref `a7ef280` and still omitted it. Refreshing that remote ref
failed because this host could not resolve `github.com`, so verify sema `main`
before choosing an integration base. Do not point Amu's lock at that local-only
commit: first integrate the schema change on sema `main`, then advance Amu's
dependency pin and regenerate `deps-lock.edn` together. This bootstrap schema
refusal is separate from the Native CLI vector-budget exhaustion.

The r22 follow-up compiled the Native CLI with alias-stub generation filtered
by qualified names present in the consumer source. Its Seed-built AArch64
KSEED is 3,839,393 bytes (code length 3,839,360, `main` offset 3,816,960;
SHA-256
`a0a05e5e5f58f2bf29767d40ab58a43104460101a20d0a5ba72ad7970b357081`). With
that candidate, the two-module `target_names.kotoba` alias-import closure and
a one-module `.cljk` thread-first fixture both returned `semantic ok`. The
actual `kotoba/form.cljk` source also passed as a one-module Native CLI project
at 12,316,453 vectors, 17,709,104 pairs, and 559,378,572 bytes of arena heap.
In contrast, the `frontend_tables.kotoba` entry closure exhausted a 16M vector
table, using 23,598,279 pairs and 755,320,215 bytes of arena heap. The full
eight-module `frontend/base.cljk` closure still exhausted the vector table: at
24M handles it used 36,245,422 pairs and 1,153,645,270 bytes of arena heap; at
the 32M limit it used 51,159,392 pairs and 1,578,939,274 bytes. The latter
also reported zero scope releases. No semantic success is claimed for either
larger closure. The source-text filter did not remove the allocation ceiling;
the adopted Seed build still lowers `arena-scope` without reclaiming memory.
The next gate is to implement or select a compiler path that honors the
arena-scope contract, then rerun these closures. This remains a Native CLI
qualification gap; JVM, CLJS/nbb and Node dependencies remain in the public
launcher.

## Native project-check allocation follow-up: 2026-10-17 (r24)

`native_frontend.kotoba` now reads a project module once and passes that same
form tree to `native_project_linker.kotoba` through `link-project-forms`.
Previously the frontend parsed the source, then the linker parsed it again.
Reader failures still take the semantic reader-error path. The updated
linker/frontend/CLI build passed through the adopted Seed and linked to an
AArch64 macOS KSEED with 3,839,744 code bytes (SHA-256
`e32177c0548418d879d8f0e02ce410e07f955a9b6300efb7768c623ede63de2d`).

The r24 Native CLI returned `semantic ok` for the two-module
`target_names.kotoba` alias-import closure, the one-module `.cljk` thread-first
fixture, the actual one-module `kotoba/form.cljk` source, and the two-module
`kotoba.compiler.kotoba-reader` entry closure. The reader closure used
13,884,839 vectors, 25,027,836 pairs, and 707,168,719 bytes of arena heap. The
full eight-module `frontend/base.cljk` project still exceeded a 32M vector
table. A scratch-only trace reached `kotoba.compiler.kotoba-reader` after
starting the `kotoba.form`, frontend-tables, string, string-join, text, and
decimal-bits modules; the run then trapped at 33,554,432 vectors, with
50,272,040 pairs and 1,565,574,628 bytes of arena heap. The duplicate-parse
removal lowered the high-water mark slightly, but did not complete the graph.
The adopted Seed reports zero arena-scope releases, so accumulated per-module
analysis allocations remain the main blocker. No host runtime has been
removed from `bin/amu`.

## `.cljk` conditional-thread lowering: 2026-10-17

The Kotoba surface lowerer now admits `cond->` and `cond->>` alongside `->`,
`->>`, and `as->`. It evaluates the initial value once, then builds sequential
Kotoba `let` bindings whose `if` expressions evaluate every condition in
source order and apply each admitted thread step only when its condition is
true. Generated local names are chosen outside the source form to avoid
capturing user bindings. This extends the native `.cljk` analyzer's lowering
boundary; it does not execute Clojure or ClojureScript macros.

The adopted Native Seed `check --unpinned` returned `ok` for the updated
lowerer, and source-only compilation produced a 123,816-byte AArch64 macOS
KSEED (SHA-256
`d9291d28bef8e74a5dbbaa46dde2e05f942a642e7c4b0251870f985d9b08495f`). This
confirms source admission and code generation; the artifact was not executed,
and the change has not yet been exercised through the full Native CLI. The
lowerer remains a bounded syntax subset, and no launcher or host runtime
dependency has been removed.

## Native Seed `arena-scope` lowering: 2026-10-17

The Seed checker now retains `arena-scope` as a checked node instead of
rewriting it to `do`. It checks the scalar result, clears tail position so an
outer `recur` cannot jump past LEAVE, and rejects an unhandled abort with
E2180 so a throw or aborting call cannot jump to a handler outside the scope.
An abort caught by a `try` inside the scope remains admitted. Seed lowering
emits ABI v6 `arena_enter` (context offset 224), the body, then `arena_leave`
(offset 232), preserving the scalar in its temporary while LEAVE writes to
the next temporary. The test-only SIR interpreter treats these two void calls
as no-ops; it does not model arena reclamation.

The AArch64 optimizer excludes functions containing either arena operation
from vector-length and parameter-zero-return inference. This prevents bounds
check or alias facts from crossing a scope that can invalidate handles.

The adopted Seed compiled the final 16-module Seed source, and each resulting
image compiled the same source for two more generations. All three containers
were 2,548,211 bytes and byte-identical (SHA-256
`46a40863726c2aabf4b00b53f0882dc0836ee485e0d396058cc556a0cc5c5c84`). A
program produced by the third-generation Seed ran 20,000 iterations, allocating vectors of
16 and 8 items in nested scopes and catching a throw inside the inner scope.
It returned `20000`; the loader recorded 40,000 scope releases, with a high
water mark of 2 vector handles, 24 vector items, and 224 heap bytes. A separate
source with an unhandled throw inside `arena-scope` was refused as E2180 at
byte 69. These results verify Seed lowering and runtime reclamation on this
probe. A full Native CLI source closure has since been rebuilt through the
third-generation Seed; see the follow-up below. No JVM, ClojureScript/nbb, or
Node route has been removed.

## Native CLI 34-module closure follow-up: 2026-10-17

The final Seed built all 34 modules in the current Native CLI source closure
as separate objects and linked the CLI into a 3,844,857-byte AArch64 macOS
KSEED; extracting its entry reported offset 3,822,364. The Native CLI ran
successfully on a one-module Kotoba check and on a scratch two-module import
fixture (`semantic ok`, two resolved modules). These controls establish the
basic Native CLI execution and project-link path for small inputs.

This checkpoint's reader-trap diagnosis was incorrect: the run omitted the
reader's declared `:hash/sha256` wire 3 and did not provide the later G3
arena-scope implementation. With wire 3 granted, the reader source returned
`semantic ok: modules=2`; see the following update. The larger frontend
closure was subsequently completed by the G3-built Native CLI.

## Native schema imports and G3 frontend check: 2026-10-17

`native_project_linker.kotoba` now carries each provider's closed namespace
schema table with imported interface stubs, merges those tables with the
consumer's local schemas, and adds the result to the importing namespace.
Finite schema-backed record values are synthesized recursively for analysis
stubs, including `[:ref :kotoba.reader/out]`. These remain semantic interfaces;
the Native CLI does not yet emit or execute a linked multi-module program.

The Kotoba reader now treats a selected top-level `nil` reader-conditional
branch as an omitted definition, so the common `.cljk` compatibility spelling
`#?(:kotoba nil :default (defn ...))` leaves no stray top-level value. Nested
`nil` remains a value. A scratch Native CLI fixture using this spelling and a
Kotoba `main` returned `semantic ok: modules=1`.

The Native CLI was rebuilt with the G3 Seed that lowers `arena-scope` to the
runtime enter/leave operations. Its AArch64 macOS KSEED is 3,851,393 bytes
(code 3,851,360 bytes, `main` offset 3,828,900, SHA-256
`7e6b170a8f0655c7adb7f26688aee2f2d23a92bd7911d393e37ad944f7121dbf`). The
reader control returned `semantic ok: modules=2` with 10,779,908 vectors,
19,232,591 pairs, and two scope releases. Most importantly, the real
`kotoba.compiler.frontend.base` `.cljk` project returned
`semantic ok: modules=8`; it used 22,316,546 vectors, 42,968,661 pairs, and
1,183,128,637 bytes of arena heap, and recorded eight scope releases. This
resolves the previous pair/vector exhaustion for this closure and admits the
imported reader-result record type.

This is Native semantic-check evidence from a Seed-built CLI, not a complete
Amu self-rebuild, command-surface parity, code generation, or execution of a
linked multi-module program. JVM, ClojureScript/nbb, and Node dependencies
remain in the public `bin/amu` path.

## Native project entry diagnostics: 2026-10-17

The Native CLI now has `modules` to report a resolved dependency order and
`check-entry` to analyze one entry after resolving its dependency sources.
These modes separate source-graph resolution from the full project semantic
pass; `check-entry` does not semantically validate dependency bodies. With the
six configured source roots, `frontend/base.cljk` resolves to eight modules.
The reader-conditional `.cljk` control fixture passes `check-entry`.

The first recheck was misconfigured: its loader allow-list omitted wire 3,
which the Native CLI declares for `:hash/sha256`. Schema identity computation
then trapped in `artifact/sha256`. With wire 3 added to the allow-list, the
actual `kotoba/form.cljk` entry passed `check-entry`, and the full
`frontend/base.cljk` eight-module project passed `check`. This reproduces the
recorded G3 frontend result; the earlier SIGILL was a test-invocation
capability omission, not evidence of a Seed semantic trap.

The corrected per-entry sweep over the 27-module `frontend.cljk` graph used
allow-list `3,35,37,38,39`. Nineteen entries returned `semantic ok`:
`kotoba.form`, `kotoba.compiler.frontend-tables`, `kotoba.artifact.core`,
`kotoba.compiler.value-type`, `kotoba.lang.coll`, `kotoba.kir.value`,
`kotoba.compiler.validate-expr`, `kotoba.compiler.affine`,
`kotoba.compiler.schema`, `kotoba.string`, `kotoba.string.join`,
`kotoba.lang.text`, `kotoba.compiler.decimal-bits`,
`kotoba.compiler.kotoba-reader`, `kotoba.compiler.frontend.base`,
`kotoba.compiler.frontend.kernel-region`,
`kotoba.compiler.frontend.closure-types`,
`kotoba.compiler.frontend.validate`, and `kotoba.compiler.frontend`.
Eight entries still trapped with `SIGILL` in this invocation:
`kotoba.compiler.frontend.expand`,
`kotoba.compiler.frontend.namespace-defs`,
`kotoba.compiler.frontend.infer`,
`kotoba.compiler.frontend.record-projection`,
`kotoba.compiler.frontend.desugar`, `kotoba.compiler.frontend.row`,
`kotoba.compiler.frontend.state-ability`, and
`kotoba.compiler.frontend.analyze`. The stderr for every one of those
runs records `:budget/cells` on `:pairs` at exactly 67,108,864, the loader's
64 Mi-entry ceiling; the run's arena scope does not reach its release. These
are pair-arena exhaustion failures during analysis of the selected entry, not
unclassified traps. Raising `KEXE_PAIRS` cannot exceed the loader ceiling, so
the next gate is to reduce per-entry analyzer allocations or split the
analysis while preserving module-wide semantics. `check-entry` resolves
dependency sources but checks only the selected entry body. No JVM, CLJS/nbb,
or Node dependency has been removed from the public launcher.

## Native direct-dependency packet follow-up: 2026-10-17

The Native CLI now gives the linker only the current module's direct
`:require` sources. The linker looks up imported interfaces by those
namespace names and does not inspect transitive source bodies. The updated
project-files and CLI modules compiled and linked through the G3 Seed. The
`kotoba.form` entry still passes, and the full `frontend/base.cljk` project
still returns `semantic ok: modules=8` with 42,901,848 pairs, 22,304,455
vectors, 1,181,113,369 bytes of arena heap, and eight scope releases.

The resolver-precedence-corrected sweep still passes 19 of 27 entries; the
same eight larger frontend entries exhaust the 67,108,864-pair ceiling. For
`frontend.expand`, graph-only `modules` resolves its 13-module closure using
156,460 pairs; `check-entry` then reaches the ceiling during the additional
semantic pass. Direct-dependency packets reduced string-pool use from
20,967,404 to 18,807,199 bytes, vectors from 23,081,923 to 23,069,242, and
arena heap from 1,574,685,060 to 1,572,220,663 bytes, but pair use still
reached the ceiling. This trims source-packet overhead without resolving the
large-entry analyzer allocation gate. No JVM, CLJS/nbb, or Node dependency has
been removed from the public launcher.

## Reader-conditional allocation follow-up: 2026-10-17

The Native Kotoba reader now scans unselected collection branches without
retaining their child syntax trees. It still validates collection structure,
map parity, nesting limits, and ordinary token and string forms; selected
branches continue through the full reader. The changed reader, project-files,
and Native CLI modules compiled and linked through the G3 Seed. `kotoba.form`
and the `frontend/base` entry passed `check-entry`; `frontend.expand` still
reached the loader's 67,108,864-pair ceiling during semantic analysis. Raising
that limit is rejected by the loader. The same 27-entry sweep now passes 21
entries, up from the previous 19: `frontend.namespace-defs` passes at
64,917,242 pairs, and `frontend.row` at 64,360,075. The six remaining entries
(`frontend.expand`, `infer`, `record-projection`, `desugar`, `state-ability`,
and `analyze`) still reach the pair ceiling. This reduces reader allocation
for these `.cljk` sources but does not clear the large-entry analyzer gate;
the JVM, CLJS/nbb, and Node dependencies remain in the public launcher.

## Native frontend sweep with pair hash-consing: 2026-10-17

The stable Native CLI artifact above (raw SHA-256
`75d8d6824e4e7f40fc3352b33626553fdd6e204c8fd25f7dcf48fe2d6ed5db35`) was
rechecked across the same 27 frontend entries with the G3 loader's optional
`KEXE_HASHCONS=16` pair-sharing table enabled. This exact pair reuse is a
loader diagnostic setting, not the default launcher configuration. The sweep
passed 24/27 entries, up from 21/27 with hash-consing off. `frontend.expand`,
`frontend.record-projection`, and `frontend.state-ability` cleared their
previous pair-arena failures. `frontend.expand` completed at 40,650,571 pairs
with 33,606,751 pair hits; `frontend.record-projection` completed at
65,155,871 pairs; and `frontend.state-ability` completed at 38,712,749 pairs.

Three entries still fail under this configuration. `frontend.infer` reaches
the 67,108,864-pair ceiling; retrying with `KEXE_HASHCONS=22` and `24` still
reaches that ceiling. `frontend.analyze` also reaches the pair ceiling, even
with the 2^24-entry table. `frontend.desugar` first exhausted the configured
33,554,432-vector table; with vectors raised to the loader's 67,108,864-entry
maximum, it then reached the pair ceiling. The maximum-vector retry used
48,034,409 vector handles and 40,335,642 vector items before the pair trap.

This identifies three remaining per-entry allocation gates under a more
sharing-friendly loader configuration. It does not change the default Native
CLI environment or the public launchers: `bin/amu` still starts on Node and
`bin/kotoba` still starts on nbb. `check-entry` is frontend admission evidence,
not proof that Amu has built the complete Kotoba compiler without those
bootstrap runtimes.

## Native syntax-sugar allocation follow-up: 2026-10-17

The Native `.cljk` syntax-sugar pass now scans for admitted thread forms before
rebuilding. It returns the original Form when no sugar occurs and rebuilds
only paths that contain a lowered form. This avoids constructing replacement
Form records for untouched source trees.

The source compiled as a module with `seed/bootstrap/adopted-20261012.bin`
(20,530 bytes; SHA-256
`ebc2753b39ce8de084ccce3b83a5f4f12f01b0e6b45625335fea4e89d4e25999`).
Replacing the syntax-sugar object in the current Native CLI object set linked
to a 3,868,129-byte AArch64 macOS KSEED (SHA-256
`81b03784e0ed4bec8b750f9a165832b8ac0f8ad871caa419f32402ee93c1f251`). Its
extracted raw entry has SHA-256
`6dcda89b00de9001570a4c155573c990c3eb945a929ec0d1a5b95be68b3ed94d`.
`check-entry` accepted a scratch `.cljk` module whose `main` uses `(-> 3
plus-one)`, returning `semantic ok: entry=kotoba.syntax-sugar-probe
dependency-sources=0`. This verifies the small project-analysis path through
the updated lowerer. A paired run against the previous CLI raw (SHA-256
`75d8d6824e4e7f40fc3352b33626553fdd6e204c8fd25f7dcf48fe2d6ed5db35`) also
returned the same semantic result. On this small fixture, the new lowerer used
153,065 pairs and 127,476 vectors; the previous raw used 153,192 pairs and
127,519 vectors. The exact paired readings are in the scratch
`pair-comparison.tsv`. This 127-pair difference is a narrow signal, not
evidence that the three large frontend allocation gates are cleared. The
24/27 sweep above remains the latest large-entry allocation evidence. The
check does not execute the source program. `.kotoba` input and public launchers
are unchanged.

## Native project-link rewrite allocation follow-up: 2026-10-17

The project linker now scans each source form for an imported call head before
rewriting. Forms without one are returned unchanged, so local-only definitions
do not build replacement Form trees. The scan skips `quote` and `ns`, matching
the rewrite boundary. The changed linker compiled as a Native Seed module
(244,503 bytes; SHA-256
`cd150b9cc8c6be67a99b9fd5f64a05dbe6529d528abeb5fde7e0463bba776c6c`) and was
linked into a 3,868,969-byte AArch64 macOS Native CLI.

On the same 128-helper no-import fixture, the linked candidate and the control
with the previous linker both returned `semantic ok`. With
`KEXE_HASHCONS=16`, the candidate used 5,167,290 pairs and 6,936,616 vectors;
the control used 5,169,480 pairs and 6,938,163 vectors. A two-module alias
import fixture also returned `semantic ok` on both CLIs: 193,927 candidate
pairs versus 193,937 control pairs. These small checks show lower allocation
on the no-import case and preserved import admission, but do not measure runtime
or clear the large-entry analyzer gates. The source program was not executed;
JVM, CLJS/nbb, and Node launch paths remain.

## Native frontend no-op rewrite allocation follow-up: 2026-10-17

The Kotoba-native `analyze.cljk` and `expand.cljk` now scan for the syntax each
pass changes and keep a top-level Form intact when no matching form exists. The
doseq annotation and app-data byte-write passes use exact supported traversal
shapes; pure-application scanning stops at `quote` and scans nested call heads,
matching the rewrite pass. Both
modules compiled through the Native Seed compiler (`expand`: 423,136 bytes,
SHA-256 `09b51b9beb27df84251858f1fda131e9e4234c2da0f1f18c8a6ef1fc8587fe1f`;
`analyze`: 954,131 bytes, SHA-256
`cdfa68677a875c5e3590bd4d0d66f67a74f10fb9dcd3210f100926e7b0511e16`). The
linked Native CLI entry raw is SHA-256
`80b54e10be3a15e59efd95d3d9dd13bf473a04d0f3b40754e0f91b115ad18a0c`.

Paired `check-entry` runs used the same Native Seed, source paths, arena limits,
and `KEXE_HASHCONS=16`; the previous raw had the same project-linker change but
the earlier frontend modules. On the 128-helper no-import fixture, both runs
returned `semantic ok`; pairs fell from 5,167,877 to 5,159,044 and vectors from
6,936,669 to 6,930,714. On `frontend/expand.cljk`, both runs returned
`semantic ok` with 12 dependency sources; pairs fell from 40,754,157 to
40,661,370, vectors from 21,854,749 to 21,785,237, and heap bytes from
1,154,147,702 to 1,150,864,846.

The nested call-head fixture `((ref f) 1)` also returned `semantic ok` on the
candidate (151,287 pairs, 126,882 vectors). For `frontend/analyze.cljk`, the
old and new CLIs both reached the 67,108,864-pair ceiling and trapped with
`:budget/cells`; heap was 1,428,442,636 bytes on the old CLI and 1,428,449,184
on the new one. This change does not clear the large-entry gate. These checks
admit source only and do not execute it. JVM, CLJS/nbb, and Node launch paths
remain unchanged.

## Native HIR validator module boundary follow-up: 2026-10-17

The Kotoba-native HIR envelope validator now lives in
`kotoba.compiler.frontend.hir-validation`; `analyze.cljk` calls its `valid?`
entry and keeps the validator out of the large analyzer module. The Native Seed
compiled `hir-validation` to 31,355 bytes (SHA-256
`234afd8edb80c0a606790e0406205a45886de0199414093f4e978e7efb04411c`) and the
reduced `analyze` module to 933,162 bytes (SHA-256
`fb1abde41c4a57dbd612cf08ce6e4f021184f830f7a487fa10bffc5880f49629`). The
linked project graph lists 27 modules, including both `hir-validation` and
`analyze`. A Native Seed `check-entry` of `hir_validation.cljk` returned
`semantic ok` with eight dependency sources (4,761,615 pairs and 3,279,475
vectors).

This extraction has not cleared the analyzer gate: `check-entry
frontend/analyze.cljk` still traps at 67,108,864 pairs with `:budget/cells`
(heap 1,428,672,449 bytes). The native CLI checks source admission; they do
not execute the validator or a compiled Kotoba program. This is a module
boundary and selfhost-closure increment, not evidence that the complete
frontend runs natively. JVM, CLJS/nbb, and Node launch paths remain.

## Native HIR value helpers module boundary follow-up: 2026-10-17

The native HIR typed-value selection and callable-field erasure helpers are
now isolated in `kotoba.compiler.frontend.hir-values`; `analyze` calls those
helpers through a narrow module interface. Its Native Seed `check-entry`
returned `semantic ok` with 11 dependency sources (4,906,331 pairs and
153,514,507 heap bytes). Native `modules analyze.cljk` returned a 28-module
graph containing both `hir-validation` and `hir-values`.

The full `check-entry frontend/analyze.cljk` still traps at 67,108,864 pairs
(`:budget/cells`, 1,428,795,903 heap bytes), essentially the same admission
wall as the preceding split. The extraction makes this Kotoba-native compiler
responsibility separately checkable; it has not reduced the whole analyzer
closure below the current arena ceiling, and it has not executed the generated
HIR path. Runtime retirement remains gated on broader native parity.

## Native absence-resolution module boundary follow-up: 2026-10-17

The Kotoba-route `resolve-function-absences` and `retire-absence-markers`
functions now live in `kotoba.compiler.frontend.absence-resolution`; the
existing host implementations remain in `analyze.cljk`. Native Seed `modules`
resolved the 18-module absence-resolution closure and the 29-module analyze
closure, including the new module. The latter graph check used 331,237 pairs,
80,010 vectors, and 49,802,019 bytes of arena heap.

Native Seed `check-entry` read and resolved the new module, then exhausted its
configured 4,194,304-vector table at 14,022,519 pairs and 345,441,487 bytes of
arena heap. It did not return `semantic ok`, so semantic admission of this
module remains unverified. A retry with an 8,388,608-vector table and
33,554,432-pair limit reached semantic analysis but failed with
`expression type mismatch: expected [:ref :form/r], got option-i64` after
14,568,642 pairs, 5,085,553 vectors, and 375,326,773 bytes of arena heap.
The extracted let-binding helper was using a form vector where the original
analyzer returned its typed `:ana/r` record. A follow-up Native Seed
`check-entry` of the actual module source now returns `semantic ok` with 17
dependency sources (exit 0), using the 8,388,608-vector / 33,554,432-pair
arena. Isolated, uniquely named candidates showed that the helper's trailing
`:default nil` clause caused the earlier type mismatch; removing that fallback
from this Kotoba-only reader branch preserved the implementation and admitted
the source. The result is source admission only; it does not execute the
resolver or prove `.cljk`/`.kotoba` behavioral parity. The analyzer's existing
67,108,864-pair admission wall also remains unresolved. No JVM, CLJS/nbb, or
Node dependency has been removed from a launcher; runtime retirement still
requires broader native parity and execution evidence.

## Native source prepasses module boundary follow-up: 2026-10-17

The Kotoba-native doseq collection-kind annotation and `fs/app-data-bytes`
source rewrite now live in `kotoba.compiler.frontend.source-prepasses`.
`analyze.cljk` imports those two functions; its host implementations remain
available on the default route. Native Seed `modules analyze.cljk` now resolves
30 modules, including `source-prepasses`; the new module's own graph resolves
9 modules.

Native Seed `check-entry source_prepasses.cljk` returned `semantic ok` with
eight dependency sources: 3,635,470 pairs, 2,963,798 vectors, and
136,658,350 bytes of arena heap. This admits the two source transformations as
a Kotoba-native module. It does not prove their runtime behavior or complete
frontend execution. The analyze pair ceiling remains open; no JVM, CLJS/nbb,
or Node launcher dependency has been retired.

## Native implicit-export analysis module boundary follow-up: 2026-10-17

The Kotoba implementations of `intrinsic-helper-name?` and
`implicit-export-exclusions`, with their private loop-ownership traversal,
now live in `kotoba.compiler.frontend.implicit-exports`. `analyze.cljk`
imports these functions on the Kotoba route and retains its existing host
implementations on the default route. Native Seed `check-entry` of the new
module returned `semantic ok` with eight dependency sources. Native Seed
`modules analyze.cljk` resolved a 31-module graph containing
`implicit-exports`. A separate scratch importer referred to both public
functions and returned `semantic ok` with nine dependency sources. This admits
source and confirms the dependency edge; it does not execute the export
calculation or establish host/native output parity. The latest full analyzer
entry check, before this extraction, reached the 67,108,864-pair ceiling; it
has not been rerun against the smaller module.
No JVM, CLJS/nbb, or Node launcher dependency has been retired.

## Native export-form module boundary follow-up: 2026-10-17

The Kotoba export selection and multi-arity name expansion moved into
`kotoba.compiler.frontend.export-forms`; `analyze.cljk` imports
`an-exports` and `an-public-sources` on the Kotoba route. This moved 12 Kotoba
forms out of the analyzer source. Native Seed `check-entry export_forms.cljk`
returned `semantic ok` with nine dependency sources. A scratch Kotoba importer
calling both exports also returned `semantic ok` with ten dependency sources.
Native Seed `modules analyze.cljk` resolves 32 module records and includes
`export-forms`. These checks admit source and resolve the import boundary; they
do not execute export selection or establish host/native output parity. The
latest full analyzer check, before this extraction, reached the 67,108,864-pair
ceiling and has not been rerun. No host-runtime dependency has been removed.

## Native effect-inference module boundary follow-up: 2026-10-17

The Kotoba implementation of direct effect/call discovery and transitive
effect-row inference now lives in `kotoba.compiler.frontend.effect-inference`.
`analyze.cljk` imports `infer-effects` on the Kotoba route; its host
`direct-facts` and `infer-effects` implementations remain on the default
route. Native Seed `check-entry effect_inference.cljk` returned `semantic ok`
with eight dependency sources. A scratch entry importing and calling the
export returned `semantic ok` with nine dependency sources. Native Seed
`modules analyze.cljk` resolved 33 module records and included
`effect-inference`. These checks admit the module and resolve its import; they
do not execute effect inference or establish host/native output parity. The
full analyzer entry check has not been rerun; the previous analyzer check hit
the 67,108,864-pair ceiling. No JVM, CLJS/nbb, or Node launcher dependency has
been removed.

## Native analyzer finalization-stage follow-up: 2026-10-17

The Kotoba `an-stage-finish` path now passes a typed `:ana/fh` record through
separate export/header admission, schema and value validation, and HIR/effect
assembly functions. This shortens each function's local binding graph while
preserving the stage order. Native Seed `check-entry analyze.cljk` parsed the
updated source and dependency graph, then again reached the 67,108,864-pair
arena ceiling. The run recorded 46,138,024 hash-cons pair hits and about
1.429 GB heap; the preceding run was 46,138,545 hits and about 1.429 GB, so
this function-level split did not materially lower cumulative arena use. It
does not establish semantic parity or remove host runtime dependencies. The
next step is to investigate module-scope arena reclamation or reduce the
reachable native analyzer graph, rather than continue source-only function
splits. No JVM, CLJS/nbb, or Node launcher dependency has been removed.

## Kotoba-only finalization module extraction follow-up: 2026-10-17

Moved Kotoba HIR/effect finalization from `frontend/analyze.cljk` into the
Kotoba-only `frontend/finalize.cljk` module. `an-stage-finish` now hands the
validated stage values to `finish-hir`; the host route remains in the analyzer.
Native Seed `check-entry finalize.cljk` returns `semantic ok` with 20 dependency
sources at 13,294,033 pairs, 10,153,514 pair hits, and 398,397,301 heap bytes.
`modules analyze.cljk` resolves the 35-module closure, including `finalize`, at
359,244 pairs. These checks admit source and imports; they do not execute the
finalizer or prove host/native behavior parity.

The current full `check-entry analyze.cljk` still traps with SIGILL and reaches
the 67,108,864-pair loader ceiling, with 46,138,040 pair hits and 1,429,401,785
heap bytes; no arena scope is released. Moving finalization out of the analyzer
therefore does not clear the full-entry gate. The next useful work is to isolate
which reachable analyzer/module stages retain arena data or generate the trap.
No JVM, CLJS/nbb, or Node runtime dependency has been removed.

## Direct Native `.cljk` analysis and lint entrypoints: 2026-10-17

The exported Native frontend entrypoints `analyze-cljk-source` and
`lint-cljk-source` now read with the bounded Kotoba reader, lower each admitted
surface form through `syntax-sugar/lower-surface`, and pass the canonical forms
to the same `analyze-forms` and `lint-forms` APIs used by `.kotoba`. Added
`lint-forms` through the Kotoba analyzer, frontend, and sema export boundaries.
Native Seed `check-entry` returns `semantic ok` for `kotoba.sema.cljk` (36
dependency sources; 4,270,310 pairs), `frontend.cljk` (35; 10,630,115 pairs),
and `native_frontend.kotoba` (40; 4,095,517 pairs). These checks admit source
and linked signatures; they do not execute either entrypoint or compare
Definition CIDs.

The full `check-entry analyze.cljk` remains at the 67,108,864-pair loader
ceiling with SIGILL, 46,137,508 pair hits, and 1,429,407,672 heap bytes. The
direct surface entrypoints are now wired to the bounded sugar pass, but
`.cljk`/`.kotoba` execution and Definition CID conformance remain unverified.
JVM, CLJS/nbb, and Node dependencies have not been removed.

## Measured distance

`scripts/measure-selfhost-distance.cljk` in `kotoba-lang/kotoba-lang` writes
`lang/selfhost-distance.edn`. The last recorded figures, at amu `821ed388`
(2026-09-26), are reachable stage 1 = 9, stage 2 = 8, stage 3 = 2, of 142
source files. Largest stage-1 walls then: source over the 1 MiB admission
limit (29, `kotoba-sema` `frontend.cljk`), qualified call not an admitted
exported import (19), `[:set :keyword]` item type mismatch (7), and
`#?(:clj)`-only empty bodies (7). Re-measure before quoting these; the file in
`kotoba-lang/kotoba-lang` is the authority, not this paragraph.

A file that reads is not a file that compiles, and a file `check` admits is
not a file whose semantics survive lowering. The scoreboard says how far the
compiler's text is from the language's text surface; it does not by itself
prove the compiler is selfhost.

Version 3 of the measurement adds per-module native compilation plus verifier
admission (stage 2), then differential execution against the host reading
(stage 3) for functions the loader can drive. These are useful module-level
qualification gates, but the runner still invokes the Node/nbb `bin/amu` path,
and the report remains on `:plane :authored-input`. Even an all-green report
would not show that an Amu-built compiler can rebuild and run the compiler
without JVM/Clojure, CLJS/nbb, or Node.

## Embench

`bench/embench/` holds the Kotoba ports and the qualification runner. The
2026-09-29 Apple M4 numbers in `bench/embench/REPORT-20260929.md` were taken
with a GraalVM-built compiler (SHA-256
`59e3081256a116d3f50e864f44178bb35d38f5e07fd86420929c5ae13ad99ba0`). Under
rule 2 they are **bootstrap-reference numbers**. They are also not official
Embench scores.

## 2026-10-17 native compiler and runtime core follow-up

Moved the Kotoba lint implementation out of `frontend/analyze.cljk` into the
new `frontend/lint.cljk` module. `frontend.cljk` now routes its Kotoba lint
entrypoints through that module while the host implementations remain on the
default route. Native Seed rebuilt and linked the full 46-module compiler CLI
closure (3,965,233 bytes; SHA-256
`b8a7de2c271080627eb28d9e304536658afe29c8aba907c268049d4ab572567f`).
The first attempt to run that KSEED as a raw image was invalid: it trapped on
the `KSEED1` container header before guest allocation. Do not count that as an
analyzer result. After extracting the `main` symbol at offset 3,943,016, a
47-module r13 Native CLI ran `modules analyze.cljk` and resolved 38 sources.
`check-entry typed_ops.cljk` returned `semantic ok` at 583,830 pairs. With the
loader's maximum vector table, `check-entry analyze.cljk` reached the
67,108,864-pair ceiling (11,915,848 vectors; 2,861,933 vector items;
87,447,431 string-pool bytes; 1,374,738,287 arena bytes). A 4,194,304-vector
run hit that lower vector cap first. This r13 CLI was built directly from the
adopted Seed image, so it is not the later G3 arena-scope build described
above. It was not executed as a self-hosted rebuild.

On the runtime side, `runtime.kotoba` now exports the existing Kotoba WASM byte
codec operations for alignment, heap-base calculation, LEB encoding, packed
byte concatenation, vectors, and sections. Native Seed rebuilt and linked its
14-module runtime closure (405,874 bytes; SHA-256
`50ccf00ac8d17439866123ff343e276e128bf8d53049ff102de2f4a3325f7f9b`). The
artifact was not executed, and this build does not establish runtime behavior
parity. Analyzer arena reclamation, self-hosted compiler rebuild, runtime
execution parity, and `.cljk`/`.kotoba` Definition CID conformance remain open.

The pinned `scripts/seed/build-adopted.py` refused a new generation because
the current working tree differs from the adoption receipt in four existing
Seed files (`00-ns`, `21-check`, `30-lower`, and `41-a64gen`). Those changes
include the arena-scope lowering needed by the G3 CLI. They are preserved; an
un-pinned three-generation build from the current manifest is running in a
separate workspace and will be reported independently of the adopted receipt.

## Native `.cljk` to `.kotoba` HIR comparison follow-up: 2026-10-17

`native_cli.kotoba` now exposes `compare-hir <surface.cljk> <core.kotoba>
--unpinned [--source-path DIR ...]`. It resolves each project graph and
compares the entry modules' analyzed HIR with Kotoba `form/eq`. The command
reports HIR equality explicitly; it does not report or imply Definition CID
equality.

The first broader comparison exposed a lowering defect: `cond->` and
`cond->>` generated `__kotoba_` temporaries, a prefix refused by the analyzer.
The lowerer now uses collision-checked `kotoba_cond_tmp_` names. Native Seed
recompiled the changed syntax-sugar module (20,514-byte object), linked a
3,947,953-byte KSEED, extracted its `main`, and ran the 3,947,920-byte AArch64
macOS raw image. That raw image has SHA-256
`da59234d29d96e843be3bcb971c3eb7b858b5589cb0a7d9ce5f9f7c6323a5380`.

`compare-hir` returned 0 with equal HIR for paired forms using `->`, `->>`,
`as->`, `cond->`, and `cond->>`. A two-step conditional case with an input
binding that collides with the temporary-name prefix also matched, as did a
quoted-symbol `defn`. Changing a core `(+ 40 2)` to `(+ 40 3)` produced
`semantic mismatch` and exit 65. This is a small positive/negative corpus, not
a complete surface conformance corpus.

The same corrected CLI and syntax-sugar object were then rebuilt with the G3
Seed, which implements runtime `arena-scope` enter/leave. Its extracted raw
image is 3,947,992 bytes with SHA-256
`d85408b7ed100503e4d9a6dd2f0b5e07f061605c9ab978fb3e9d7264c6baf7ec`. The
five sugar pairs, quoted-symbol case, collision case, and mismatch control all
had their expected result; each execution recorded one arena-scope release.
Using the same G3 CLI, the actual `kotoba.compiler.frontend.base` source graph
also returned `semantic ok: modules=8`, with 42,492,436 pairs, 22,152,898
vectors, 1,170,947,951 arena-heap bytes, and eight scope releases.

The artifact was built by the adopted Seed from the current Amu worktree; Amu
did not build this compiler. This does not establish Definition CID parity,
full project/build/verification CLI parity, or public launcher parity. JVM,
CLJS/nbb, and Node dependencies remain, as do analyzer arena reclamation,
self-hosted compiler rebuild, and runtime execution parity.

## Current Native analyzer gate recheck: 2026-10-17

With the G3-lowered Native CLI artifact above and the current analyzer source,
`check-entry frontend/analyze.cljk` still traps before its enclosing scope can
leave. The run returned exit 120 with `SIGILL` / `:budget/cells` at the
67,108,864-pair loader ceiling; it used 15,074,298 vectors, 1,459,753,635
arena-heap bytes, and 48,152,402 hash-cons pair hits. This diagnostic run set
`KEXE_HASHCONS=16`; it did not change the loader ceiling. The analyzer gate
therefore remains a compiler/frontend allocation blocker, not a launcher
parity result.

## 2026-10-17 analyzer inference import bridge experiment

Added a Kotoba-only `frontend/infer-bridge.cljk` facade and routed the Native
branch of `frontend/analyze.cljk` through it. This keeps the host `infer`
imports on the default reader branch while presenting the analyzer with a
bounded Kotoba import surface. Native Seed compiled the bridge and analyzer,
then rebuilt the dependent `frontend`, `sema`, Native frontend and CLI modules
in a separate scratch object closure. The linked KSEED is 4,035,401 bytes;
its extracted `main` is 4,035,368 bytes at offset 4,006,344. This is a G3
Seed-built artifact, not an Amu self-rebuild.

`check-entry frontend/analyze.cljk --unpinned` returned exit 120 with a guest
`SIGILL`. The arena report recorded 60,043,037 pairs, 45,390,618 hash-cons
pair hits, 13,941,000 vectors, 5,178,557 vector items, 97,859,419 string-pool
bytes, 1,323,032,467 arena-heap bytes, and zero arena-scope releases. Compared
with the preceding analyzer run, this used fewer pairs and less arena memory,
but the generic signal did not identify a `:budget/cells` cause. The analyzer
gate still fails; reclamation behavior and the reason for the signal remain
unresolved. No JVM, Clojure, CLJS/nbb, or Node dependency has been removed.

## 2026-10-17 current-source Native CLI closure recheck

Rebuilt the current Native CLI graph from an empty object directory with the
G3 Seed. The source resolver reported 54 modules, including the newly split
`frontend.helper-forms`; all 54 emitted KSO objects, linked into a 4,077,273
byte KSEED, and extracted `main` into a 4,077,240 byte AArch64 macOS image at
offset 4,048,192. `modules native_cli.kotoba --unpinned` then resolved the same
54-module graph. This is a clean Seed-built closure, not an Amu self-rebuild.

On that image, seven `.cljk`/`.kotoba` pairs covering `->`, `->>`, `as->`,
`cond->`, `cond->>`, a quoted-symbol `defn`, and a conditional temporary-name
collision returned equal HIR. A changed core expression returned
`semantic mismatch` with exit 65. These are HIR parity checks only; Definition
CID parity and the full surface corpus remain unverified.

The current `check-entry evaluator.kotoba --unpinned` returned exit 120 with
`SIGILL` at 219,430 pairs and 5,290,496 arena-heap bytes; no arena scope was
released. The current `check-entry frontend/analyze.cljk --unpinned` also
returned exit 120 with `SIGILL`, at 49,175,575 pairs, 1,081,673,009 arena-heap
bytes, 37,557,970 hash-cons pair hits, and zero scope releases. The configured
pair ceiling was 67,108,864, so this is a guest trap before the ceiling, not a
reported pair-budget exhaustion. These gates do not establish analyzer or
evaluator runtime parity.

The evaluator module and repaired constant-substitution source both compile as
part of this closure, but evaluator behavior has not passed its Native entry
gate. JVM/Clojure, CLJS/nbb, and Node build or launch dependencies remain; no
host route has been retired. Full project/build/verification CLI parity,
Definition CID parity, runtime execution parity, and an Amu-produced compiler
rebuild remain open.

## Corrected current-source Native CLI verification: 2026-10-17

Correction: the preceding r9 `check-entry evaluator.kotoba` and
`check-entry frontend/analyze.cljk` SIGILL readings omitted loader allow ID 3,
`:hash/sha256`, which schema identity evaluation needs. Those readings and the
claim that they demonstrated a pre-ceiling compiler trap are superseded by this
run. All checks below used loader IDs `3,35,37,38,39` and the approved Amu,
Kotoba, verifier, JSON, bytes, and scratch roots.

Fixed the Native schema route so `fail!` throws a schema refusal document
instead of returning `0`, checks `:document` maps with `document-kind`, and
checks a qualified keyword's printed document spelling rather than
`keyword-name` (which drops its namespace). A clean G3 Seed build from an empty
object directory compiled 55/55 Native CLI modules, including the current
`frontend.inference-signatures` module. The linked KSEED is 4,083,177 bytes;
the extracted AArch64 raw image is 4,083,144 bytes at entry offset 4,054,096,
SHA-256 `cbf0d964ef9f8a1a2dcaa4a418cd4244d643397a91c40c42b16b530aeb3f68b6`.
`modules native_cli.kotoba --unpinned` resolves the 55-module graph. This is a
G3 Seed-built Native CLI, not an Amu-produced selfhost rebuild.

On the clean image, a valid nonempty `:schemas` record table returned
`semantic ok`; a malformed descriptor was refused with exit 65. Native
`check-entry` returned `semantic ok` for `kotoba.form` (11,395,021 pairs,
11,883,394 vectors, 455,069,978 arena-heap bytes, one scope release) and
`kotoba.runtime.evaluator` (1,598,194 pairs, 1,535,751 vectors, 61,713,695
arena-heap bytes, one scope release). These are source-admission checks, not
runtime execution parity.

Seven paired `.cljk`/`.kotoba` HIR cases matched: `->`, `->>`, `as->`,
`cond->`, `cond->>`, a quoted symbol inside a valid `defn`, and a conditional
thread temporary-name collision. A changed core expression was rejected with
`semantic mismatch` and exit 65. This remains a small HIR corpus, not
Definition CID parity or full surface conformance.

With `KEXE_HASHCONS=21`, the corrected `check-entry frontend/analyze.cljk`
reached the fixed 67,108,864-pair ceiling and was refused with exit 120,
`:budget/cells :arena :pairs`, 58,312,975 hash-cons pair hits, 25,918,633
vectors, 15,684,230 vector items, 1,713,919,035 arena-heap bytes, and zero
scope releases. Analyzer arena reclamation and full analyzer admission remain
the immediate Native frontend blockers. No JVM/Clojure, CLJS/nbb, or Node
build/launch dependency has been retired. Definition CID parity, runtime
execution parity, full project/build/verification CLI parity, and an
Amu-produced compiler rebuild remain open.

## Native surface lowering and project-import parity: 2026-10-17

Added Native Kotoba lowering for the seven bounded `.cljk` forms `->`, `->>`,
`as->`, `cond->`, `cond->>`, `some->`, and `some->>`. The Native project linker
checks raw author forms for reserved `__kotoba_` names, lowers `.cljk` forms,
then rewrites imported alias calls; quoted data and `case` test literals remain
outside the reserved-name scan. This ordering lets `(-> 40 ops/inc)` link to
the same checked import stub as `(ops/inc 40)`.

An incremental G3 Seed build reused the r30 Native object closure, rebuilt the
syntax-sugar, project-linker, and Native frontend modules, and relinked and
extracted the Native CLI. The final r38 KSEED is 4,086,961 bytes; its extracted
AArch64 image is 4,086,928 bytes at entry offset 4,057,872. This was not a clean
from-source closure and was not an Amu-produced compiler rebuild.

The r37 CLI matched HIR for all nine committed positive/edge pairs in
`test/fixtures/selfhost/syntax-sugar/`. A multi-module project pair also matched
HIR for an imported alias used as a `->` step. `check-entry` refused a raw
reserved-prefix source and an incomplete `some->` with exit 65, while quoted
reserved-prefix data returned `semantic ok`. The r38 rebuild then recompiled
the Native frontend refusal-code mapping and rechecked project-alias parity and
reserved-source refusal. These results establish this Native source/HIR slice
only; Definition CID and runtime parity are still unverified. Full analyzer
admission remains blocked by the arena pair ceiling above, and JVM/Clojure,
CLJS/nbb, and Node build/launch dependencies remain in place.

## Native `.cljk` HIR conformance after private metadata fix: 2026-10-17

Using the r40 Native CLI image built by the G3 Seed from the retained r38
object closure (AArch64 image: 4,090,256 bytes, entry offset 4,061,200,
SHA-256 `8aded3086ec0416d616fdc7d0e0f1ff318759bbaeb4338e306771b80a0f3d239`),
the paired HIR corpus returned equality for all ten cases: the nine syntax-
sugar fixtures and the private-constant metadata fixture. The corpus covers
`->`, `->>`, `as->`, `cond->`, `cond->>`, `some->`, `some->>`, conditional
temporary-name collision, quoted-symbol `defn`, and `^:private` on a constant.

The refusal controls returned exit 65 for a raw reserved-prefix source, an
incomplete `some->`, and a deliberately mismatched core counterpart; quoted
reserved-prefix data remained accepted. The fixture files were copied into
the already-approved scratch root because the KEXE resource capability does
not include the repository's `test/` directory.

This is HIR equality/refusal evidence for the bounded surface corpus. It does
not establish Definition CID parity, runtime behavior parity, full project or
command parity, a clean current-source closure, or an Amu-produced compiler
rebuild. The full analyzer remains blocked by its pair-arena ceiling, and no
JVM/Clojure, CLJS/nbb, or Node build/launch dependency has been retired.
