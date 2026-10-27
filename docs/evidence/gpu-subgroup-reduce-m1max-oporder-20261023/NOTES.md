# JUN-58 -- the op-order instrument variant: :sum measured in the fast regime (2026-10-23)

## What changed

The instrument variant the shape-2 record named as the structural blocker
on the W = 32 regime question: the harness's fixed operator dispatch order
(sum, max, min) left :sum with NO fast-regime sample on any cell, because
the fresh-process clock ramp always completed after :sum's block. The
harness now takes a dispatch order (argv[4] in
scripts/gpu-subgroup-reduce-metal-measure.m, --op-order in the .py driver,
a comma-separated permutation of sum,max,min, validated in both, default
"sum,max,min" -- byte-identical behavior for every earlier cell's command
line). The order is printed as `op_order=` in every run header and recorded
in summary.md. The timing path, the pairs, the warmup, the read-back and
the emitted bytes are untouched.

## The cell

w32-sum-last/: W = 32, n = 1,000,003 (the flip contract's shape -- the
shape the W = 32 decision was made on), order "max,min,sum" (sum LAST,
after where the ramp happens), 6 fresh processes, 20 interleaved AB/BA
pairs per operator per run, 2 warmup submits per arm discarded, verified
read-back. Same host (Apple M1 Max, reported subgroup size 32), same
native-Metal channel (MSL arm only; NOT wire 42). Protocol identical to
every earlier cell except the named order variable.

## What the numbers say

The ADR-0358 per-run statistic (summary.md): sum 0.919 (per-run
0.921/0.918/0.917/0.915/0.925/1.016), max 0.916, min 0.920 -- but this
statistic averages over whatever clock levels the process sat at and
cannot answer the regime question. The regime-conditioned within-pair
ratio can (analyze-oporder.py over run-log.txt; level buckets set from the
observed clusters -- slow ~109k, middle ~45-69k, fast ~35.6-37k baseline
gpu_ns per pair):

| op  | level  | pairs | median pair ratio |
|-----|--------|-------|-------------------|
| sum | slow   | 61    | 0.919             |
| sum | middle | 35    | 0.932             |
| sum | fast   | 24    | 1.018             |
| max | slow   | 113   | 0.917             |
| max | fast   | 7     | 1.029             |
| min | slow   | 86    | 0.920             |
| min | middle | 14    | 0.993             |
| min | fast   | 20    | 1.018             |

FINDING: :sum's sign follows the clock level exactly the way :max/:min's
does. The first :sum samples that exist at the fast level are SLOWER for
the variant (median 1.018 over 24 pairs; run 6's per-run ratio 1.016),
while the same :sum at the slow level is ~8% faster (0.919). The W = 32
"variant is faster" win is a SLOW-REGIME ARTIFACT for all three operators;
at the fast level the variant is slower for all three (1.018 / 1.029 /
1.018). The shape-2 record's statement that the W = 32 sign is
regime-scoped was, for :sum, an inference from structure (no fast sample
could exist); it is now directly measured.

Named noise, not hidden: single pairs spike in both directions at the slow
and middle levels (0.295..2.858 in the raw per-pair lists in
analyze-oporder.txt -- clock/transient glitches in one pair); the medians
above are robust to them and the per-pair lists are printed in full. The
middle buckets are ramp-transition samples and noisier (sum 0.932 over
0.716..1.274).

## What does NOT change (state honesty)

- No `:measured?` flag, no `:measured-cell` set, no selection behavior and
  no workgroup row (ADR-0355/0358) is touched by this tick. The diff is
  scripts/gpu-subgroup-reduce-metal-measure.{m,py} + docs/evidence.
- The W = 32 keep-`:baseline` decision (2026-10-23) stands unchanged and
  keeps its honesty lock (:measured? false). Its basis is strengthened:
  the regime split is now measured at :sum too, not inferred.
- The flip contract still keys to n = 1,000,003; this run is ON that
  shape. Nothing extends the contract.
- UNMEASURED unchanged: the GLSL arm (no wire-42 route since the C loader
  removal), every Apple device but this M1 Max, every other shape,
  NVIDIA/Intel/ARM/AMD variant rows.

## Gate (real runs, this host, kbb --backend sci)

  scoped (the 7 GPU-owned test namespaces, scratch runner):
    Ran 87 tests containing 6512 assertions.
    0 failures, 0 errors.
    (87/6512 before this tick too -- this diff touches no test namespace.)

  full (kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)"
  run-tests.cljk): RED AT BASE, verified this tick, outside this diff --
  fails at NAMESPACE LOAD with "Could not find namespace: kotoba.form"
  (the W3 port path, documented red at base in ADR 0362).

## LEFT (the next rows)

- The prose slice: the flip contract's basis text and ADR-0360 should
  cite the shape-2 corroboration AND this regime measurement (the prior
  record's prose slice, now with more material -- one slice).
- Whether the W = 32 decision note's basis should name the now-measured
  :sum fast-regime samples explicitly (same prose slice territory).
- The GLSL arm stays blocked on a wire-42 execution route (ADR 0371).
