# gpu-subgroup-reduce-m1max-resweep-20261023/w512 — the flip-set cell W = 512 re-swept (JUN-58)

Tick: amu-gpu chain (bot/amu-gpu-chain). Tracking: JUN-58 (the Apple vendor
row), parent JUN-55. One row of work: one MEASUREMENT -- the LAST remaining
shape-1 flip-set cell of the re-sweep series the honest LEFTs named as the
real remainder ("Shape-1 W = 512 (W = 64/128/256/1024 shape-1 now
re-swept) ... each its own MEASUREMENT row, one at a time"), run on the only
vendor this host has (Apple M1 Max).

## What this is a re-sweep OF

The shape-1 flip-set cell at the TOP of the W-sweep's measured side:
:baseline vs :subgroup-reduce on the MSL route, Apple M1 Max (reported
subgroup size 32), W = 512, n = 1,000,003, the three operators -- the exact
cell docs/evidence/gpu-subgroup-reduce-m1max-wsweep-20261023/w512/
measured earlier 2026-10-23 (the W > 256 sweep that closed the named
"W > 256 on M1 Max" UNMEASURED scope). Same-day replication across sessions
-- NOT cross-day, and it does not claim temporal stability beyond this day.

## What ran (real hardware, real emitted bytes)

- Same driver as every cell: `python3 scripts/gpu-subgroup-reduce-metal-measure.py
  --runs 6 --workgroup 512 --elements 1000003 --op-order sum,max,min
  --out docs/evidence/gpu-subgroup-reduce-m1max-resweep-20261023/w512`
  (explicit --out: the driver's named FOOTGUN -- default --out rewrites the
  historical run-log -- was avoided; the historical cell's record is
  untouched). Ran ~15:33 JST (run-log.txt / summary.md written this tick).
- Device: Apple M1 Max; reported simdgroup size 32 ([[threads_per_simdgroup]])
  in every fresh process's header.
- Protocol: identical to the historical cell -- 6 fresh-process runs, 20
  interleaved paired samples per operator per run with alternating AB/BA
  order, 2 warmup submits per arm discarded, Metal GPU timestamps
  (GPUStartTime->GPUEndTime) around one reduce dispatch, verified read-back
  of the partials. run-log.txt: 720 sample lines = 6 x 3 x 2 x 20 (grep -c
  "sample" = 720); verify ok=1 on every arm of every operator of every run
  (36 verify lines).
- Headers forwarded in all 6 runs (each of n=1000003 / workgroup=512 /
  op_order=sum,max,min appears 6 times in run-log.txt): the shape and the
  op-order were forwarded, not defaulted-into-being-measured-silently.

## The numbers (summary.md, full tables; paired statistic = ADR-0358's)

| operator | paired ratio (median of 6 per-run ratios) | per-run ratios | historical w512 cell |
|---|---|---|---|
| sum | **1.197** | 1.195..1.198 | 1.196 |
| max | **1.194** | 1.184..1.196 | 1.195 |
| min | **1.193** | 1.177..1.197 | 1.197 |

**The cell REPRODUCES in sign and within 0.004 in ratio.** The variant is
slower in all 18 per-run ratios (3 operators x 6 fresh processes), the same
sign as the historical cell and every other flip-set cell. Sum reproduces to
0.001 and max to 0.001; min lands 0.004 below the historical median -- the
same regime term the W = 64/128/1024 re-sweep cells named.

## Regime caveat (reported as data, not hidden)

This session again carried an intra-session clock-regime shift: baseline
per-run medians sit at ~114.5-114.9k gpu ns except :max run 3 (70,604) and
:min run 3 (59,834) / run 6 (92,979), with the variant's run-3 processes
shifted together (83,625 / 70,396). Both arms shift together inside a run --
the paired within-run ratio is the regime guard and it holds -- but the
ratio's magnitude carries the same small regime term seen at W = 64, 128 and
1024: the fast-regime runs land 1.177-1.184 against the slow runs'
1.192-1.198 (~2% ratio shift, sign-invariant). The sign never flips (all 18
per-run ratios above 1). At W = 512 the historical cell itself carried a
1.648 :max outlier and a 1.231 :min outlier in one process; the median-of-
per-run-medians statistic is robust to those, and this session's per-run
spread is narrower than that.

## Determinism check (the emitter-identity guard)

`diff -r` of this run's six emitted sources against the historical w512
cell's shaders/: BYTE-IDENTICAL (empty diff). Per the emit script's own
contract ("If a run of this script changes a file, an emitter changed"), the
two sessions compared the same emitted bytes.

Verified read-back (summary.md, verbatim): :max and :min bit-identical
between arms and against the CPU reference in every run; :sum arms within
3.05e-5 of each other and 1.63e-5 of the reference in every run -- the same
low-bit class as the historical w512 cell's 1.63e-5/3.05e-5 (rule 2's
low-bit movement for f32 :sum, reported as data; the historical cell's
values are identical to this run's).

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

- The shape-1 re-sweep series is now COMPLETE (W = 64/128/256/512/1024 all
  re-swept, each its own MEASUREMENT row). The five shape-2 flip-set cells
  (W = 64/128/256/512/1024) remain -- each its own MEASUREMENT row, one at
  a time.
- Cross-day replication of any cell needs a later-day run (a cron tick on
  another day), not more same-day sessions.
- The regime term now seen at W = 64, 128, 512 and 1024 (a ~2% ratio shift
  at the fast clock level, sign-invariant, wider at W = 128) motivates a
  regime-robust magnitude claim protocol -- PROPOSED, decided nowhere,
  own slice if taken.
- The blocked/absent-hardware rows stay exactly as the 2026-10-23
  correction record left them.
