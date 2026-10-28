# Seed backend in the big route: `amu compile --backend seed` (2026-10-03, agent INT2)

Decision record: ADR 0365 (amu) and kotoba-verifier ADR 0052. This page holds the measurements. Every run below was on
this Mac while it was loaded (load average recorded per run). No timing here is a result.

## What runs

```
amu compile <src> --target aarch64-macos --backend seed --seed <packaged seed> --output x.kexe [--fuel n]
  nbb frontend -> effect-row admission -> ir/lower (oracle) -> sealed KIR (:program)
  -> seed compile-kir <work>/program.kir --output <work>/program.kseed [--metered]     (process/spawn shape, bootstrap)
  -> accepted: artifact :code/:exports from the container, :emitter {:name :kotoba-seed :sha256 .. :route :bootstrap-process}
     refused/failed: machine_ir, report :backend {:emitted :machine-ir :fallback {..}}
  -> provenance (:emitter under its seal) -> compile-time verifier re-emits WITH THE SEED and compares bytes
amu extract-native x.kexe --symbol s --output r.bin --seed <seed>        (verifier re-emits with the seed again)
amu verify-output-set x.kexe --seed <seed>                               (output admission + the same re-emission)
```

Files: src/kotoba/compiler/nbb/seed_backend.cljk (new, `;; bootstrap-tooling`), src/kotoba/compiler/nbb/cli.cljk
(selector, report, caches, extract-native), src/kotoba/compiler/provenance.cljk (`:emitter`),
src/kotoba/compiler/nbb/output_admission.cljk + output_set_cli.cljk (`:emitter`, `--seed`), kotoba-verifier
src/kotoba/verifier.cljk (`:emitter`, `*emitters*`). Harness: scripts/seed-backend/{build-wrapper.sh,
amu-seed-wrapper.c, test.sh, embench.sh}. Unit tests: test/kotoba/compiler/seed_backend_test.cljk (amu, 6 tests),
test/kotoba/verifier_emitter_test.cljk (verifier, 6 tests).

Seed under test: be8898af (675,512 B, the r6c-kir rung's fixed point, build/seedfix-g/seed-1.bin), packaged by
scripts/seed/package.sh with scope repo:tooldir:/private/tmp:/tmp. The artifact records the sha256 of the PACKAGED
command (loader + code + scope), because that is the program that runs; build-wrapper.sh's wrapper.info ties it to
the code sha256.

## Classpath (no pin moved)

bin/amu resolves kotoba-verifier from the lock pin a560612e, which has no `*emitters*`. The seed route is therefore
measured with the lock closure in which only kotoba-verifier is taken from /private/tmp/wt-D-kotoba-verifier
(build-wrapper.sh; the same substitution the selfhost-wall harness makes). bin/amu itself, with `--backend seed`, does
not run the seed: it falls back with "the loaded kotoba-verifier has no emitter registry" and writes the default bytes
(test T7). Advancing the pin is the owner's step.

## Results

### Embench, full pipeline (scripts/seed-backend/embench.sh, the unchanged run_native_qualification.py, --samples 1)

RECORD: see the "record" section at the end (clean worktree run). First run (dirty worktree, 2026-10-03 19:52-20:00,
load 22.3 -> 31.6):

| measure | result |
|---|---|
| runner (compile, extract-native with seed re-emission, kexe-benchmark result 1) | **19/19 correct**, exit 0 |
| artifacts emitted by the seed (report `:emitted :kotoba-seed`, artifact records `:emitter`) | **19/19**, 0 fallbacks |
| compile-time verifier, re-emitting with the recorded seed | 19/19 accepted (the compile does not write without it) |
| extract-native verifier, re-emitting with the seed | 19/19 accepted (runner exit 0) |
| `verify-output-set --seed` | 13/19 ACCEPT; 6 refused `:native-decode` |
| `verify-output-set` without `--seed` | the same 13 refused by name: "recorded emitter is not available to this verifier" |

The 6 `:native-decode` refusals (aha-mont64, edn, huffbench, picojpeg, tarfind, wikisort) are not the seed's: the
default (machine_ir) artifact of edn is refused the same way (output_admission decodes with kotoba.lang.edn, which
refuses integers beyond 2^53-1; a documented property of that file).

The runner's report says `"javascript_node_dependency": false` and `"jvm_dependency": false`. That is `otool -L` of
the Mach-O wrapper only. node + nbb ARE in the process tree (no JVM is). embench.sh writes
`seed-backend-labels.json` next to the report with the true labels.

### End-to-end checks (scripts/seed-backend/test.sh): 16/16 PASS (load 30-36)

T1 no flag: kexe and provenance byte-identical to bin/amu's for crc32, edn, examples/recursive-tree; T2 crc32 by the
seed: report, artifact and provenance carry the same `:emitter` with the seed's sha256, the artifact code is
byte-identical to `seed compile-kir` of the artifact's own `:program`, test-crc32 returns 1; T3 f64_add: refusal E2101
falls back, kexe + provenance identical to the default build; T4 typed-closure-parameters with `--fuel`: E1203
(documents under `--metered`) falls back; T5 verify-output-set: `--seed` accepts, no seed and a different seed program
are refused by name; T6 `--backend llvm` and `--backend seed` without a seed are usage errors; T7 bin/amu (pinned
verifier): fallback with the reason, default bytes.

Metered build (crc32 `--fuel 16777216`): seed artifact consumes 1,028 fuel, machine_ir artifact 1,028.

### Unit tests

amu (nbb): seed_backend_test + provenance_portable_test 11 tests, 54 assertions, 0 failures. test/nbb
native-fuel-diagnostics, compile_cache, native-value-abi: pass. kotoba-verifier nbb suite: 50 tests, the 6 new pass;
18 failures in `a-non-literal-count-is-still-refused` are identical on HEAD without this change (same classpath).

## Findings and open risks

- **Silent export drop in `compile-kir` (filed in seed/CONTRACT-REQUESTS.md).** typed-closure-parameters' container
  exports 1 of the KIR's 7 exports (document-typed parameters, closures). kir-backend-diff.sh compares arity-0 exports
  only and did not see it. The selector treats a missing export as a failure and falls back, so no artifact lacks an
  export, but a refusal by name in the seed would be better.
- The registry trusts the caller's binding of sha256 -> program. amu hashes the seed and runs a private copy written
  from the hashed bytes; nothing stronger (signatures) is involved.
- `amu run`, `amu verify` and `sign` paths other than output sets do not take `--seed`: they refuse seed artifacts.
- Seed exports carry no `:length`.
- Each seed-backed compile runs the seed twice (emit + verifier re-emission); the verdict cache replays the second.
- The route is bootstrap-only by design: node + nbb + a spawned seed. The in-process link (seed modules in the amu
  image) is the next step and removes seed_backend.cljk.

## Record (clean worktree, 2026-10-03 20:03-20:2x)

Clean detached worktree of amu 0a77f161d (dirty 0; node_modules symlinked), kotoba-verifier worktree HEAD 4be5856
(dirty 0), seed code be8898af, packaged seed command df610454 (scope = that worktree, its tool dir, /private/tmp, /tmp),
wrapper a4b525fb, classpath 103 entries (lock closure, verifier from the worktree). Load 33.5 at the start, 60.6 at the
end of the Embench run, 71.5 at the end of test.sh: correctness only, no timing.

- `scripts/seed-backend/embench.sh`: exit 0. Runner 19/19 correct (exit 0), 19/19 emitted by the seed, 0 fallbacks,
  compile-time and extract-native re-emission with the seed 19/19; verify-output-set --seed 13 ACCEPT + 6
  `:native-decode` (same 6 ports as the first run, a property of output admission, not of the seed); without --seed
  the 13 are refused by name; 0 seed-related refusals. Per port: docs/records/seed-backend-embench-20261003.tsv.
- `scripts/seed-backend/test.sh`: 16/16 PASS.
- Reproduce: `SB_SEED_BIN=<be8898af seed-1.bin> zsh scripts/seed-backend/embench.sh <out>` then
  `zsh scripts/seed-backend/test.sh <out>/tool`, after `bin/amu compile` once (fills the lock-classpath cache).
