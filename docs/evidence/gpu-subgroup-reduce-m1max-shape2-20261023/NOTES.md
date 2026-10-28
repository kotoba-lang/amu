amu-gpu tick 2026-10-23 -- ONE measurement: the second shape (JUN-58).
n = 2^20 = 1,048,576 (clean multiple of every W in [32, 1024], no
padded-lane tail) at W = 256 (the anchor of the flip set) and W = 32 (the
decided cell), MSL arm, native-Metal channel, same protocol as every prior
JUN-58 cell. Evidence log; no POSIX shell files.

WHY THIS SHAPE: every cell before it ran n = 1,000,003 -- one shape, and a
padded one (not a multiple of W: the tail group is partial). The variant's
record itself names "one device and narrow shape coverage" as the limit of
the narrowing's basis (accelerator_variants / variant-bases). Shape 2
changes ONE variable: the tail disappears. The emitted kernels read n at
runtime (buffer 2), so the arms are byte-identical to shape 1's, and the
LCG input prefix is the same first 1,000,003 values.

INSTRUMENT CHANGE (this tick, named): the shape rode a #define before
(N_ELEM 1000003u). It is now a command-line variable
(scripts/gpu-subgroup-reduce-metal-measure.{m,py}: argv[3] / --elements,
default 1000003 so every historical protocol statement still describes the
default). The timing path is untouched.

WHAT THE TICK RAN (real tool output, in this directory):

    python3 scripts/gpu-subgroup-reduce-metal-measure.py --runs 6 \
      --workgroup 256 --elements 1048576 \
      --out docs/evidence/gpu-subgroup-reduce-m1max-shape2-20261023/w256
    python3 scripts/gpu-subgroup-reduce-metal-measure.py --runs 6 \
      --workgroup 32 --elements 1048576 \
      --out docs/evidence/gpu-subgroup-reduce-m1max-shape2-20261023/w32

Each cell: the emitters' own bytes for both arms at that width, 6
fresh-process runs, 20 interleaved paired samples per operator per run
with alternating AB/BA order, 2 warmup submits discarded, verified
read-back against a double CPU reference (summary.md / run-log.txt /
compile-log.txt per cell).

PAIRED MEDIAN RATIOS (variant/baseline gpu ns; per fresh process the
median over its pairs, then the median over the six processes) AT
SHAPE 2 (n = 2^20), with the shape-1 anchor beside it:

    W     op    shape-2       shape-1 (n = 1000003, prior record)
    256   sum   1.227         1.220
    256   max   1.223         1.217
    256   min   1.220         1.217
    32    sum   0.919         0.918
    32    max   0.921         0.923
    32    min   0.918         1.019 (NOT ESTABLISHED, regime-straddling)

FINDING: the shape-1 verdicts replicate at the second shape. The W = 256
penalty band is the same ~22% off the padded tail as on it (1.220-1.227,
per-run spread tight), and the W = 32 not-slower sign replicates too
(:sum 0.919 with every one of the six processes below 1, 0.916-0.922).
The narrowing's demotion basis is therefore NOT a padded-tail artifact --
but the W = 32 sign is STILL regime-scoped on this shape, exactly as on
shape 1, so the honesty lock there still has no cross-regime verdict to
release it.

THE REGIME, RE-MEASURED (W = 32, shape 2): the per-run baseline medians
show the clock stepping inside and across processes (sum all six runs
~113.3-114.1k ns; max 114.1k/113.9k/48.0k/37.8k/112.9k/113.8k; min
113.8k/113.3k/48.0k/37.5k/37.6k/114.0k) and the ratio follows the clock,
not the operator:
  - slow level (~113k): variant ~8% FASTER (max ratios 0.916/0.918/0.925/
    0.917, min 0.917/0.918/0.917)
  - middle level (~48k): still faster (max 0.928, min 0.910)
  - fast level (~37.5k): variant slightly SLOWER (max 1.026, min
    1.021/1.026)
So W = 32's sign straddles 1 across clock levels on shape 2 just as on
shape 1 -- a regime-scoped sign, not a selection basis. At W = 256 the
penalty is regime-ROBUST on both shapes (shape-2 per-run ratios
1.203-1.231 at every clock level; shape-1 was tight across regimes too).

INSTRUMENT STRUCTURE FOUND (named, not hidden): :sum STILL has no
fast-regime sample -- on shape 2 all six :sum runs sat at the slow level
even though runs 3-5 reached the fast level later IN THE SAME processes
for :max/:min. The cause is structural, not luck: the harness dispatches
the operators in a FIXED order (sum, max, min) per fresh process, so :sum
is always the first op after process start and the GPU clock ramp always
happens after it. Any future W = 32 regime question needs an op-order
variant (or an op-per-process schedule) to sample :sum in the fast regime;
this tick does not build it.

READ-BACK (every fresh process, every cell): ok=1 on all 72 verify lines,
0 failures. :max/:min bit-exact against the CPU reference and between
arms in both cells. :sum at W = 32 is bit-exact BETWEEN arms (one simdgroup
per group at W = S = 32, both regroup identically), 2.15e-06 vs ref; at
W = 256 the arms regroup differently (3.05e-05 vs each other) as in the
historical W = 256 cell.

STATE HONESTY:
- MEASURED (this tick, this host, MSL arm, native-Metal channel): the
  second shape n = 2^20 at W = 256 and W = 32 on Apple M1 Max. Numbers
  above are this directory's own record.
- NOT MOVED (this tick): no :measured? flag, no :measured-cell set, no
  selection behavior, no workgroup row (ADR-0355/0358). The flip contract
  keys to n = 1,000,003 (accelerator_variants/apple-measured-n) and this
  tick does not extend it -- the shape-2 numbers are corroboration, and
  whether the contract's basis text should cite them is its own later
  slice.
- CORROBORATED (not upgraded): the W = 64..1024 demotion basis and the
  W = 32 decision both survive a second shape. The W = 32 answer keeps
  the honesty lock unchanged (:measured? false, apple-w32-note): its win
  is still regime-scoped on the new shape too.
- UNMEASURED (unchanged): the GLSL arm at any width beyond its labeled
  bootstrap record (no wire-42 execution path since the C loader removal,
  ADR 0371 provider track unimplemented); every other Apple device; other
  shapes beyond these two; NVIDIA/Intel/ARM/AMD variant rows entirely.

VERIFICATION (runner output, not paraphrase):
- w256/summary.md, w256/run-log.txt, w256/compile-log.txt and w32/
  siblings in this directory are the driver's own record.
- Gate: this diff touches scripts/*.m, scripts/*.py (measurement
  instrument) and docs/evidence -- no test namespace. The scoped GPU gate
  (the 7 GPU-owned namespaces) was run anyway and its output is in
  ../gpu/shape2-measurement-20261023.txt alongside the full run-tests.cljk
  state.

LEFT (the next rows): whether the flip contract's basis text should cite
the shape-2 corroboration (one prose slice, no flag movement expected);
an op-order variant of the harness so :sum can sample the fast regime
(the W = 32 regime question's structural blocker); the GLSL arm stays
blocked on a wire-42 route.
