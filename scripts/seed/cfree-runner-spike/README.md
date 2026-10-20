# JUN-29: C-free seed runner — spike (interpreter route), 2026-10-20

Minimal, measured demonstration that the seed runner's execution model
(read -> check -> evaluate) runs with **no C loader**. Landed so the JUN-29
spike phase is durable and reproducible.

## What is measured here

1. **Runner graph resolves and builds.** `spike_cfree_runner.kotoba` requires
   `kotoba.runtime.native-interpreter` (the Kotoba-native integer
   interpreter). The `modules` subcommand resolves the require graph to 20
   modules (form / form-transform / syntax-sugar / decimal-bits /
   kotoba-reader / form-pipeline / evaluator-collections / evaluator-strings /
   value-semantics / evaluator-builtins / evaluator / policy / reader-depth /
   embedded-native / raw-memory / bytes / wasm-bytes / runtime /
   native-interpreter / the entry). All 20 compile with `--emit-module`, link
   to a container, and extract to a raw image.

   Measured (2026-10-20, from landed sources):
   `containerBytes 442535`, `containerSha256
   7f525dfdae89ba1777c6804edca0e826054dbdd480b2da5eca9023a7f5aefb51`,
   `mainOffset 434032`, image `442504` bytes. The build is deterministic:
   the same container sha256 results from worktree and landed inputs.

2. **The extracted image is a raw image, not an OS executable.** `file`
   answers `data`; exec yields `Exec format error`. Running it needs a
   trampoline (load image, enter `mainOffset`) — which is exactly the
   kexe-loader mechanism role. This is the empirical version of the
   thin-shim/interpreter fork: the runner *logic* builds; the raw-image
   execution mechanism is the remaining C-free work.

3. **The interpreter route runs today with zero C.** The same evaluation
   semantics run through `kotoba.runtime/run` on the host with no loader and
   no trampoline (sanctioned JVM final-means route):

   ```
   clojure -M -i tools/cljk_loader.cljk -i host_proof.cljk   # in kotoba repo
   ```

   `host_proof.cljk` (see below) reads `fixture_add.kotoba`
   (`(defn main [] :i64 (+ 21 21))`) with `runtime/read-file`, statically
   checks it (`launcher/safe-analyzer-fact-classification` +
   `launcher/source-plan`), and evaluates it with `runtime/run`. Measured
   output: `:run-ok true`, `:run-value 42`, `:run-problems nil`.

## Enabling fix landed on the way

`kotoba.bytes`' base64 family failed the typed closure compile (E2104 in
`encode-64`/`decode-64`) because of the known dual-flavour unannotated
parameters. Fixed via kotoba-lang/bytes PR #1 (5 functions annotated with the
existing `#?@(:kotoba [...] :default [...])` convention; `:default` paths
unchanged; suite 21 tests / 140 assertions / 0 failures). This unblocks the
runtime graph for every consumer.

## Reproducing

```
CFREE_LOADER=<kexe-loader> CFREE_IMAGE=<G1.bin> CFREE_OUT=<new-outdir> \
CFREE_ROOTS=<src-root>[:<src-root>...] \
  python3 scripts/seed/cfree-runner-spike/build_cfree_runner_spike.py
```

Source roots must cover the runtime module set (the spike used the closure
overlay tree, the kotoba repo `src`, `kotoba-lang/kotoba-lang/src`, `osaho`,
`artifact-core`, `kotoba-hir`, `coll`, `kotoba-text`, `bytes`, `error`,
`grammar`, plus this directory). The builder refuses duplicate namespace
resolution across roots (E6024), so each namespace must resolve from exactly
one root.

The host-route proof script (`host_proof.cljk`, not in this PR) is three
calls as above; the fixture is one line.

## What remains (JUN-29 product phase)

- The raw-image execution mechanism without the C loader: either the
  interpreter-route runner form (run the closure's forms through the
  evaluator directly — no trampoline) or a minimal mechanism-only trampoline
  under the AGENTS.md "mechanism layer" exception.
- The runner's native-image product form (the host runtime itself compiled
  to a standalone image) and the seed ceremony format update it implies.
