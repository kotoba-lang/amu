amu-gpu tick 2026-10-23 -- ONE measurement: the named UNMEASURED scope
"W > 256 on M1 Max" gets hardware numbers (JUN-58).
Evidence log; no POSIX shell files.

WHAT THE TICK RAN (real tool output, in this directory):

The JUN-58 native-Metal measurement driver
(scripts/gpu-subgroup-reduce-metal-measure.{py,cljk,m}), extended this
tick to parameterize the workgroup width W, ran three cells on this host
(Apple M1 Max, [[threads_per_simdgroup]] = 32):

    python3 scripts/gpu-subgroup-reduce-metal-measure.py --runs 6 \
      --workgroup {256,512,1024} --out docs/evidence/ \
      gpu-subgroup-reduce-m1max-wsweep-20261023/w{256,512,1024}

Each cell: the emitters' own bytes for :baseline and :subgroup-reduce MSL
arms at that cell's width (the subgroup arm's threadgroup partials array
is sized from the emitted W, so every cell emits its own sources --
shaders/ under each cell), 6 fresh-process runs, 20 interleaved paired
samples per operator per run with alternating AB/BA order, 2 warmup
submits discarded, verified read-back against a double CPU reference
(run-log.txt / compile-log.txt / summary.md per cell).

PAIRED MEDIAN RATIOS (variant/baseline gpu ns; per fresh process the
median over its pairs, then the median over the six processes):

    W     :sum   :max   :min
    256   1.220  1.217  1.217   (anchor; reproduces the earlier same-day
                                 W=256 cell, 1.216-1.223)
    512   1.196  1.195  1.197
    1024  1.186  1.186  1.185

FINDING: the variant is SLOWER at every measured W, all three operators,
every fresh process -- W = 512 and W = 1024 are now MEASURED on M1 Max
(MSL arm), closing the scope ADR-0360's second decision named as
UNMEASURED. The demotion to :baseline at W > 256 on this device rests on
this device's own measurement at those sizes, not on the monotone-trend
inference. The penalty NARROWS slightly with W on the MSL arm (1.22 ->
1.19) where the GLSL band (PR #1348, W = 32..256) grew with W; the SIGN
is unanimous in every measured cell of both arms. One noisy run at W = 512
(:max run 3, faster-clocked baseline, ratio 1.648) is visible in the
per-run ratios and does not move the medians. Read-back: :max/:min
bit-exact vs the CPU reference and between arms in every cell (rule 2's
ordinary-value domain holds on hardware); :sum's low-bit divergence grows
with W (max abs vs other 3.05e-05 at W=256, 6.10e-05 at W=1024).

STATE HONESTY:
- MEASURED (this tick, this host, MSL arm only): W = 512 and W = 1024 on
  Apple M1 Max via the native-Metal harness; W = 256 re-run as the
  same-session anchor.
- UNMEASURED (unchanged): the GLSL arm at W > 256 (the wire-42 route has
  no execution path since the C loader removal; the 2026-10-19 GLSL band
  stopped at W = 256). Everything on Intel/Mali/NVIDIA/AMD hardware.
- CONTRACT CAVEAT (unchanged): these numbers carry ADR-0360 question (1)'s
  undecided status -- the native-Metal harness is NOT the wire-42 route
  the measurement contract names. :measured? is UNCHANGED (false on every
  answer of every row) and no workgroup row (ADR-0355/0358) is touched.
  Question (1) remains PROPOSED, decided nowhere.

WHAT CHANGED (thin recording half of the same slice):
1. scripts/gpu-subgroup-reduce-metal-measure.cljk -- --width N / --out DIR
   (defaults preserve the historical single cell byte-for-byte: verified,
   the six W=256 sources re-emitted to scratch are IDENTICAL to
   docs/evidence/gpu-subgroup-reduce-m1max-20261023/shaders/). A width
   outside the KIR's admission (power of two in [32, 1024]) is REFUSED.
2. scripts/gpu-subgroup-reduce-metal-measure.m -- W is runtime (argv[2],
   default 256), REFUSED outside the same admission, and a dispatch-width
   guard against the pipeline's maxTotalThreadsPerThreadgroup.
3. scripts/gpu-subgroup-reduce-metal-measure.py -- --workgroup / --out;
   runs pass the width to both the emit step and the harness; the summary
   states the cell's width and MISMATCHES are named if the harness
   disagrees. The refuted "first hardware comparison" title claim is gone
   from newly generated summaries. FOOTGUN named: a DEFAULT run rewrites
   the historical W=256 record in place (run logs are not deterministic);
   sweep cells pass --out and never touch it.
4. docs/adr/0360-... -- the "Scope, stated plainly" UNMEASURED clause
   marked SUPERSEDED as to W > 256 MSL, plus the W-sweep amendment with
   the table above and what it does and does not license.
5. src/kotoba/compiler/accelerator_variants.cljk -- PROSE ONLY (no
   behavior): the apple-narrow-note's "W > 256 on this device is
   UNMEASURED" tail replaced by the measured statement; the
   :subgroup-reduce basis cell extended with the W-sweep numbers; the ns
   docstring's false "Nothing in this repository has executed a variant
   reduction on the vendor hardware its rows name" (contradicted by
   variant-bases in the same file since the row-prose reconciliation)
   corrected to the execution record. No :measured? flag, no row, no
   selection behavior moved.

VERIFICATION (runner output, not paraphrase):
- scoped gate (7 GPU-owned namespaces, kbb --backend sci): "Ran 85 tests
  containing 6336 assertions. 0 failures, 0 errors." -- IDENTICAL counts
  to the pre-edit base (prose-only diff), verbatim in scoped-gate.txt.
- full gate run-tests.cljk: RED AT BASE, unchanged by this diff -- aborts
  at namespace load "Could not find namespace: kotoba.form" (upstream W3
  port via kotoba.compiler.js-value-target, outside this diff), verbatim
  in full-gate.txt. No green-suite claim.
- emit determinism: the six W=256 sources re-emitted with the
  parameterized script are byte-identical (cmp) to the historical cell.

TOOLING DEFECTS (named, not hidden; this tick):
- the patch wire's whitespace mangling placed a guard inside a parse loop
  with broken indentation twice (IndentationError caught by the wire's
  own lint before any run); fixed by exact replacement. One loop variable
  (`out`) shadowed the new output-path variable and was renamed
  (`run_out`) -- caught by reading, not by any tool.
- the escape-drift auto-corrector fired again on the .cljk docstring edit
  (it reports stripping a "spurious" backslash); verified after the edit
  that the escaped \"m1 max\" inside apple-narrow-note survived intact.

LEFT (the next rows, unchanged by this tick): ADR-0360 question (1) (does
a native Metal harness satisfy the measurement contract?) stays PROPOSED
and blocks every :measured? flip; the GLSL arm at W > 256 is UNMEASURED
and unmeasurable until a wire-42 route exists (ADR 0371 provider);
W = 32..128 on the MSL arm is UNMEASURED (the earlier bands were the GLSL
arm).
