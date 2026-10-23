# gpu-subgroup-reduce-m1max-shape2-resweep-20261023/w1024 — the shape-2
flip-contract cell W = 1024 re-swept (JUN-58)

Tick: amu-gpu chain (bot/amu-gpu-chain). Tracking: JUN-58 (the Apple vendor
row), parent JUN-55. One row of work: one MEASUREMENT -- the FOURTH of the
five shape-2 flip-set cells the honest LEFT named as the real remainder
("The five shape-2 flip-set cells (W = 64/128/256/512/1024) remain -- each
its own MEASUREMENT row, one at a time"), following the shape-1 series'
order after the anchor (256 -> 64 -> 128 -> 1024 -> 512). Run on the only
vendor this host has (Apple M1 Max).

## What this is a re-sweep OF

The shape-2 flip-set cell at W = 1024: :baseline vs :subgroup-reduce on the
MSL route, Apple M1 Max (reported subgroup size 32), W = 1024, n = 2^20 =
1,048,576 (no padded-lane tail), the three operators -- the exact cell
docs/evidence/gpu-subgroup-reduce-m1max-shape2-band-20261023/w1024/
measured earlier today (commit 14b30b84, "the shape-2 flip-set band
measured", the record that also fixed the shape-forwarding defect). This
re-sweep ran a separate session the same day: fresh emit, fresh xcrun
metal/clang builds, 6 fresh processes. Same-day replication across sessions
-- NOT cross-day, and it does not claim temporal stability beyond this day.

## What ran (real hardware, real emitted bytes)

- Same driver as every cell: `python3 scripts/gpu-subgroup-reduce-metal-measure.py
  --runs 6 --workgroup 1024 --elements 1048576 --op-order sum,max,min
  --out docs/evidence/gpu-subgroup-reduce-m1max-shape2-resweep-20261023/w1024`
  (explicit --out: the driver's named FOOTGUN -- default --out rewrites the
  historical run-log -- was avoided; the historical cell's record is
  untouched). The explicit --op-order sum,max,min matches the historical
  cell's fixed dispatch order (that record predates the op-order variant).
- Device: Apple M1 Max; reported simdgroup size 32
  ([[threads_per_simdgroup]]) in every fresh process's header.
- Protocol: identical to the historical cell -- 6 fresh-process runs, 20
  interleaved paired samples per operator per run with alternating AB/BA
  order, 2 warmup submits per arm discarded, Metal GPU timestamps
  (GPUStartTime->GPUEndTime) around one reduce dispatch, verified
  read-back of the partials. run-log.txt: 720 sample lines (grep -c
  "sample" = 720 = 6 x 3 x 2 x 20); verify ok=1 on every arm of every
  operator of every run (36 verify lines, 36 ok=1).
- Headers forwarded in all 6 runs (each of n=1048576 / workgroup=1024 /
  op_order=sum,max,min appears 6 times in run-log.txt): the shape was
  forwarded, not defaulted-into-being-measured-silently -- a hardware run
  of the shape-forwarding fix (14b30b84's `argc >= 4`) with the shape it
  names.
- Emitted arms byte-identical to the historical cell: `diff -r shaders
  ../../gpu-subgroup-reduce-m1max-shape2-band-20261023/w1024/shaders` is
  empty (the six emitted .metal sources).

## The numbers (summary.md, full tables; paired statistic = ADR-0358's)

| operator | paired ratio (median of 6 per-run ratios) | per-run ratios | historical shape-2 band w1024 | shape-1 resweep w1024 |
|---|---|---|---|---|
| sum | **1.184** | 1.183..1.184 | 1.183 | 1.185 |
| max | **1.183** | 1.168..1.183 | 1.166 | 1.177 |
| min | **1.183** | 1.171..1.341 | 1.167 | 1.172 |

**The W = 1024 shape-2 cell reproduces in SIGN STRICTLY and its magnitude
splits by clock regime.** The variant is slower in all 18 per-run ratios
(3 operators x 6 fresh processes; the smallest is 1.168), the same sign as
the historical cell, the shape-1 re-sweep, and every cell of both
re-sweep series. :sum reproduces within 0.001 (1.184 vs 1.183). :max/:min
land +0.017 / +0.016 ABOVE the historical band cell's medians -- the
largest cross-session deviation in the two re-sweep series so far (prior
cells: 0.003..0.013) -- and within 0.006 / 0.011 of the shape-1 re-sweep
w1024 cell (1.177 / 1.172).

## The regime term at the band's interior cell (named, not hidden)

The :max/:min deviation tracks the GPU clock level; the ratio is
regime-split at this cell, and the split is visible inside this one
session's six runs:

- This session's baseline per-run medians (summary.md): :sum sat at the
  slow level in all 6 runs (132.0k..132.4k gpu ns). :max/:min sat at the
  same slow level in runs 1-3 (131.9k..132.4k) and dropped to intermediate
  levels in runs 4-6 (:max 132.0k -> 68.6k -> 106.5k; :min 93.8k -> 68.4k
  -> 81.1k).
- The historical band cell's baseline per-run medians: :sum at the same
  slow level (132.0k..132.3k -- and its :sum ratio 1.183 matches this
  session's 1.184 within 0.001), :max/:min at the fast level (~41.7k..41.9k,
  run 1 :max 54.4k) with ratios 1.166 / 1.167.
- Slow-level runs here give per-run ratios 1.183..1.184; the
  intermediate/fast-level runs here give 1.168..1.174 (runs 5-6) --
  bracketing the historical fast-level cell's per-run range (1.163..1.175
  :max, per the band record's lists). The paired within-run ratio held in
  SIGN across every regime; its MAGNITUDE moves with the clock level
  (slow ~ 1.183-1.184, fast ~ 1.166-1.174).
- Named single-run outlier: run 4's :min ratio 1.341 -- its baseline
  dropped to 93.8k while its variant stayed at 125.7k, an INSIDE-RUN
  straddle (the same phenomenon the shape-2 band w128 cell named). It is
  data in the record, not discarded.

Host regime, recorded as data: load averages 95/112/105 (1/5/15 min)
before the run, 92/109/104 after -- a chronic Virtualization.framework VM
at 488% CPU (pid 14239, running since ~17 min after boot, so also present
during the historical cells) plus one transient other-session unittest run
at ~97% during this measurement. The primary timer is GPU timestamps with
interleaved paired sampling; host submit->completion ns is secondary and
carries no claim here.

## Gate (this tick changed no code namespace)

- Scoped GPU gate (the 7 GPU-owned test namespaces, scratch runner
  gpu_scoped_gate.cljk, not in the repo), run this tick after the
  measurement: 88 tests / 7122 assertions / 0 failures, 0 errors.
- Full run-tests.cljk: RED AT BASE (aborts at namespace load with
  "Could not find namespace: kotoba.form", the W3 port path, outside this
  diff -- documented red at base in ADR-0362 and every prior tick record).
  No green full suite is claimed.

## Honest LEFT (the real remainder after this row)

- The shape-2 re-sweep series has 4 of 5 cells done (W = 256 anchor, W =
  64, W = 128, W = 1024 this tick). Remaining, its own MEASUREMENT row:
  W = 512 (shape 2) -- the last cell.
- Record defect named, not edited: the w64 and w128 NOTES' LEFT lines
  carry an off-by-one COUNT ("3 of 5 cells done" naming 2, "4 of 5" naming
  3). The named cells were right in both; the ratio was not. Committed
  evidence is not rewritten -- the correction is this note, and this
  cell's "4 of 5" above counts the four cells it names.
- Cross-day replication of any cell needs a later-day run (a cron tick on
  another day), not more same-day sessions. This cell and its historical
  source are same-day.
- The regime term is now seen at the band's interior as well as its ends,
  and at this cell it QUANTIFIES as a slow/fast ratio split (~1.183-1.184
  vs ~1.166-1.174). That strengthens the case for a regime-robust
  magnitude claim protocol -- PROPOSED, decided nowhere, own slice if
  taken.
- The blocked/absent-hardware rows stay exactly as the 2026-10-23
  correction record left them.
