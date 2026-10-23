# JUN-58 -- the shape-2 flip-set band, and the shape-forwarding defect it
exposed (2026-10-23)

amu-gpu tick: ONE measurement row -- complete the second shape at the flip
set's widths (W = 64/128/512/1024 at n = 2^20) -- which first surfaced an
instrument defect, found and fixed in the same record (named, not hidden).

## The defect (the tick's primary finding)

`scripts/gpu-subgroup-reduce-metal-measure.m` parsed the shape argument
behind an exact argc gate: `if (argc == 4)`. That gate was CORRECT when it
was written (the driver passed `[workdir workgroup elements]`, argc 4 --
the shape-2 record's runs are unaffected, verified: its run-logs read
n=1048576). The op-order change (commit 3801a8ee) widened the argc
ceiling to 5 and made the driver ALWAYS pass five arguments
(`[workdir workgroup elements op-order]`) -- and left the elements gate at
`== 4`. From that commit on, every driver run silently ignored
`--elements` and ran the 1000003 default. Symptom, caught this tick: a
band run invoked with `--elements 1048576` wrote run-log headers reading
`n=1000003`.

Impact audit (verified from the records and git log):

- The shape-2 record (713be46b, w256/w32) PREDATES the defect; its logs
  read n=1048576. Unaffected.
- The op-order record (3801a8ee, w32-sum-last) ran under the defect, but
  its protocol wanted n = 1,000,003 (the default) -- its run-log reads
  n=1000003 BY DESIGN. Its numbers stand.
- This tick's first band run is the only mis-shaped run. It is preserved
  in full under `misshape-defect-20261023/` (w64/w128/w512/w1024, all
  n = 1,000,003): not deleted, superseded, and kept as the defect's
  record. Its numbers are shape-1 numbers (the same shape the wsweep /
  wsweep-low records already measured) and are NOT part of the shape-2
  band below.

Fix (this tick): `if (argc == 4)` -> `if (argc >= 4)`, with a comment
naming the defect and this record. Verified by re-running every cell of
the band: all four run-logs now read `n=1048576`. Residual exact-match
gates in the same main(): the op-order parse still keys on `argc == 5`
(harmless today -- the driver is the only caller and always passes 5) --
named, not changed.

## The band (shape 2, n = 2^20, this tick's measurement)

Four cells at the flip-set widths the shape-2 record had not run, same
host (Apple M1 Max, reported subgroup size 32), MSL arm, native-Metal
channel, the ADR-0358 sweep protocol (6 fresh processes, 20 interleaved
AB/BA pairs per operator per run, 2 warmup submits discarded, verified
read-back -- ok=1 x36 per cell). Commands, from the chain worktree root:

    python3 scripts/gpu-subgroup-reduce-metal-measure.py --runs 6 \
      --workgroup W --elements 1048576 \
      --out docs/evidence/gpu-subgroup-reduce-m1max-shape2-band-20261023/wW

Paired within-run median ratios (variant/baseline gpu-ns; the ADR-0358
statistic), shape 2 beside shape 1 (the prior records' per-op medians:
wsweep-low w64/w128, wsweep w256/w512/w1024):

| W     | shape-2 sum/max/min        | shape-1 sum/max/min        |
|-------|----------------------------|----------------------------|
| 64    | 1.224 / 1.220 / 1.220      | 1.221 / 1.216 / 1.202      |
| 128   | 1.239 / 1.235 / 1.230      | 1.246 / 1.243 / 1.242      |
| 256   | 1.227 / 1.223 / 1.220 (*)  | 1.220 / 1.217 / 1.217      |
| 512   | 1.200 / 1.192 / 1.187      | 1.196 / 1.195 / 1.197      |
| 1024  | 1.183 / 1.166 / 1.167      | 1.186 / 1.186 / 1.185      |

(*) from the shape-2 record (gpu-subgroup-reduce-m1max-shape2-20261023),
not this tick; included to show the completed set.

FINDING: the flip set's demotion basis replicates at the second shape at
EVERY width -- the variant is slower in all 15 width x operator cells of
the completed shape-2 band (1.166-1.239), the same sign and the same
penalty band as shape 1 at every width. The shape-2 record had shown this
for W = 256/32 only; the band closes the shape question for the whole
flip set: the narrowing's basis is not shape-dependent over the two
measured shapes. Whether the flip contract widens to shape 2 is its own
later decision (accelerator-variants' `apple-measured-n` still keys to
n = 1,000,003); that decision now has complete band evidence.

Named noise, not hidden: single per-run ratio spikes appear in both
records (this tick: w128 :max run 3 at 1.789; mis-shape w512 runs at
~1.28/1.65 equivalents in its own log) against otherwise tight per-run
lists (e.g. w1024's 1.163-1.168); the per-run lists are printed in full
in every summary.md and the medians are robust to single runs.

## What does NOT change (state honesty)

- No `:measured?` flag, no `:measured-cell` set, no selection behavior
  and no workgroup row (ADR-0355/0358) is touched by this tick. The diff
  is scripts/gpu-subgroup-reduce-metal-measure.m + docs/evidence.
- The W = 32 keep-:baseline decision and its honesty lock stand
  unchanged; this tick runs no W = 32 cell (the band is the flip set's
  widths only).
- The workgroup defaults in kotoba.compiler.accelerator-targets remain
  PROVISIONAL (:measured? false); nothing here is optimization evidence
  for them.
- UNMEASURED unchanged: the GLSL arm at every width (no wire-42
  execution route, ADR 0371 provider not implemented), every Apple
  device but this M1 Max, shapes beyond these two, and the
  NVIDIA/Intel/ARM/AMD variant rows.

## Gate (real runs, this host, kbb --backend sci)

  scoped (the 7 GPU-owned test namespaces, scratch runner
  gpu_scoped_gate.cljk, not in the repo), from the chain worktree root:

    kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)" \
      /Users/junkawasaki/.hermes/profiles/amu-gpu/cache/scratch/gpu_scoped_gate.cljk

    Ran 87 tests containing 6818 assertions.
    0 failures, 0 errors.

    scoped: 87 tests, 6818 passed, 0 failed, 0 errors

  (unchanged from before this tick -- this diff touches no test
  namespace.)

  full (kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)"
  run-tests.cljk): RED AT BASE, verified this tick, outside this diff --
  fails at NAMESPACE LOAD with "Could not find namespace: kotoba.form"
  (the W3 port path, documented red at base in ADR 0362 and every prior
  tick record). This diff touches no namespace on that path.

## LEFT (the next rows)

- The flip-contract widening decision: `apple-measured-n` keys to
  n = 1,000,003; shape 2 now has a complete flip-set band and the
  decision (own slice) has its evidence.
- The residual exact-match gate class in the harness's argv parsing
  (op-order `argc == 5`; harmless with today's single caller).
- The GLSL arm stays blocked on a wire-42 execution route (ADR 0371).
