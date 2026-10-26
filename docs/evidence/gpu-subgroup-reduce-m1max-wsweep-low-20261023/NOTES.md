amu-gpu tick 2026-10-23 -- ONE measurement: the named UNMEASURED scope
"MSL W = 32..128 on M1 Max" gets hardware numbers (JUN-58), plus the
instrument defect the first cell exposed. Evidence log; no POSIX shell
files.

WHAT THE TICK RAN (real tool output, in this directory):

The JUN-58 native-Metal measurement driver
(scripts/gpu-subgroup-reduce-metal-measure.{py,cljk,m}) at the three
remaining widths of the MSL band, on this host (Apple M1 Max,
[[threads_per_simdgroup]] = 32):

    python3 scripts/gpu-subgroup-reduce-metal-measure.py --runs 6 \
      --workgroup {32,64,128} --out docs/evidence/ \
      gpu-subgroup-reduce-m1max-wsweep-low-20261023/w{32,64,128}

Each cell: the emitters' own bytes for :baseline and :subgroup-reduce MSL
arms at that cell's width, 6 fresh-process runs, 20 interleaved paired
samples per operator per run with alternating AB/BA order, 2 warmup
submits discarded, verified read-back against a double CPU reference
(run-log.txt / compile-log.txt / summary.md per cell).

INSTRUMENT DEFECT (found at W = 32, fixed this tick, named not hidden):

The first W = 32 driver run crashed the harness with signal 10 (SIGBUS)
before any output. Root cause in scripts/gpu-subgroup-reduce-metal-measure.m
line 225: the verified read-back's scratch arrays were fixed at 3907
elements -- exactly W = 256's group count (ceil(1000003/256) = 3907). Any
cell with MORE groups overflows the stack: W = 32 admits 31251 groups.
The prior W-sweep (W = 256/512/1024) never hit it because every cell had
fewer groups than 3907 -- the guard admitted [32, 1024] but the instrument
could only run [256, 1024]. The arrays are now malloc'd from num_groups
(the timing path is untouched by the fix).

PAIRED MEDIAN RATIOS (variant/baseline gpu ns; per fresh process the
median over its pairs, then the median over the six processes):

    W     :sum   :max   :min
    32    0.918  0.923  1.019
    64    1.221  1.216  1.202
    128   1.246  1.243  1.242

    (anchors, prior sessions, same host/protocol:
     256: 1.220/1.217/1.217   512: 1.196/1.195/1.197   1024: 1.186/1.186/1.185)

FINDING: the penalty band is NOT monotone toward small W. W = 64 and
W = 128 measure the same ~20-25% penalty as W >= 256 (peaking at W = 128,
1.243-1.246). W = 32 is the one cell where the variant is not slower:
:sum is faster in every fresh process (ratios 0.916-0.920), :max faster in
the slow-clock runs (0.916-0.924) -- about 8% ahead.

REGIME NOISE, named: the GPU changed clock state mid-session in the W = 32
cell (per-run median gpu ns step 109k -> 36k inside the same process's op
order and across processes). In the fast regime the W = 32 arms are within
noise of each other (:min runs 3-6 ratios 1.017-1.024; :max runs 4/6
0.958/1.017). So the W = 32 :min cell's overall sign (median 1.019) is
NOT ESTABLISHED -- its per-run ratios straddle 1 with the regime shift --
and the "variant faster" claim at W = 32 is scoped to the slow regime
where :sum ran all six processes. W = 64/128 ratios are tight across
regimes (per-run spread < 0.02).

READ-BACK (every fresh process, every cell): ok=1 on all 108 verify
lines, 0 failures. :max/:min bit-exact against the CPU reference and
between arms in every cell. :sum at W = 32 is bit-exact BETWEEN arms
(both regroup identically: one simdgroup per group) and 2.15e-06 vs ref;
at W = 64/128 :sum's arms regroup differently (3.8e-06 / 1.5e-05 vs each
other).

STATE HONESTY:
- MEASURED (this tick, this host, MSL arm only, native-Metal channel --
  the channel ADR-0360 question (1)'s 2026-10-23 decision admits for the
  MSL arm): W = 32/64/128 on Apple M1 Max. The full MSL band W = 32..1024
  is now measured on this device; no cell of it remains UNMEASURED.
- NOT MOVED (this tick): no :measured? flag, no :measured-cell W set, no
  selection behavior, no workgroup row (ADR-0355/0358). The honesty-lock
  flip set in accelerator_variants.cljk still names W = 256/512/1024 only.
- CONTRADICTED, not yet acted on: the narrowing's demotion rationale ("the
  variant measured slower at every W, so :baseline at every W on this
  device") is contradicted at W = 32 by this device's own measurement. The
  selection change (whether the narrowing's W = 32 cell should answer
  :subgroup-reduce, and the flip set + test label refresh with it) is an
  implementation slice, LEFT for the next tick with its tests -- this tick
  is the measurement only.
- UNMEASURED (unchanged): the GLSL arm at W > 256 (no wire-42 execution
  path since the C loader removal; 2026-10-19 GLSL band stopped at 256);
  every other Apple device; NVIDIA/Intel/ARM/AMD rows entirely.

VERIFICATION (runner output, not paraphrase):
- Each cell's summary.md / run-log.txt / compile-log.txt in this
  directory (w32/, w64/, w128/) is the driver's own record.
- Gate: this diff touches scripts/*.m (measurement instrument), the .py
  summary boilerplate (prose), docs and evidence -- no test namespace. The
  scoped GPU gate was run anyway and its output is in scoped-gate.txt; the
  full run-tests.cljk state is in full-gate.txt.

LEFT (the next rows): the W = 32 selection question (narrowing vs
measured-cell flip at the band's bottom edge) as one implementation slice
with tests; the test label "MSL W = 32..128 keeps the lock (UNMEASURED)"
in accelerator_variants_test.cljk is stale as of this measurement and
updates with that slice; the GLSL arm at W > 256 stays blocked on a
wire-42 route (ADR 0371 provider).
