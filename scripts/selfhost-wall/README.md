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

`DS_LINES=<file>` runs the guest on case lines you write (`[{f #{1 2}} false (and a b) nil [] {} [] #{} false false]`: the function
names with their arities, the absence mode, the form, the expected answer, then what the host's side registries held after the
call: loop helpers, loop-helper shapes, lifted lambdas, requested closure dispatchers, the `uses-apply` and `uses-lazy` flags), `DS_NOGEN=1` skips
regeneration. `ds-names.txt` lists the definitions of the guest in source order; when a port adds a definition, add its name there.
`FRONTEND` is a `:`-separated list of files (the facade first, then the modules under `frontend/`; a later definition of a name
wins), since the frontend is split into modules.

The case line may carry an eleventh element, the callable-contract tables of the function the form sits in (`{:binds [params] :lexical {param contract}
:results {[name arity] contract} :params {[name arity] {index contract}} :expected contract}`, computed from the program's `defn` signatures the way `analyze`
does) which both sides bind (`*lexical-bindings*`, `*lexical-callable-contracts*`, `*function-callable-result-contracts*`, `*function-callable-param-contracts*`,
`*expected-callable-contract*` on the host, the env field `contracts` on the guest). A float the JVM-free reader hands over as `(f64-from-bits N)` (recognized
on the host by reader metadata) is carried as `(__ds_f64 N)` and revived as the float Form by the guest. The interpreter is given the hash ability (the bootstrap
host's SHA-256) because a structured closure family's name is a digest. `desugar-shape.py` prints the cycle's shape (`scc`), the Kotoba definitions outside
`ds-names.txt` (`leftovers`) and checks the host view of `desugar.cljk` against a revision (`hostview REV`); `module-overlay.py` stages one frontend module
for `amu check` before its dependencies are Kotoba-clean.

The state the host keeps in dynamic vars (`*pending-loop-helpers*`, `*loop-helper-shapes*`, `*pending-lambdas*`,
`*required-closure-dispatchers*`, `*uses-apply?*`, `*uses-lazy?*`, `*loop-counter*`, `*lambda-counter*`) is part of what a port must reproduce:
the host side of the differential binds each to a fresh atom/volatile, the guest returns the same data as `:fe/env` fields
(`helpers shapes lambdas dispatchers uses-apply uses-lazy`), and a case agrees only when the form AND all six are equal.
A case the guest cannot decide (a trap) is rerun alone and named `TRAP <message>`. `ds-corpus/*.kotoba` holds programs written
for the differential (loops, `dotimes`/`doseq`, `filter`/`reduce`/`map`/`fn`/..., with their refusals); add the directory to
`DS_EXTRA`. `DS_WHY=1` lists the cases dropped before comparison (an unprintable value, a case over 30000 bytes).

## Compiled Kotoba side (native by default), 2026-10-01

The Kotoba reading of a differential no longer has to run on the KIR interpreter on nbb. `guest-run.sh` compiles a module's
text->text entry with the amu native backend (aarch64 `.kexe`, run by `tools/kexe_loader.c`), falls back to wasm under node
(bootstrap) and then to the interpreter (bootstrap), printing and caching the refusal at each step:

    guest-run.sh [--native-only|--wasm-only|--interp] [--resolve] <guest.cljk> <entry> < cases > answers
    case-diff.sh [--native|--wasm|--interp] [--limit N]      # kotoba.string.case vs the host, all 1.1 M scalar values
    native-gaps.sh guests/*.cljk                              # per-function native refusals + operations the wasm emitter and verifier lack

`vx-diff.sh`, `ds-diff.sh` and `tm-diff.sh` resolve the mode first and take `--interp` to force the interpreter. Every
guest in `guests/` (and the generated ds guest) compiles natively since 2026-10-02; the gap list, the measured speeds and what is still
open are in `docs/selfhost-native-gaps-20261001.md`. `bytes-cap.sh` runs the `fs/app-data-bytes` wire end to end; `GUEST_POLICY_CAPS` /
`GUEST_GRANT` set the compile-time and run-time capability grants of `guest-run.sh`. Needs `WALL_CP`, `WALL_K`, `WALL_AMU_SRC`,
`WALL_NBB_DIR` as above; `GUEST_CACHE` (default `/tmp/kotoba-guest-cache`) holds compiled products and refusals.
