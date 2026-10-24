# gpu-subgroup-reduce-m1max-resweep-20261023/w128 — the flip-set cell W = 128 re-swept (JUN-58)

Tick: amu-gpu chain (bot/amu-gpu-chain). Tracking: JUN-58 (the Apple vendor
row), parent JUN-55. One row of work: one MEASUREMENT -- the fourth cell of
the re-sweep series the honest LEFTs named as the real remainder ("Re-sweeps
of the remaining flip-set cells ... are each their own MEASUREMENT row, one
at a time"), run on the only vendor this host has (Apple M1 Max).

## What this is a re-sweep OF

The flip-set cell at the TOP of the measured W band's penalty side:
:baseline vs :subgroup-reduce on the MSL route, Apple M1 Max (reported
subgroup size 32), W = 128, n = 1,000,003, the three operators -- the exact
cell docs/evidence/gpu-subgroup-reduce-m1max-wsweep-low-20261023/w128/
measured earlier 2026-10-23 (the low band that closed the named
"MSL W = 32..128 on M1 Max" UNMEASURED scope). Same-day replication across
sessions -- NOT cross-day, and it does not claim temporal stability beyond
this day.

## What ran (real hardware, real emitted bytes)

- Same driver as every cell: `python3 scripts/gpu-subgroup-reduce-metal-measure.py
  --runs 6 --workgroup 128 --elements 1000003 --op-order sum,max,min
  --out docs/evidence/gpu-subgroup-reduce-m1max-resweep-20261023/w128`
  (explicit --out: the driver's named FOOTGUN -- default --out rewrites the
  historical run-log -- was avoided; the historical cell's record is
  untouched). Ran ~15:17 JST (run-log.txt / summary.md written 15:18:01).
- Device: Apple M1 Max; reported simdgroup size 32 ([[threads_per_simdgroup]])
  in every fresh process's header.
- Protocol: identical to the historical cell -- 6 fresh-process runs, 20
  interleaved paired samples per operator per run with alternating AB/BA
  order, 2 warmup submits per arm discarded, Metal GPU timestamps
  (GPUStartTime->GPUEndTime) around one reduce dispatch, verified read-back
  of the partials. run-log.txt: 720 sample lines = 6 x 3 x 2 x 20 (grep -c
  "sample" = 720); verify ok=1 on every arm of every operator of every run
  (36 verify lines).
- Headers forwarded in all 6 runs (each of n=1000003 / workgroup=128 /
  op_order=sum,max,min appears 6 times in run-log.txt): the shape and the
  op-order were forwarded, not defaulted-into-being-measured-silently.

## The numbers (summary.md, full tables; paired statistic = ADR-0358's)

| operator | paired ratio (median of 6 per-run ratios) | per-run ratios | historical w128 cell |
|---|---|---|---|
| sum | **1.244** | 1.229..1.247 | 1.246 |
| max | **1.243** | 1.222..1.245 | 1.243 |
| min | **1.234** | 1.215..1.244 | 1.242 |

**The cell REPRODUCES in sign and within 0.008 in ratio.** The variant is
slower in all 18 per-run ratios (3 operators x 6 fresh processes), the same
sign as the historical cell and every other flip-set cell. Max reproduces to
0.000 and sum to 0.002; min lands 0.008 below the historical median -- see
the regime caveat below.

## Regime caveat (reported as data, not hidden)

This session again carried an intra-session clock-regime shift, and at W =
128 it hit MORE processes than at W = 64/1024: baseline per-run medians
step 95.5-95.7k gpu ns down to 50,000 (:sum run 6), 49,812/30,625 (:max
runs 4/6), and 95,750 -> 30,396 across the six :min processes. Both arms
shift together inside a run -- the paired within-run ratio is the regime
guard and it holds -- but the ratio's magnitude carries the same regime
term the W = 64 and W = 1024 cells named: fast-regime runs land 1.215-1.230
against the slow runs' 1.241-1.247. The sign never flips (all 18 per-run
ratios above 1). The min median's 0.008 gap vs the historical cell is
carried by this regime mix (3 of 6 processes in the fast regime). The
earlier "W = 64/128 per-run spread < 0.02" tightness claim does NOT hold
across regimes at this W (this session's spreads: sum 0.018, max 0.023,
min 0.029).

## Determinism check (the emitter-identity guard)

`diff -r` of this run's six emitted sources against the historical w128
cell's shaders/: BYTE-IDENTICAL (empty diff). Per the emit script's own
contract ("If a run of this script changes a file, an emitter changed"), the
two sessions compared the same emitted bytes.

Verified read-back (summary.md, verbatim): :max and :min bit-identical
between arms and against the CPU reference in every run; :sum arms within
1.53e-5 of each other and 9.24e-6 (baseline) / 9.78e-6 (variant) of the
reference -- the same low-bit class as the historical w128 cell's
9.24e-6/9.78e-6/1.53e-5 (rule 2's low-bit movement for f32 :sum, reported
as data; the historical cell's values are identical to this run's).

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

- Scoped GPU gate (the 7 GPU-owned test namespaces), run this tick after
  the measurement: "Ran 88 tests containing 7122 assertions. 0 failures,
  0 errors."
- Full run-tests.cljk: RED AT BASE, re-run this tick (real transcript:
  aborts at namespace load with "Could not find namespace: kotoba.form",
  the W3 port path, outside this diff -- documented red at base in ADR 0362
  and every prior tick record). No green full suite is claimed.

## Honest LEFT (the real remainder after this row)

- Shape-1 W = 512 (W = 64/128/256/1024 shape-1 now re-swept), and the five
  shape-2 flip-set cells (W = 64/128/256/512/1024) -- each its own
  MEASUREMENT row, one at a time.
- Cross-day replication of any cell needs a later-day run (a cron tick on
  another day), not more same-day sessions.
- The regime term now seen at W = 64, 128 and 1024 (a ~2% ratio shift at
  the fast clock level, sign-invariant, and wider at W = 128) motivates a
  regime-robust magnitude claim protocol -- PROPOSED, decided nowhere,
  own slice if taken.
- The blocked/absent-hardware rows stay exactly as the 2026-10-23
  correction record left them.
