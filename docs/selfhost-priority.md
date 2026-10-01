# Selfhost is the top priority for the Amu compiler

Decision recorded 2026-09-29. It outranks new features, new targets and
benchmark publication.

## The goal

**The Amu compiler is a native executable produced by Amu, and building it
needs no JVM, no GraalVM and no Node.js.** (The same sentence is the goal in
`kotoba-lang/kotoba-lang` `docs/selfhost-native-binary.md`.)

"Kotoba is a native compiler" (Amu emits machine code) and "the Amu compiler
is a native binary" (a GraalVM Native Image folds a JVM-hosted Clojure program
into one file) are different claims. Only a compiler that Amu built from its
own `.cljk` sources satisfies the second one.

## Rules

1. **Selfhost first.** When work competes for time, the item that moves the
   compiler toward building itself wins. Walls on the selfhost scoreboard are
   fixed in the language / frontend / backend, not worked around in the
   compiler's source.
2. **Only a selfhost-built compiler is selfhost evidence.** A compiler
   executable counts only if Amu produced it. An executable built with
   GraalVM Native Image, run on the JVM, or run on Node/nbb is a *bootstrap or
   reference* artifact and is labelled that way wherever its numbers appear
   (README, reports, kotoba-lang.org).
3. **No GraalVM in the selfhost path.** `bin/build-native-image` and
   `scripts/build-native-image.py` are a bootstrap route kept for comparison.
   They are not acceptance evidence for selfhost and must not be presented as
   such.
4. **Benchmarks follow selfhost.** Embench and other compiler measurements are
   published as selfhost results only when taken with a selfhost-built
   compiler, on a quiet host, with the compiler binary hash recorded. Results
   from a bootstrap compiler are published as bootstrap-reference numbers,
   never as selfhost numbers.
5. **The language is not shaped by wasm32.** Selfhost walls are fixed in the
   language, frontend and native backends even when wasm32 has no lowering
   yet; wasm32 refuses the feature by name until it gains one
   (ADR 0354).
6. **Fail closed.** No JVM, GraalVM or Node fallback is added to make a
   selfhost stage pass. An unreachable file stays on the scoreboard as
   refused, with its reason.
7. **Port by rule, not by hand.** Selfhost porting edits are made with
   `amu refactor` (`kotoba refactor` in `kotoba-lang`): `plan -> apply --check
   -> verify`, differential on per-test outcomes, nbb/Kotoba only (no Python or
   JVM). Hand edits are for changes no rule covers, and then the rule is
   written or the reason recorded. A large namespace is parallelised with
   `refactor graph -> split -> one agent per module`. The `plan` counts and the
   `verify` result go in the commit message. Workflow: `docs/refactoring.md`.
7. **Refactor by AST.** Wall rewrites that recur are done with
   `amu refactor` rules (lossless, plan/apply/verify), not text edits; the
   refactoring tool is itself Kotoba-route code (ADR 0357).

8. **The product does not depend on nbb, Node or the JVM** (2026-10-01).
   nbb, Node, the JVM and GraalVM are bootstrap references only. The end
   state is an `amu` binary built by `amu` that runs `check`, `refactor`,
   `compile` and `kotoba ...` with no node/nbb/JVM process. nbb is not an
   acceptable resting place for the product; "it runs on nbb" is a bootstrap
   result. Inventory: `scripts/selfhost-wall/bootstrap-boundary.sh`
   (snapshot `docs/selfhost-bootstrap-boundary-20261001.md`); removal: stage
   S6 of `docs/selfhost-core-rewrite-plan-20260930.md`.
9. **New product-path code is Kotoba.** Code a user's `amu`/`kotoba` run reaches
   is written as `.cljk`/`.kotoba` with a `:kotoba` reading that passes
   `amu check`, never as nbb/Node/JVM-only code. Host-only code
   (`node:*`, `js/*`, `java.*`, `:import`) lives behind `#?(:cljs ...)` /
   `#?(:clj ...)` in files flagged `;; bootstrap-tooling` (first five lines) or
   under `scripts/`, `test/`, `bench/`, `tools/`. The wall harness and
   differential scripts are BOOTSTRAP-TOOL and may stay nbb/Python until the
   self-built compiler exists.
10. **Refuse new host dependencies.** A PR or commit that adds an nbb, Node or
    JVM dependency to the product path is refused (a new `bin/` host launcher,
    an `nbb/*_cli` entry without a `:kotoba` reading, an unguarded host
    require in `src/`, a new `#?(:kotoba nil ...)`). Compare
    `bootstrap-boundary.sh` PRODUCT counts before and after; they must not
    grow.
11. **What 100% means.** The `amu` binary built by `amu` itself runs the full
    `check`, `refactor` and `compile` on its own sources with zero
    node/JVM/nbb processes, verified by
    `scripts/selfhost-wall/no-host-processes.sh -- <command>` (an
    strace/dtruss execve trace; a missing tracer is a failure, not a pass).
    File counts, `amu check` OK counts and GraalVM binaries do not meet it.

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

## Embench

`bench/embench/` holds the Kotoba ports and the qualification runner. The
2026-09-29 Apple M4 numbers in `bench/embench/REPORT-20260929.md` were taken
with a GraalVM-built compiler (SHA-256
`59e3081256a116d3f50e864f44178bb35d38f5e07fd86420929c5ae13ad99ba0`). Under
rule 2 they are **bootstrap-reference numbers**. They are also not official
Embench scores.
