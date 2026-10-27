# gpu-subgroup-reduce-m1max-oporder-20261024/w1024-sum-last -- the W = 1024 op-order-scoped regime check (JUN-58)

Tick: amu-gpu chain (bot/amu-gpu-chain). Tracking: JUN-58 (the Apple vendor
row; Linear AWAI-41), parent JUN-55 (AWAI-35). One row of work: ONE
MEASUREMENT -- the op-order-scoped regime check the resweep w1024 record's
Honest LEFT named as PROPOSED ("The W = 1024 regime term (above) motivates
an op-order-scoped regime check at this W -- PROPOSED, own slice if
taken"), run on the only vendor this host has (Apple Silicon).

## What this is a check OF

The flip-set cell at the top of the W band: :baseline vs :subgroup-reduce
on the MSL route, Apple M1 Max (reported subgroup size 32), W = 1024,
n = 1,000,003 -- the cell
docs/evidence/gpu-subgroup-reduce-m1max-wsweep-20261023/w1024/ measured
(2026-10-23) and
docs/evidence/gpu-subgroup-reduce-m1max-resweep-20261023/w1024/ re-swept
(2026-10-23). The resweep's regime caveat measured a ratio term at this W
(the fast-regime runs carried 1.167-1.175 for :max/:min against the slow
runs' 1.183-1.186) and named its own confound: under the fixed sum,max,min
dispatch order, :sum's block runs FIRST (it "stayed at the ~128k level
throughout") while :max/:min's later blocks hit the fast regime -- so the
term could be a clock-regime term OR a dispatch-block-position term. This
cell separates the two the way the W = 32 cell did
(docs/evidence/gpu-subgroup-reduce-m1max-oporder-20261023/w32-sum-last):
the instrument runs :sum LAST.

This is an OP-ORDER CHECK, not a cross-day replication row: it fills none
of the nine pending :simdgroup-reduce cross-day rows (each runnable
2026-10-25+ per its own session date) and claims nothing about them.

## What ran (real hardware, real emitted bytes)

- Same driver, the op-order instrument of 2026-10-23:
  `python3 scripts/gpu-subgroup-reduce-metal-measure.py --runs 6
  --workgroup 1024 --elements 1000003 --op-order max,min,sum --out
  docs/evidence/gpu-subgroup-reduce-m1max-oporder-20261024/w1024-sum-last`
  (explicit --out: the driver's named FOOTGUN, avoided; no historical
  record was rewritten). Ran 2026-10-24 ~17:00 JST.
- Device: Apple M1 Max; reported simdgroup size 32
  ([[threads_per_simdgroup]]) in every fresh process's header.
- Protocol: identical to every cell -- 6 fresh-process runs, 20
  interleaved pairs per operator per run with alternating AB/BA order, 2
  warmup submits per arm discarded, Metal GPU timestamps around one reduce
  dispatch, verified read-back of the partials (run-log.txt: 720 sample
  lines = 6 x 3 x 2 x 20).
- Headers: all six runs print n=1000003, workgroup=1024,
  op_order=max,min,sum (the shape and op-order were forwarded, not
  defaulted).

## The numbers (summary.md, full tables; paired statistic = ADR-0358's)

| operator | paired ratio (median of 6 per-run ratios) | per-run ratios | same cell, sum-first sessions |
|---|---|---|---|
| sum | **1.185** | 1.184..1.186 | 1.186 (wsweep), 1.185 (resweep) |
| max | **1.184** | 1.183..1.185 | 1.186 (wsweep), 1.177 (resweep) |
| min | **1.184** | 1.183..1.186 | 1.185 (wsweep), 1.172 (resweep) |

Baseline per-run medians: 128,125..128,500 gpu-ns at every operator --
ONE rule-1 level (GAP-1.15), cross-operator level identity HOLDS (all 15
run pairs agree). Rule 2: regime-invariant slower at all three operators
(18/18 per-run ratios above 1.0). The fresh-process clock ramp the
resweep saw (128k -> 40k within one session) did NOT appear in this
session: zero middle- or fast-bucket pairs at any operator
(analyze-oporder.txt: every one of the 360 pairs sits above the 80k slow
bucket; single pairs spike both ways on host noise, 0.198..2.705, named in
the per-pair lists).

## What the check answers (its finding)

**At a fixed regime, the paired ratio does not follow the dispatch block's
position.** :sum measured at the LAST block lands 1.185 -- within 0.001 of
:sum at the FIRST block in both sum-first sessions (1.186/1.185) and of
:max/:min at their blocks in this session (1.184/1.184). The resweep's
lower fast-regime ratios (1.167-1.175) are therefore attributable to the
clock regime, not to running in a later block -- the position confound its
caveat named is ruled out at the slow regime. The same separation at the
fast regime was measured at W = 32 (the 2026-10-23 cell: all three
operators ~1.02-1.03 at the fast level, :sum at the last block included);
at W = 1024 the fast regime is UNMEASURED in this session (zero fast
pairs) and the fast-regime ratio at any block position stays UNMEASURED
here.

A second, structural fact this session adds: the fresh-process clock ramp
is SESSION-dependent, not protocol-determined -- three sessions at this
cell shape have now produced three different regime structures (wsweep
with an intra-session ramp at :max/:min, resweep with its larger
128k->40k shift, this session single-level throughout).

## Determinism check (the emitter-identity guard)

`diff -r` of this run's emitted sources against BOTH earlier W = 1024 cells'
shaders/ (wsweep-20261023/w1024 and resweep-20261023/w1024): BYTE-IDENTICAL
(empty diff, both). Verified read-back (summary.md, verbatim): :max and :min
bit-identical between arms and against the CPU reference; :sum arms within
6.10e-5 of each other and 3.27e-5 of the reference -- the same values as
both earlier W = 1024 cells. 36 verify lines, ok=1 on every arm of every
operator of every run.

## What this is NOT (nothing upgrades)

- No `:measured?` flag moves, no `:measured-cell` set changes, no selection
  answer changes, no workgroup row (ADR-0355/0358) is touched. This diff
  is docs/evidence only -- no code namespace and no test namespace changed.
- Not a cross-day replication row, not a new shape, width, device or route;
  it is an op-order instrument run, its own record kind (the W = 32 cell's).
- The regime term's magnitude claim stays regime-matched (claim protocol
  rule 3): the resweep's ~18.5% band at the slow level is corroborated here
  at all three operators; the ~17% fast-level band is not re-measured here.
- UNMEASURED scope unchanged: shapes beyond the two contract cells; every
  Apple device but this M1 Max; W = 32 as a verdict (it is a decision); the
  GLSL arm beyond its LABELED BOOTSTRAP record (blocked on a wire-42
  execution route, ADR 0371); the NVIDIA/Intel/ARM/AMD variant rows
  entirely (no hardware; the fleet hosts are tailnet-SSH-blocked to this
  session, verified this tick).
- The channel is the native-Metal harness (ADR-0360 question (1)'s
  2026-10-23 decision admits it as contract-satisfying FOR THE MSL ARM);
  wire 42 still executes SPIR-V through Vulkan only.

## Gate (this diff changed no code namespace)

1. python3 scripts/gpu_regime_classify.py --self-test
   -> TOTAL: 1904 assertions passed, 0 failed.
      (1873 at the previous tick; the growth is this record joining the
      classified corpus -- corpus 53 -> 54 summaries, rule-2 cells
      159 -> 162, three new regime-invariant slower.)
2. python3 scripts/gpu-subgroup-reduce-metal-measure.py --self-test
   -> driver auto-wiring self-test: 12 assertions passed, 0 failed.
3. Scoped GPU gate (the 8 GPU-owned test namespaces, scratch runner
   gpu_scoped_gate.cljk, not in the repo; classpath route 2,
   AMU_KBB_TEST_CLASSPATH):
     kbb --backend sci --classpath "src:test:$AMU_KBB_TEST_CLASSPATH" \
       /Users/junkawasaki/.hermes/profiles/amu-gpu/cache/scratch/gpu_scoped_gate.cljk
   -> Ran 102 tests containing 9774 assertions. 0 failures, 0 errors.
      (unchanged from the previous tick -- this diff touches no code or
      test namespace; run anyway.)
4. Full suite (run-tests.cljk, same route-2 classpath): RED AT BASE,
   outside this diff, at namespace load on `kotoba.form`
   ("Could not find namespace: kotoba.form"; the W3 port path, ADR 0362).
   No green full suite is claimed.

## Honest LEFT (the real remainder after this row)

- The nine pending :simdgroup-reduce cross-day rows (the narrowed list),
  runnable 2026-10-25+ per each pair's own session date.
- The W = 1024 fast-regime ratio at a late block position stays UNMEASURED
  (this session held one regime); a session that ramps would close it, but
  no session schedules a regime.
- A later-day DATA run at the refused pair (shape-2 W = 512): neither
  scheduled nor forbidden (its own decision row if wanted).
- The blocked rows stay exactly as prior records left them.
