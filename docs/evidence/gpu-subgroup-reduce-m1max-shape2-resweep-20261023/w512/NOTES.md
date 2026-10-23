# gpu-subgroup-reduce-m1max-shape2-resweep-20261023/w512 — the shape-2
flip-contract cell W = 512 re-swept (JUN-58)

Tick: amu-gpu chain (bot/amu-gpu-chain). Tracking: JUN-58 (the Apple vendor
row), parent JUN-55. One row of work: one MEASUREMENT -- the FIFTH and LAST
of the five shape-2 flip-set cells the honest LEFT named as the real
remainder ("The five shape-2 flip-set cells (W = 64/128/256/512/1024)
remain -- each its own MEASUREMENT row, one at a time"), the shape-1
series' closing order mirrored (256 -> 64 -> 128 -> 1024 -> 512). Run on
the only vendor this host has (Apple M1 Max).

## What this is a re-sweep OF

The shape-2 flip-set cell at W = 512: :baseline vs :subgroup-reduce on the
MSL route, Apple M1 Max (reported subgroup size 32), W = 512, n = 2^20 =
1,048,576 (no padded-lane tail), the three operators -- the exact cell
docs/evidence/gpu-subgroup-reduce-m1max-shape2-band-20261023/w512/
measured earlier today (commit 14b30b84, "the shape-2 flip-set band
measured"). This re-sweep ran a separate session the same day: fresh emit,
fresh xcrun metal/clang builds, 6 fresh processes. Same-day replication
across sessions -- NOT cross-day, and it does not claim temporal stability
beyond this day.

## What ran (real hardware, real emitted bytes)

- Same driver as every cell: `python3 scripts/gpu-subgroup-reduce-metal-measure.py
  --runs 6 --workgroup 512 --elements 1048576 --op-order sum,max,min
  --out docs/evidence/gpu-subgroup-reduce-m1max-shape2-resweep-20261023/w512`
  (explicit --out: the driver's named FOOTGUN -- default --out rewrites the
  historical run-log -- was avoided; the historical cell's record is
  untouched). The explicit --op-order sum,max,min matches the historical
  cell's fixed dispatch order (that record predates the op-order variant).
  Ran ~16:45 JST (run-log.txt / summary.md written by the driver).
- Device: Apple M1 Max; reported simdgroup size 32
  ([[threads_per_simdgroup]]) in every fresh process's header.
- Protocol: identical to the historical cell -- 6 fresh-process runs, 20
  interleaved paired samples per operator per run with alternating AB/BA
  order, 2 warmup submits per arm discarded, Metal GPU timestamps
  (GPUStartTime->GPUEndTime) around one reduce dispatch, verified
  read-back of the partials. run-log.txt: 720 sample lines (grep -c
  "^sample" = 720 = 6 x 3 x 2 x 20); verify ok=1 on every arm of every
  operator of every run (36 verify lines, 36 ok=1).
- Headers forwarded in all 6 runs (each of n=1048576 / workgroup=512 /
  op_order=sum,max,min appears 6 times in run-log.txt): the shape was
  forwarded, not defaulted-into-being-measured-silently.
- Emitted arms byte-identical to the historical cell: `diff -r shaders
  ../../gpu-subgroup-reduce-m1max-shape2-band-20261023/w512/shaders` is
  empty (the six emitted .metal sources).

## The numbers (summary.md, full tables; paired statistic = ADR-0358's)

| operator | paired ratio (median of 6 per-run ratios) | per-run ratios | historical shape-2 band w512 | shape-1 resweep w512 |
|---|---|---|---|---|
| sum | **1.202** | 1.188..1.205 | 1.200 | 1.197 |
| max | **1.195** | 1.186..1.197 | 1.192 | 1.194 |
| min | **1.197** | 1.187..1.201 | 1.187 | 1.193 |

**The W = 512 shape-2 cell reproduces in SIGN STRICTLY and its magnitude
within 0.010 of the historical cell -- and it CLOSES the shape-2 re-sweep
series.** The variant is slower in all 18 per-run ratios (3 operators x 6
fresh processes; the smallest is 1.186), the same sign as the historical
cell, the shape-1 re-sweep, and every cell of both re-sweep series. Sum
reproduces within 0.002 (1.202 vs 1.200), max within 0.003 (1.195 vs
1.192), min lands +0.010 above the historical band cell's median (1.197
vs 1.187) -- the same regime term the W = 64/128/1024 cells named, and
the min median straddles the regime boundary (see below).

## The regime term at the closing cell (named, not hidden)

The deviation tracks the GPU clock level again, and both sessions carry
it:

- This session's baseline per-run medians (summary.md): runs 1, 2, 4, 5, 6
  sit at the slow level (:sum 118.8k..119.3k gpu ns); run 3 dropped
  (:sum 61.9k, :max 72.5k, :min 96.1k). The run-3 ratios are the session's
  smallest for every operator (1.188 / 1.186 / 1.187); the slow-level runs
  give 1.191..1.205.
- The historical band cell's baseline per-run medians: :max/:min runs 1-3
  sat at fast/intermediate levels (37.5k..49.0k), :sum's run 4 at 96.1k --
  and its :min per-run ratios there are the cell's smallest (1.178..1.182).
  Its medians (1.200 / 1.192 / 1.187) mix regimes across runs.
- Consequence: the :min median comparison at this cell straddles the
  boundary (this session mostly slow, the historical cell partly fast),
  which is exactly why the +0.010 lands there while :sum/:max reproduce
  within 0.003. The SIGN is regime-invariant in both sessions (no ratio
  below 1.0 anywhere; 18/18 slower in both).

## Gate (this tick changed no code namespace)

- Scoped GPU gate (the 7 GPU-owned test namespaces, scratch runner
  gpu_scoped_gate.cljk, not in the repo), run this tick after the
  measurement: 88 tests / 7122 assertions / 0 failures, 0 errors.
- Full run-tests.cljk: RED AT BASE (aborts at namespace load with
  "Could not find namespace: kotoba.form", the W3 port path, outside this
  diff -- documented red at base in ADR-0362 and every prior tick record).
  No green full suite is claimed.

## Honest LEFT (the real remainder after this row)

- Both same-day re-sweep series are now COMPLETE: shape-1 (W = 64/128/256/
  512/1024) and shape-2 (W = 64/128/256/512/1024), 10 of 10 flip-set
  cells re-swept, each its own MEASUREMENT row. Every cell reproduced the
  flip sign strictly; magnitudes land within 0.017 of their historical
  cells (the widest is the shape-2 w1024 cell's +0.017), with the named
  regime term accounting for the spread.
- Cross-day replication of any cell needs a later-day run (a cron tick on
  another day), not more same-day sessions. Nothing here claims temporal
  stability beyond 2026-10-23.
- The regime term is now seen at every re-swept cell (W = 64/128/256/512/
  1024 in both shapes), and at this closing cell it quantifies as a
  session-mixing effect on the :min median. That strengthens the case for
  a regime-robust magnitude claim protocol -- PROPOSED, decided nowhere,
  own slice if taken.
- Record defect carried forward (named at w1024, not rewritten): the w64
  and w128 NOTES' LEFT lines carry an off-by-one COUNT. Committed evidence
  is not rewritten; this note is the correction thread.
- The blocked/absent-hardware rows stay exactly as the 2026-10-23
  correction record left them. No `:measured?` flag or honesty-lock code
  moves in this tick (evidence-only; the lock set is code and extends in
  its own slice).
