# Replication record — post-fix `:subgroup-reduce` device execution (M1 Max)

Three-process byte-identical replication of
`scripts/test-gpu-subgroup-reduce-exec-postfix.cljk` (the probe landed by
PR #1391, commit `0f6ed80b`), per the PR #1346 replication protocol. This
record is intentionally a separate file: `README.md` in this directory is
being added by the still-open PR #1391 and is not edited here, to keep the
two PRs conflict-free.

## Runs

All three runs are fresh processes executing the probe at worktree HEAD
`e7a5b164d6d1eedd126d5cb20892094a80e4fca8` (= `origin/main` at fork time of
both tick branches; the PROVENANCE line inside every log pins this head and
the emitter source sha256 `ce3d52dd…`). Command (each run):

```
kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)" \
    scripts/test-gpu-subgroup-reduce-exec-postfix.cljk
```

| run | where produced | bytes | sha256 |
| --- | --- | --- | --- |
| run-1.log | this branch, 2026-10-20 (re-run) | 2673 | `379ee1d244f9c474e107a68914de071621e07fc17cf1163064b6dc51b6a609ac` |
| run-2.log | this branch, 2026-10-20 (re-run) | 2673 | `379ee1d244f9c474e107a68914de071621e07fc17cf1163064b6dc51b6a609ac` |
| run-3.log | this branch, 2026-10-20 (re-run) | 2673 | `379ee1d244f9c474e107a68914de071621e07fc17cf1163064b6dc51b6a609ac` |

**3/3 byte-identical** (`shasum -a 256` + `diff`, verified 2026-10-20; all
three runs produced here with the INFO-recording probe, so each log now
carries the parsed wire-42 device identity (`INFO=Apple M1 Max|1.3.357|1024|1`)
on every case line). Every
run ends `GPU-SGRE-POSTFIX RESULT ran=14 failed=0 not-admitted=0`: all six
(W ∈ {64,256}) × (sum/max/min) shapes compiled as-emitted with zero rung
patches, and all 14 cases — including the four ±Inf extrema-identity
discriminators — read back bit-exact on the device.

## What this is evidence of, and of what it is not

- **Correctness only.** The probe prints no timing line and none may be
  claimed from it. No performance value is measured here; host load during
  the runs was high (other bots' `bin/amu check` batches concurrent).
- **Nothing flips `:measured?`** anywhere. Corrected description of the
  current state: the workgroup-default rows in
  `kotoba.compiler.accelerator-targets` are ALREADY `:measured? true` for
  nvidia/apple/intel/amd (ADR-0358 measurements); `:arm` and `:unknown`
  stay `:measured? false`. The VARIANT rows (warp-shuffle-reduce,
  subgroup-reduce) are the ones still UNMEASURED — this replication flips
  none of them (it is correctness evidence, not optimization evidence).
- **The cross-subgroup fold fix is UNEXERCISABLE on this host** (misfold
  needs W > 2·S²; S=32 on M1 Max ⇒ W > 2048, above KIR's 1024 ceiling).
  It targets small-S devices (Intel 8/16, Mali 4–32) — JUN-59/60 hardware
  absent. UNMEASURED there, with this reason.
- **Fixture regeneration stays OPEN** (the named follow-up of `4b7a1ccb`):
  the execution half is now replicated 3/3, but regenerating
  `test/fixtures/gpu/*.emitted.glsl` would break the pinned sign-probe
  chain (PR #1390 pins the pre-fix fixture bytes); the chain must carry its
  copies / re-pin first.

States: emission fix — implemented (`4b7a1ccb`); probe + this replication —
implemented and executed (PR #1391 + this PR); timing, cross-fold behavior
on small-S hardware, and any `:measured?` row — not measured.
