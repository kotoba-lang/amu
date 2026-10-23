# gpu-subgroup-reduce-m1max-resweep-20261023/w64 — the flip-set cell W = 64 re-swept (JUN-58)

Tick: amu-gpu chain (bot/amu-gpu-chain). Tracking: JUN-58 (the Apple vendor
row), parent JUN-55. One row of work: one MEASUREMENT -- the third cell of
the re-sweep series the honest LEFTs named as the real remainder
("Re-sweeps of the remaining flip-set cells ... are each their own
MEASUREMENT row, one at a time"), run on the only vendor this host has
(Apple M1 Max).

## What this is a re-sweep OF

The flip-set cell at the BOTTOM of the measured W band's penalty side:
:baseline vs :subgroup-reduce on the MSL route, Apple M1 Max (reported
subgroup size 32), W = 64, n = 1,000,003, the three operators -- the exact
cell docs/evidence/gpu-subgroup-reduce-m1max-wsweep-low-20261023/w64/
measured earlier 2026-10-23 (the low band that closed the named
"MSL W = 32..128 on M1 Max" UNMEASURED scope). Same-day replication
across sessions -- NOT cross-day, and it does not claim temporal stability
beyond this day.

## What ran (real hardware, real emitted bytes)

- Same driver as every cell: `python3 scripts/gpu-subgroup-reduce-metal-measure.py
  --runs 6 --workgroup 64 --elements 1000003 --op-order sum,max,min
  --out docs/evidence/gpu-subgroup-reduce-m1max-resweep-20261023/w64`
  (explicit --out: the driver's named FOOTGUN -- default --out rewrites the
  historical run-log -- was avoided; the historical cell's record is
  untouched). Ran ~15:00 JST.
- Device: Apple M1 Max; reported simdgroup size 32 ([[threads_per_simdgroup]])
  in every fresh process's header.
- Protocol: identical to the historical cell -- 6 fresh-process runs, 20
  interleaved paired samples per operator per run with alternating AB/BA
  order, 2 warmup submits per arm discarded, Metal GPU timestamps
  (GPUStartTime->GPUEndTime) around one reduce dispatch, verified
  read-back of the partials. run-log.txt: 720 sample lines = 6 x 3 x 2 x
  20 (grep -c "sample" = 720); verify ok=1 on every arm of every operator
  of every run (36 verify lines).
- Headers forwarded in all 6 runs (each of n=1000003 / workgroup=64 /
  op_order=sum,max,min appears 6 times in run-log.txt): the shape and the
  op-order were forwarded, not defaulted-into-being-measured-silently.

## The numbers (summary.md, full tables; paired statistic = ADR-0358's)

| operator | paired ratio (median of 6 per-run ratios) | per-run ratios | historical w64 cell |
|---|---|---|---|
| sum | **1.218** | 1.216..1.221 | 1.221 |
| max | **1.216** | 1.195..1.218 | 1.216 |
| min | **1.214** | 1.195..1.223 | 1.202 |

**The cell REPRODUCES in sign and within 0.012 in ratio.** The variant is
slower in all 18 per-run ratios (3 operators x 6 fresh processes), the
same sign as the historical cell and every other flip-set cell. Max
reproduces to 0.000; sum lands 0.003 below and min 0.012 above the
historical medians -- see the regime caveat below.

## Regime caveat (reported as data, not hidden)

This session again carried an intra-session clock-regime shift: :max
baseline per-run medians step 92,125/92,084/92,104 -> 38,146/29,812 ->
92,458 gpu ns and :min 91,938/91,938/73,854 -> 29,667/29,666 -> 92,125
across the six processes (:sum ran first in the op order and stayed at the
~92k level throughout, the same pattern the W = 1024 session showed).
Both arms shift together inside a run -- the paired within-run ratio is
the regime guard and it holds -- but the ratio's magnitude carries a small
regime term here too: fast-regime runs land 1.195-1.196 for :max/:min
against the slow runs' 1.211-1.223. The sign never flips (all 18 per-run
ratios above 1). This is the same qualitative term the W = 1024 cell
named (~2% of ratio at the fast clock level); the earlier "W = 64/128
per-run spread < 0.02" tightness claim holds for the slow regime but NOT
across regimes at this W (this session's :max spread 0.023, :min 0.028).

## Determinism check (the emitter-identity guard)

`diff -r` of this run's six emitted sources against the historical w64
cell's shaders/: BYTE-IDENTICAL (empty diff). Per the emit script's own
contract ("If a run of this script changes a file, an emitter changed"),
the two sessions compared the same emitted bytes.

Verified read-back (summary.md, verbatim): :max and :min bit-identical
between arms and against the CPU reference in every run; :sum arms within
3.81e-6 of each other and 3.46e-6 (baseline) / 4.53e-6 (variant) of the
reference -- the same low-bit class as the historical w64 cell's ~3.8e-06
(rule 2's low-bit movement for f32 :sum, reported as data).

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

- Correction to the previous LEFT's enumeration ("W = 64/128/256, the
  shape-2 cells"): it was imprecise. W = 256 shape-1 was already
  re-swept (the anchor, w256/) and W = 512 shape-1 was omitted. The
  exact remainder after this row: shape-1 W = 128 and W = 512 (W =
  64/256/1024 shape-1 now re-swept), and the five shape-2 flip-set cells
  (W = 64/128/256/512/1024) -- each its own MEASUREMENT row, one at a
  time.
- Cross-day replication of any cell needs a later-day run (a cron tick on
  another day), not more same-day sessions.
- The regime term now seen at W = 64 and W = 1024 (a ~2% ratio shift at
  the fast clock level, sign-invariant) motivates a regime-robust
  magnitude claim protocol -- PROPOSED, decided nowhere, own slice if
  taken.
- The blocked/absent-hardware rows stay exactly as the 2026-10-23
  correction record left them.
