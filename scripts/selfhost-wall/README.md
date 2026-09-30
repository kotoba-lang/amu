# Selfhost wall harness

Measures how many sources reachable from the `nbb/*_cli.cljk` entries pass `amu check` on the
Kotoba project route (docs/selfhost-status-20260930.md). Keep this in the repo: it once lived only
in `/private/tmp` and was lost.

    scripts/selfhost-wall/make-classpath.py <amu-root> /tmp/cp.txt      # worktrees named wt-<L>-<repo>
    scripts/selfhost-wall/reach-list.py <amu-root> /tmp/cp.txt <kotoba-lang> > /tmp/list.txt
    WALL_CP=/tmp/cp.txt WALL_K=<kotoba-lang> scripts/selfhost-wall/scan.sh /tmp/list.txt /tmp/scan.tsv

Numbers from this harness are Kotoba-route checks, not bootstrap (JVM/GraalVM/nbb) measurements.

## Definition identity, differentially

`kotoba.compiler.definition-identity` and `kotoba.kir.definition-identity` carry a Kotoba reading beside the
host code (`#?(:kotoba ..)`). The Kotoba reading takes the compiler's HIR / KIR as `:form/r` Forms
(`definitions hir kir catalog`, with the capability catalog as a Form map because `kotoba.sema` is not a
Kotoba module yet) and must produce the host's CIDs, byte for byte:

    KROOTS=<every classpath src dir, this repo's src, kotoba-lang/lang/compat, joined with :> \
    FILES=<root .cljk[,root .cljk]> SYNTH=1 STACK=30000 \
    scripts/selfhost-wall/run-verify.sh                      # ulimit -s 65500; nbb --stack-size=$STACK

`verify-definition-identity.cljs` analyzes each root on the project route (the repo's own definitions), asks the
host for the report, hands the same HIR/KIR to the Kotoba `definitions` running on the KIR interpreter (one link
for all cases) and compares the `name<TAB>cid` listing and the SCANNED line. `SYNTH=1` adds cycles (2 and 3
members, self recursion), shadowed binders, refused rows (unbridged wire id, `:abort`), integers beyond +-2^53,
f64 leaves and an f32 module. `probe-definition-identity.cljs` is the narrower probe over `canonical-hex`.

## Desugar differential (selfhost S3, desugar half)

`ds-diff.sh` runs the frontend's HOST `desugar-expr` against its Kotoba-route port (the `:kotoba` view of kotoba-sema's
`frontend.cljk`, extracted by `ds-gen.sh` with the `ds-names.txt` definitions, `ds-header.cljk` and `ds-tail.cljk`, then
run on the KIR interpreter) on every list form of the programs embedded in kotoba-sema's tests (`DS_TESTS`) and of the
`.kotoba` programs under `DS_EXTRA`. The guest answers `OK` (its form equals the host's), `DIFF <form>`, `ERR <message>`
(a refusal, compared with the host's), or `UNPORTED <head>` (counted as coverage, never compared).

    WALL_CP=<cp> WALL_K=<kotoba-lang> WALL_AMU_SRC=<this repo>/src WALL_NBB_DIR=<checkout with node_modules> \
    FRONTEND=<kotoba-sema>/src/kotoba/compiler/frontend.cljk DS_TESTS=<kotoba-sema>/test DS_EXTRA=<dir>:<dir> \
    DS_MAX=300 DS_TOTAL=1500 scripts/selfhost-wall/ds-diff.sh

`DS_LINES=<file>` runs the guest on case lines you write (`[{f 1} false (and a b) nil]`), `DS_NOGEN=1` skips regeneration.
`ds-names.txt` lists the definitions of the guest in source order; when a port adds a definition, add its name there.
