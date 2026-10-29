# gpu-subgroup-reduce-m1max-resweep-20261023/w1024 — the flip-set cell W = 1024 re-swept (JUN-58)

Tick: amu-gpu chain (bot/amu-gpu-chain). Tracking: JUN-58 (the Apple vendor
row; Linear AWAI-41), parent JUN-55 (AWAI-35). One row of work: one
MEASUREMENT -- the second cell of the re-sweep series the previous tick's
honest LEFT named as the real remainder ("Re-sweeps of the remaining
flip-set cells ... are each their own MEASUREMENT row, one at a time"),
run on the only vendor this host has (Apple Silicon).

## What this is a re-sweep OF

The flip-set cell at the TOP of the W band: :baseline vs :subgroup-reduce
on the MSL route, Apple M1 Max (reported subgroup size 32), W = 1024,
n = 1,000,003, the three operators -- the exact cell
docs/evidence/gpu-subgroup-reduce-m1max-wsweep-20261023/w1024/ measured
earlier 2026-10-23 (commit 7c80f56f, the W-sweep that closed the named
"W > 256 on M1 Max" UNMEASURED scope). Same-day replication across
sessions -- NOT cross-day, and it does not claim temporal stability beyond
this day.

## What ran (real hardware, real emitted bytes)

- Same driver as every cell: `python3 scripts/gpu-subgroup-reduce-metal-measure.py
  --runs 6 --workgroup 1024 --elements 1000003 --op-order sum,max,min
  --out docs/evidence/gpu-subgroup-reduce-m1max-resweep-20261023/w1024`
  (explicit --out: the driver's named FOOTGUN -- default --out rewrites the
  historical run-log -- was avoided; the historical cell's record is
  untouched). Ran ~14:50 JST.
- Device: Apple M1 Max; reported simdgroup size 32 ([[threads_per_simdgroup]])
  in every fresh process's header.
- Protocol: identical to the historical cell -- 6 fresh-process runs, 20
  interleaved pairs per operator per run with alternating AB/BA order,
  2 warmup submits per arm discarded, Metal GPU timestamps around one
  reduce dispatch, verified read-back of the partials (run-log.txt: 720
  sample lines = 6 x 3 x 2 x 20).
- Headers: all six runs print n=1000003, workgroup=1024,
  op_order=sum,max,min (run-log.txt lines 4-8, 138-142, ... 674-678). The
  shape and op-order were forwarded, not defaulted.

## The numbers (summary.md, full tables; paired statistic = ADR-0358's)

| operator | paired ratio (median of 6 per-run ratios) | per-run ratios | historical w1024 cell |
|---|---|---|---|
| sum | **1.185** | 1.184..1.187 | 1.186 |
| max | **1.177** | 1.167..1.185 | 1.186 |
| min | **1.172** | 1.167..1.186 | 1.185 |

**The cell REPRODUCES in sign and within 0.013 in ratio.** The variant is
slower in every one of the 18 per-run ratios (3 operators x 6 fresh
processes), the same sign as the historical cell and every other flip-set
cell. Sum reproduces to 0.001; max/min land 0.009/0.013 below their
historical medians -- see the regime caveat below.

## Regime caveat (reported as data, not hidden)

This session saw an INTRA-SESSION clock-regime shift larger than any
earlier cell: :max baseline per-run medians fall 128,292 -> 40,625 gpu ns
and :min 128,375 -> 40,625 gpu ns across the six processes (:sum ran
first and stayed at the ~128k level throughout). The paired ratio shows
mild regime dependence at this W -- the fast-regime runs carry 1.167-1.175
for :max/:min against the slow runs' 1.183-1.186 -- so the ~18.5% penalty
band shrinks by ~1.5% at the fast clock level. The sign never flips (all
18 per-run ratios above 1). The earlier regime-invariance claim ("the paired
within-run ratio held") is therefore exact in SIGN at W = 1024, but the
ratio's magnitude carries a small regime term here; a cross-regime verdict
protocol for W = 1024 (like the W = 32 one) is a PROPOSED design question,
decided nowhere.

## Determinism check (the emitter-identity guard)

`diff -r` of this run's six emitted sources against the historical w1024
cell's shaders/: BYTE-IDENTICAL (empty diff). Per the emit script's own
contract ("If a run of this script changes a file, an emitter changed"),
the two sessions compared the same emitted bytes.

Verified read-back (summary.md, verbatim): :max and :min bit-identical
between arms and against the CPU reference (977 partials = ceil(1000003/1024)
groups x 6 runs); :sum
arms within 6.10e-5 of each other and 3.27e-5 of the reference -- the same
values as the historical w1024 cell (rule 2's low-bit movement for f32
:sum, reported as data). 36 verify lines, ok=1 on every arm of every
operator of every run.

## What this is NOT (nothing upgrades)

- No `:measured?` flag moves, no `:measured-cell` set changes, no
  selection answer changes, no workgroup row (ADR-0355/0358) is touched.
  A re-sweep CORROBORATES a measured row; it does not extend the flip set.
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

- Scoped GPU gate (the 7 GPU-owned test namespaces): "Ran 88 tests
  containing 7122 assertions. 0 failures, 0 errors."
- Full run-tests.cljk: RED AT BASE at kotoba.form ("Could not find
  namespace: kotoba.form", the W3 port path, outside this diff), re-run
  this tick. No green full suite is claimed.

## Honest LEFT (the real remainder after this row)

- Re-sweeps of the remaining flip-set cells (W = 64/128/256, the shape-2
  cells) are each their own MEASUREMENT row, one at a time; this tick
  covered only the W = 1024 shape-1 cell.
- Cross-day replication of any cell needs a later-day run (a cron tick on
  another day), not more same-day sessions.
- The W = 1024 regime term (above) motivates an op-order-scoped regime
  check at this W -- PROPOSED, own slice if taken.
- The blocked/absent-hardware rows stay exactly as the 2026-10-23
  correction record left them.
