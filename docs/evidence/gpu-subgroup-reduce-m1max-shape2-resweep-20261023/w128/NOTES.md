# gpu-subgroup-reduce-m1max-shape2-resweep-20261023/w128 — the shape-2
flip-contract cell W = 128 re-swept (JUN-58)

Tick: amu-gpu chain (bot/amu-gpu-chain). Tracking: JUN-58 (the Apple vendor
row), parent JUN-55. One row of work: one MEASUREMENT -- the THIRD of the
five shape-2 flip-set cells the honest LEFT named as the real remainder
("The five shape-2 flip-set cells (W = 64/128/256/512/1024) remain -- each
its own MEASUREMENT row, one at a time"), following the shape-1 series'
order after the anchor (256 -> 64 -> 128 -> 1024 -> 512). Run on the only
vendor this host has (Apple M1 Max).

## What this is a re-sweep OF

The shape-2 flip-set cell at the TOP of the measured W band's penalty
side: :baseline vs :subgroup-reduce on the MSL route, Apple M1 Max
(reported subgroup size 32), W = 128, n = 2^20 = 1,048,576 (no padded-lane
tail), the three operators -- the exact cell
docs/evidence/gpu-subgroup-reduce-m1max-shape2-band-20261023/w128/ measured
earlier today (commit 14b30b84, "the shape-2 flip-set band measured", the
record that also fixed the shape-forwarding defect). This re-sweep ran a
separate session the same day: fresh emit, fresh xcrun metal/clang builds,
6 fresh processes. Same-day replication across sessions -- NOT cross-day,
and it does not claim temporal stability beyond this day.

## What ran (real hardware, real emitted bytes)

- Same driver as every cell: `python3 scripts/gpu-subgroup-reduce-metal-measure.py
  --runs 6 --workgroup 128 --elements 1048576 --op-order sum,max,min
  --out docs/evidence/gpu-subgroup-reduce-m1max-shape2-resweep-20261023/w128`
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
- Headers forwarded in all 6 runs (each of n=1048576 / workgroup=128 /
  op_order=sum,max,min appears 6 times in run-log.txt): the shape was
  forwarded, not defaulted-into-being-measured-silently -- a hardware run
  of the shape-forwarding fix (14b30b84's `argc >= 4`) with the shape it
  names.
- Emitted arms byte-identical to the historical cell: `diff -r shaders
  ../../gpu-subgroup-reduce-m1max-shape2-band-20261023/w128/shaders` is
  empty (the six emitted .metal sources).

## The numbers (summary.md, full tables; paired statistic = ADR-0358's)

| operator | paired ratio (median of 6 per-run ratios) | per-run ratios | historical shape-2 band w128 | shape-1 resweep w128 |
|---|---|---|---|---|
| sum | **1.233** | 1.216..1.258 | 1.239 | 1.244 |
| max | **1.228** | 1.209..1.235 | 1.235 | 1.243 |
| min | **1.233** | 1.224..1.239 | 1.230 | 1.234 |

**The W = 128 shape-2 cell REPRODUCES in sign and within 0.007 in ratio**
(sum 0.006 below, max 0.007 below, min 0.003 above the historical
medians). The variant is slower in all 18 per-run ratios (3 operators x 6
fresh processes), the same sign as the historical cell, the shape-1
resweep, and every cell of both re-sweep series. The paired penalty band
at this cell (1.228-1.233) remains the TOP of the measured band at both
shapes -- the same rank order the two bands' tables show (shape-2 band
w128 1.230-1.239, shape-1 1.242-1.246).

## The regime term at the band's top cell (named, not hidden)

The historical band cell straddled clock levels heavily INSIDE its six
runs (baseline per-run medians for :max/:min dip to 41.5k / 32.1k gpu ns
in runs 5-6 while :sum sat at ~100.2k throughout; the named single-run
:max spike at 1.789 sits in that record). This session sat at ONE level
throughout (all 18 per-run baseline medians 100.5k..103.8k ns, the slow
level) -- and the ratios still matched the historical cell's full-range
medians within 0.007. Contrast the shape-1 re-sweep w128 cell (the cell
that named the regime term as widest): 3 of its 6 processes sat in the
fast regime and its :min median landed 0.008 below the historical shape-1
cell. Here the unstraddled session's spread is sum 0.042 / max 0.026 /
min 0.015 in per-run ratios, all above 1, and the paired within-run ratio
held across sessions even though the clock regime did not.

## Gate (this tick changed no code namespace)

- Scoped GPU gate (the 7 GPU-owned test namespaces, scratch runner
  gpu_scoped_gate.cljk, not in the repo), run this tick after the
  measurement: transcript recorded in the tick's commit message.
- Full run-tests.cljk: RED AT BASE (aborts at namespace load with
  "Could not find namespace: kotoba.form", the W3 port path, outside this
  diff -- documented red at base in ADR 0362 and every prior tick record).
  No green full suite is claimed.

## Honest LEFT (the real remainder after this row)

- The shape-2 re-sweep series has 4 of 5 cells done (W = 256 anchor, W =
  64, W = 128 this tick). Remaining, each its own MEASUREMENT row, one at
  a time, in the shape-1 order: W = 1024, W = 512 (shape 2).
- Cross-day replication of any cell needs a later-day run (a cron tick on
  another day), not more same-day sessions. This cell and its historical
  source are same-day.
- The regime term now seen at both ends of the penalty band (W = 64, W =
  128 at both shapes) motivates a regime-robust magnitude claim protocol
  -- PROPOSED, decided nowhere, own slice if taken.
- The blocked/absent-hardware rows stay exactly as the 2026-10-23
  correction record left them.
