# NOTES -- the cross-day replication of the :subgroup-reduce shape-2 W = 512
# cell (n = 2^20)

## What row this is, and its eligibility

ADR-0373's LEFT row 4 ("Cross-day replication of the existing
`:subgroup-reduce` cells (needs a later-day cron tick)") continued: the
shape-2 part's fourth cell after the anchor, ONE cell -- W = 512 at SHAPE 2
(n = 2^20), whose basis record is
docs/evidence/gpu-subgroup-reduce-m1max-shape2-band-20261023/w512 (record
commit 14b30b84, 2026-10-23 12:56 JST -- the flip-set band record whose
four cells land in one commit, each cell's run logged before it).

Eligibility, per the cell's OWN session date (the resweep record's
correction: "cross-day eligibility is per cell's OWN session date, not the
directory's date suffix"): both of this cell's sessions are 2026-10-23
daytime -- the basis session (shape2-band-20261023/w512, record commit
14b30b84 12:56 JST) and the same-day re-session
(docs/evidence/gpu-subgroup-reduce-m1max-shape2-resweep-20261023/w512,
record commit f3a0e1ea 16:50 JST -- that day's w512 re-sweep). This run,
2026-10-24 14:19 JST, is a later calendar day on the same host (Apple M1
Max, reported simdgroup size 32), the same conforming native-Metal channel
(ADR-0360 question (1)'s decision, the emitters' own bytes), the
byte-identical protocol (6 fresh processes, 20 interleaved AB/BA pairs per
operator per run, 2 warmup submits per arm discarded, verified read-back).

Named, not silent: both record commits are midday (12:56 / 16:50), so
there is no straddle question at this cell and its own later day is
today -- the same per-cell argument the shape-1 rows and the shape-2
anchor, w64 and w128 rows applied. The 2026-10-25 floor stays correct for
the cells with unstamped run-logs; this row claims nothing about them.

Driver (named verbatim, never paraphrased; the default --variant
subgroup-reduce is this family's compared arm; --elements equals the
shape-2 records' 1048576 and --op-order the default sum,max,min):

    python3 scripts/gpu-subgroup-reduce-metal-measure.py --runs 6
      --workgroup 512 --elements 1048576 --op-order sum,max,min
      --out docs/evidence/gpu-subgroup-reduce-m1max-crossday-shape2-20261024/w512
      --compare-historical docs/evidence/gpu-subgroup-reduce-m1max-shape2-band-20261023/w512/summary.md

The emitted shaders are byte-identical to the basis cell's (`diff -r`
empty, checked this tick). The run-log reads n=1048576 (checked this tick)
-- the shape2-band record's shape-forwarding defect (`argc == 4`, fixed
`argc >= 4` in that same record) is fixed and this run carries the
requested shape. The classpath resolution is the driver's named route 2
(`AMU_KBB_TEST_CLASSPATH`; route 1 `kbb -Spath -M:test` fails at the tree
root, "no deps.edn" -- the merge 7b8f6488 retired deps.edn; the
compile-log names the fallback route, never silent).

Host condition, named because the machine was busy: load averages 99.58 /
97.78 / 85.20 at run start (uptime, 2026-10-24 14:19 JST). The harness
times Metal GPU timestamps, not host wall time (host submit->completion ns
recorded as secondary only).

## FINDING (real measurement, this host, this tick)

- This cell's own verdict (claim protocol rule 2): **REGIME-INVARIANT
  SLOWER** -- 18/18 per-run ratios above 1.0, every observed regime
  one-sided; paired median ratios 1.200/1.193/1.192 for :sum/:max/:min
  (:subgroup-reduce / :baseline gpu ns).
- Historical sessions of this cell (both 2026-10-23): the basis record
  1.200/1.192/1.187 and the same-day re-session 1.202/1.195/1.197
  (sum/max/min medians). This row's medians sit within 0.000-0.005 of
  that day's span -- the ~19-20% penalty band at this width reproduces on
  a later day.
- The rule-3 regime-matched comparison against the basis record (the
  driver's --compare-historical auto-wiring): sign -- **"reproduces in
  sign strictly"** at every operator (all 6 per-run ratios hold the
  historical sign: slower, at each operator); magnitude -- **"magnitude
  reproduces within 0.000"** at :sum and **"magnitude splits by clock
  regime"** at :max and :min. Cell roll-up: sign -- reproduces in sign
  strictly (every operator); magnitude -- magnitude splits by clock
  regime (mixed: max, min).
- The regime-matched datum: within-stratum deltas 0.001 (:max, matched
  stratum pair 4/1), 0.002 (:min, 2/1) and 0.000 (:sum, 2/1). Unmatched
  historical levels: :max hist 1, 2, 3; :min hist 1; :sum hist 1 (the
  band record's wider level spread, including its fast-regime runs);
  nothing new unmatched -- published in the summary's table, not hidden.
  The :max/:min splits are stratum-draw splits, not magnitude movements:
  the historical median draws are mixed (level 2 at :max runs 1; level 3
  run 4; level 4 run 3 -- :min level 1 run 1, level 2 run 4) against this
  row's pure level-1 draw at every operator, and the matched-stratum
  deltas there are 0.001-0.002. The comparison is drawn across a level
  shift; the matched strata are gpu-ns-compatible, not verified clock
  identity.
- Rule 1 this run: ONE level at every operator (:max 119125..119625,
  :min 119250..121438, :sum 119229..119520) -- the first row of this
  cross-day series with a pure single-level draw at every operator;
  cross-operator level identity HOLDS (15/15) -- like the shape-2 w64
  row, unlike the shape-2 w128 row's REFUTED (5/15).
- Read-back: 36 verify lines, ok=1 on every one (ok=0: 0); :max/:min
  bit-exact vs the reference and between arms (24/24 lines); :sum
  max_abs_vs_ref 1.63316727e-05 (both arms) and max_abs_vs_other
  3.05175781e-05 -- the band cell's exact figures.
- Penalty band: this row 1.192..1.200. Cross-shape context on the same
  host: the shape-1 w512 cross-day row recorded 1.193..1.197 against ITS
  basis and rolled up magnitude "reproduces within 0.004" -- this shape-2
  sibling's medians sit within a couple of points of it; the roll-up
  difference (this row's :max/:min stratum-draw splits) is a draw
  difference at matched-stratum deltas 0.001-0.002, not a magnitude
  difference.

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
splits (mixed: min); THIS ROW w512 sign strict / magnitude splits
(mixed: max, min) -- the sign at this width replicates strictly at
shape 2, and the ~19-20% band reproduces, at every operator.

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
  re-run. This family's own shape-2 W = 512 is the cell this row just
  measured -- a different cell from the refusing one.
- This is a REPLICATION record, not a new measured cell: this tick
  changed no code namespace -- naming this record's family in
  accelerator-variants' apple-measured-evidence / apple-narrow-note is
  its own later slice (the same named debt every cross-day row carries).
  The variant's basis text and every map are unchanged by this commit.

## Gate (this tick changed no code namespace)

Run after the measurement, from the chain worktree root; classpath route 2
(AMU_KBB_TEST_CLASSPATH). Full output:
/Users/junkawasaki/.hermes/profiles/amu-gpu/cache/scratch/w512-shape2-crossday-gate.txt

1. python3 scripts/gpu_regime_classify.py --self-test
   -> TOTAL: 1842 assertions passed, 0 failed.
      (1811 at the shape-2 w128 record; the +31 growth is this record
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

- Cross-day replication of the remaining :subgroup-reduce shape-2 cell
  -- W = 1024, its own later-day MEASUREMENT row. Its two sessions are
  pinned by record commits to 2026-10-23 daytime (band 14b30b84 12:56;
  re-session 90c9f697 16:39), so any later-day run qualifies per the
  per-cell rule. The shape-2 W = 32 cell's LEFT-list membership stays
  OPEN.
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
