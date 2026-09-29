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
