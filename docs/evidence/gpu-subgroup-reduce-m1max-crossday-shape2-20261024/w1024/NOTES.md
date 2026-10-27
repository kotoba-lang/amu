# NOTES -- the cross-day replication of the :subgroup-reduce shape-2 W = 1024
# cell (n = 2^20)

## What row this is, and its eligibility

ADR-0373's LEFT row 4 ("Cross-day replication of the existing
`:subgroup-reduce` cells (needs a later-day cron tick)") continued: the
shape-2 part's fifth cell after the anchor and the last scheduled shape-2
cell -- W = 1024 at SHAPE 2 (n = 2^20), whose basis record is
docs/evidence/gpu-subgroup-reduce-m1max-shape2-band-20261023/w1024 (record
commit 14b30b84, 2026-10-23 12:56 JST -- the flip-set band record).

Eligibility, per the cell's OWN session date (the resweep record's
correction: "cross-day eligibility is per cell's OWN session date, not the
directory's date suffix"): both of this cell's sessions are 2026-10-23
daytime -- the basis session (shape2-band-20261023/w1024, record commit
14b30b84 12:56 JST) and the same-day re-session
(docs/evidence/gpu-subgroup-reduce-m1max-shape2-resweep-20261023/w1024,
record commit 90c9f697 16:39 JST -- that day's w1024 re-sweep, checked this
tick with `git log` on both shas). This run, 2026-10-24 14:35 JST, is a
later calendar day on the same host (Apple M1 Max, reported simdgroup size
32), the same conforming native-Metal channel (ADR-0360 question (1)'s
decision, the emitters' own bytes), the byte-identical protocol (6 fresh
processes, 20 interleaved AB/BA pairs per operator per run, 2 warmup
submits per arm discarded, verified read-back).

Named, not silent: both record commits are midday (12:56 / 16:39), so
there is no straddle question at this cell and its own later day is
today -- the same per-cell argument the earlier rows applied. The
2026-10-25 floor stays correct for the cells with unstamped run-logs; this
row claims nothing about them.

Driver (named verbatim, never paraphrased; the default --variant
subgroup-reduce is this family's compared arm; --elements equals the
shape-2 records' 1048576 and --op-order the default sum,max,min):

    python3 scripts/gpu-subgroup-reduce-metal-measure.py --runs 6
      --workgroup 1024 --elements 1048576 --op-order sum,max,min
      --out docs/evidence/gpu-subgroup-reduce-m1max-crossday-shape2-20261024/w1024
      --compare-historical docs/evidence/gpu-subgroup-reduce-m1max-shape2-band-20261023/w1024/summary.md

The emitted shaders are byte-identical to the basis cell's (`diff -r`
empty, checked this tick). The run-log reads n=1048576 (6 lines, checked
this tick) -- this run carries the requested shape. The classpath
resolution is the driver's named route 2 (`AMU_KBB_TEST_CLASSPATH`; route
1 `kbb -Spath -M:test` fails at the tree root, "no deps.edn" -- the merge
7b8f6488 retired deps.edn; the compile-log names the fallback route,
never silent).

Host condition, named because the machine was busy: load averages 87.67 /
106.59 / 102.82 at run start (uptime, 2026-10-24 14:35 JST). The harness
times Metal GPU timestamps, not host wall time (host submit->completion ns
recorded as secondary only).

## FINDING (real measurement, this host, this tick)

- This cell's own verdict (claim protocol rule 2): **REGIME-INVARIANT
  SLOWER** -- 18/18 per-run ratios above 1.0, every observed regime
  one-sided; paired median ratios 1.184/1.183/1.182 for :sum/:max/:min
  (:subgroup-reduce / :baseline gpu ns).
- Historical sessions of this cell (both 2026-10-23): the basis record
  1.183/1.166/1.167 and the same-day re-session 1.184/1.183/1.183
  (sum/max/min medians). This row's :sum sits within 0.001 of both
  sessions; :max/:min sit within 0.001 of the re-session's but 0.016-0.017
  above the basis's 1.166/1.167 -- that movement is what the rule-3
  machinery publishes as the split below, attributed to session mixing,
  never "failed to reproduce".
- The rule-3 regime-matched comparison against the basis record (the
  driver's --compare-historical auto-wiring): sign -- **"reproduces in
  sign strictly"** at every operator (all 6 per-run ratios hold the
  historical sign: slower, at each operator); magnitude -- **"magnitude
  reproduces within 0.001"** at :sum (matched-stratum delta 0.000) and
  **"magnitude splits by clock regime"** at :max and :min. Cell roll-up:
  sign -- reproduces in sign strictly (every operator); magnitude --
  magnitude splits by clock regime (mixed: max, min).
- The regime-matched datum: the :sum strata match (level 1 / level 1, all
  runs both sides, medians 1.183 / 1.184, delta 0.000). Unmatched
  historical levels: :max hist 1, 2 vs new 1; :min hist 1 vs new 1 --
  published in the summary's table, not hidden. The :max/:min splits are
  stratum-draw splits against the band record's wider level spread; the
  comparison is drawn across a level shift; the matched strata are
  gpu-ns-compatible, not verified clock identity.
- Rule 1 this run: ONE level at every operator (:max 132000..132500,
  :min 132000..132500, :sum 132125..132354) -- like the shape-2 w512 row,
  a pure single-level draw at every operator; cross-operator level
  identity HOLDS (15/15).
- Read-back: 36 verify lines, ok=1 on every one (ok=0: 0); :max/:min
  bit-exact vs the reference and between arms (24/24 lines); :sum
  max_abs_vs_ref 3.26633453e-05 (both arms) and max_abs_vs_other
  6.10351562e-05.
- Penalty band: this row 1.182..1.184. Cross-shape context on the same
  host: the shape-1 w1024 cross-day row rolled up magnitude PARTIAL
  (reproduces :sum/:max, splits :min) against ITS basis; this shape-2
  sibling splits at :max/:min instead and reproduces at :sum -- the two
  shapes' w1024 rows agree on the sign at every operator and on the
  ~18% penalty's presence at this width.

Series context (each record's own roll-up), the :subgroup-reduce
cross-day rows so far: shape-1 part -- w256 anchor sign strict /
magnitude "splits by clock regime (mixed: max, min, sum)"; w64 sign
strict / magnitude "splits (mixed: min)"; w128 sign does NOT reproduce
strictly (:max straddle) / magnitude splits; w512 sign strict and the
series' first cell-level magnitude REPRODUCTION (within 0.004); w1024
sign strict / magnitude PARTIAL (reproduces :sum/:max, splits :min).
Shape-2 part -- w256 anchor sign strict / magnitude "splits (mixed: max,
min)"; w64 sign strict / magnitude reproduces within 0.002 (the shape-2
part's first magnitude reproduction); w128 sign strict / magnitude
splits (mixed: min); w512 sign strict / magnitude splits (mixed: max,
min); THIS ROW w1024 sign strict / magnitude splits (mixed: max, min) --
the sign at this width replicates strictly at shape 2. With this row the
shape-2 part's SCHEDULED cells (anchor + four widths) are all replicated
cross-day.

## What this slice does NOT license

- No `:measured?` flag moves (the :baseline answers of the measured class
  were already MEASURED on the 2026-10-23 refutation; this run is
  corroboration of one cell's demotion basis at the second shape on a
  later day, nothing more). No selection answer changes and no workgroup
  row (ADR-0355/0358) is touched. W = 32 stays the decided cell
  (apple-w32-note): its answer is the low-band decision's, and this run
  says nothing about it. The shape-2 W = 32 cell's membership in the
  LEFT list stays OPEN (named in the anchor record).
- The :simdgroup-reduce family's shape-2 W = 512 REGIME-SCOPED refusal
  (its own summary: "regime-scoped (1 above 1.0, 17 below 1.0)") stands;
  resolving it is a protocol decision on the refusal's scope, not a
  re-run.
- This is a REPLICATION record, not a new measured cell: this tick
  changed no code namespace -- naming this record's family in
  accelerator-variants' apple-measured-evidence / apple-narrow-note is
  its own later slice (the same named debt every cross-day row carries).
  The variant's basis text and every map are unchanged by this commit.

## Gate (this tick changed no code namespace)

Run after the measurement, from the chain worktree root; classpath route 2
(AMU_KBB_TEST_CLASSPATH). Full output:
/Users/junkawasaki/.hermes/profiles/amu-gpu/cache/scratch/w1024-shape2-crossday-gate.txt

1. python3 scripts/gpu_regime_classify.py --self-test
   -> TOTAL: 1873 assertions passed, 0 failed.
      (1842 at the shape-2 w512 record; the +31 growth is this record
      joining the classified corpus.)
2. python3 scripts/gpu-subgroup-reduce-metal-measure.py --self-test
   -> driver auto-wiring self-test: 12 assertions passed, 0 failed.
3. Scoped GPU gate (the 8 GPU-owned test namespaces, scratch runner
   gpu_scoped_gate.cljk, not in the repo; classpath route 2,
   AMU_KBB_TEST_CLASSPATH):
     kbb --backend sci --classpath "src:test:$AMU_KBB_TEST_CLASSPATH" \
       /Users/junkawasaki/.hermes/profiles/amu-gpu/cache/scratch/gpu_scoped_gate.cljk
   -> Ran 102 tests containing 9728 assertions. 0 failures, 0 errors.
      scoped: 102 tests, 9728 passed, 0 failed, 0 errors
      (same counts as the previous tick -- this diff changed no code).
4. Full suite (run-tests.cljk): RED AT BASE, outside this diff, at
   namespace load on `kotoba.form` ("Could not find namespace:
   kotoba.form"; the W3 port path documented red at base in ADR 0362),
   re-verified live this tick. No green full suite is claimed.

## Honest LEFT (the real remainder after this row)

- The :subgroup-reduce cross-day replication list's scheduled cells are
  now complete at both shapes (shape 1 and shape 2, anchor + four widths
  each). The OPEN question named by the anchor record -- the W = 32
  cell's LEFT-list membership at shape 2 (and by symmetry at shape 1) --
  stays OPEN; W = 32 is the decided cell (apple-w32-note) and its
  membership is a decision row, not a measurement row.
- Cross-day replication of the :simdgroup-reduce cells other than the
  two measured rows (W = 256 anchor, W = 512): runnable 2026-10-25+
  (W = 32/64/128 and the shape-2 cells; W = 1024 treated as needing
  2026-10-25+, its run-log carries no date stamps).
- The shape-2 W = 512 REGIME-SCOPED refusal's scope decision (above).
- Naming the cross-day replication records in accelerator-variants'
  flip note / basis evidence lists (a docstring slice, with the scoped
  gate), and applying the same-day-resweep naming rule to this family's
  lists.
- The blocked rows stay exactly as prior records left them: no wire-42
  route (ADR 0371's provider not implemented), the GLSL arm stays
  LABELED BOOTSTRAP, every non-Apple vendor and every other Apple device
  UNMEASURED.
