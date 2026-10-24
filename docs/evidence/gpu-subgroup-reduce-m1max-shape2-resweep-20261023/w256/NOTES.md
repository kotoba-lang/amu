# gpu-subgroup-reduce-m1max-shape2-resweep-20261023/w256 — the shape-2
flip-contract anchor cell re-swept (JUN-58)

Tick: amu-gpu chain (bot/amu-gpu-chain). Tracking: JUN-58 (the Apple vendor
row), parent JUN-55. One row of work: one MEASUREMENT -- the FIRST of the
five shape-2 flip-set cells the honest LEFT named as the real remainder
("The five shape-2 flip-set cells (W = 64/128/256/512/1024) remain -- each
its own MEASUREMENT row, one at a time"), starting with the anchor the
shape-1 series also started from. Run on the only vendor this host has
(Apple M1 Max).

## What this is a re-sweep OF

The shape-2 flip-contract anchor cell: :baseline vs :subgroup-reduce on the
MSL route, Apple M1 Max (reported subgroup size 32), W = 256, n = 2^20 =
1,048,576 (no padded-lane tail), the three operators -- the exact cell
docs/evidence/gpu-subgroup-reduce-m1max-shape2-20261023/w256/ measured
earlier today (commit 713be46b, "the second shape measured"). This re-sweep
ran ~15:50 JST the same day as a fully separate session: fresh emit, fresh
xcrun metal/clang builds, 6 fresh processes. Same-day replication across
sessions -- NOT cross-day, and it does not claim temporal stability beyond
this day.

## What ran (real hardware, real emitted bytes)

- Same driver as every cell: `python3 scripts/gpu-subgroup-reduce-metal-measure.py
  --runs 6 --workgroup 256 --elements 1048576 --op-order sum,max,min
  --out docs/evidence/gpu-subgroup-reduce-m1max-shape2-resweep-20261023/w256`
  (explicit --out: the driver's named FOOTGUN -- default --out rewrites the
  historical run-log -- was avoided; the historical cell's record is
  untouched). The explicit --op-order sum,max,min matches the historical
  cell's fixed dispatch order (that record predates the op-order variant).
- Device: Apple M1 Max; reported simdgroup size 32 ([[threads_per_simdgroup]])
  in every fresh process's header.
- Protocol: identical to the historical cell -- 6 fresh-process runs, 20
  interleaved paired samples per operator per run with alternating AB/BA
  order, 2 warmup submits per arm discarded, Metal GPU timestamps
  (GPUStartTime->GPUEndTime) around one reduce dispatch, verified read-back
  of the partials. run-log.txt: 720 sample lines (grep -c "sample" = 720 =
  6 x 3 x 2 x 20); verify ok=1 on every arm of every operator of every run
  (36 verify lines, 36 ok=1).
- Headers forwarded in all 6 runs (each of n=1048576 / workgroup=256 /
  op_order=sum,max,min appears 6 times in run-log.txt): the shape was
  forwarded, not defaulted-into-being-measured-silently -- this is a
  hardware run of the shape-forwarding fix (14b30b84's `argc >= 4`) with
  the shape it names.

## The numbers (summary.md, full tables; paired statistic = ADR-0358's)

| operator | paired ratio (median of 6 per-run ratios) | per-run ratios | historical shape-2 anchor |
|---|---|---|---|
| sum | **1.226** | 1.205..1.228 | 1.227 |
| max | **1.225** | 1.220..1.227 | 1.223 |
| min | **1.225** | 1.212..1.226 | 1.220 |

**The shape-2 anchor REPRODUCES in sign and within 0.005 in ratio** (sum
0.001 below, max 0.002 above, min 0.005 above the historical medians). The
variant is slower in all 18 per-run ratios (3 operators x 6 fresh
processes), the same sign as the historical cell and every shape-1 cell.
The paired penalty band at the anchor (1.225-1.226) is the same ~22% the
historical cell measured (1.220-1.227).

## Regime caveat (reported as data, not hidden)

This session ran mostly at ONE clock level (baseline per-run medians
~107.4-108.3k gpu ns; run 4 sat slightly higher at ~111.2-111.4k across all
three operators), against the historical shape-2 anchor, whose :max/:min
processes straddled three clock levels (~107k / ~66k / ~34-44k baseline).
The absolute medians therefore differ between sessions at the fast levels
while the paired within-run ratio held in both -- the same regime
robustness of the paired statistic the whole series has relied on. The min
row's +0.005 reproduction gap sits in the same small regime term the
shape-1 re-sweep cells (W = 64/128/512/1024) named; the sign never flips
(all 18 per-run ratios above 1, lowest 1.212).

## Determinism check (the emitter-identity guard)

`diff -r` of this run's six emitted sources against the historical
shape-2 anchor's shaders/: BYTE-IDENTICAL (empty diff). Per the emit
script's own contract ("If a run of this script changes a file, an emitter
changed"), the two sessions compared the same emitted bytes.

Verified read-back (summary.md, verbatim): :max and :min bit-identical
between arms and against the CPU reference in every run; :sum arms within
3.05e-5 of each other and 1.58e-5 of the reference in every run -- the
same low-bit class as the historical shape-2 anchor at W = 256 (3.05e-5
arm-vs-arm, the arms regroup differently at W > S), rule 2's low-bit
movement for f32 :sum, reported as data.

## What this is NOT (nothing upgrades)

- No `:measured?` flag moves, no `:measured-cell` set changes, no selection
  answer changes, no workgroup row (ADR-0355/0358) is touched. A re-sweep
  CORROBORATES a measured row; it does not extend the flip set.
- Not cross-day, not a new shape, width, device or route. UNMEASURED scope
  is unchanged: shapes beyond the two contract cells; every Apple device
  but this M1 Max; W = 32 as a verdict (it is a decision); the GLSL arm
  beyond its LABELED BOOTSTRAP record (blocked on a wire-42 execution
  route, ADR 0371); the NVIDIA/Intel/ARM/AMD variant rows entirely (no
  hardware).
- The channel is the native-Metal harness (ADR-0360 question (1)'s
  2026-10-23 decision admits it as contract-satisfying FOR THE MSL ARM);
  wire 42 still executes SPIR-V through Vulkan only.

## Gate (this tick changed no code namespace)

- Scoped GPU gate (the 7 GPU-owned test namespaces, scratch runner
  gpu_scoped_gate.cljk, not in the repo), run this tick after the
  measurement: "Ran 88 tests containing 7122 assertions. 0 failures,
  0 errors."
- Full run-tests.cljk: RED AT BASE, re-run this tick (real transcript:
  aborts at namespace load with "Could not find namespace: kotoba.form",
  the W3 port path, outside this diff -- documented red at base in ADR 0362
  and every prior tick record). No green full suite is claimed.

## Honest LEFT (the real remainder after this row)

- Four shape-2 flip-set cells remain (W = 64/128/512/1024) -- each its own
  MEASUREMENT row, one at a time; this tick covered only the shape-2
  W = 256 anchor (1 of 5).
- Cross-day replication of any cell needs a later-day run (a cron tick on
  another day), not more same-day sessions.
- The regime term named at W = 64/128/512/1024 shape-1 motivates a
  regime-robust magnitude claim protocol -- PROPOSED, decided nowhere,
  own slice if taken.
- The blocked/absent-hardware rows stay exactly as the 2026-10-23
  correction record left them.

CORRECTION NOTE (2026-10-24, later tick): true when written
(2026-10-23, before the 17:07 decision); the state moved the same day
-- the regime-robust magnitude claim protocol is DECIDED (ADR-0360
Amendment 2026-10-23, commit 52a8f0634; ACCEPTED DESIGN ONLY) and
binds the :simdgroup-reduce family by ADR-0373's composition (commit
7fcaa9406). Do not copy the row forward as current state. Census:
docs/evidence/gpu/regime-protocol-leftrow-stale-20261024.txt.
