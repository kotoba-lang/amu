# NOTES -- the cross-day replication of the :subgroup-reduce shape-2 ANCHOR cell (W = 256, n = 2^20)

## What row this is, and its eligibility

ADR-0373's LEFT row 4 ("Cross-day replication of the existing
`:subgroup-reduce` cells (needs a later-day cron tick)") continued, in the
previous row's own closing words ("The shape-2 cells are the LEFT list's
remainder and keep their 2026-10-23 basis until their own later-day
runs"). This is that later-day run, ONE cell, the shape-2 part's anchor:
W = 256 (the anchor of the flip set) at SHAPE 2 (n = 2^20), whose basis
record is docs/evidence/gpu-subgroup-reduce-m1max-shape2-20261023/w256
(record commit 713be46b, 2026-10-23 12:11 JST).

Eligibility, per the cell's OWN session date (the resweep record's
correction: "cross-day eligibility is per cell's OWN session date, not the
directory's date suffix"): both of this cell's sessions are 2026-10-23
daytime -- the basis session (shape2-20261023/w256, record commit 713be46b
12:11 JST) and the same-day re-session
(docs/evidence/gpu-subgroup-reduce-m1max-shape2-resweep-20261023/w256,
record commit f8b15f25 15:51 JST). This run, 2026-10-24 13:24 JST, is a
later calendar day on the same host (Apple M1 Max, reported simdgroup
size 32), the same conforming native-Metal channel (ADR-0360 question
(1)'s decision, the emitters' own bytes), the byte-identical protocol (6
fresh processes, 20 interleaved AB/BA pairs per operator per run, 2
warmup submits per arm discarded, verified read-back).

Named, not silent: the previous row's Honest LEFT put "2026-10-25 runs
qualify for every remaining cell regardless of straddle questions" as the
floor that covers ALL remaining cells at once. This cell has no straddle
question at all (both record commits are midday), so its own later day is
today -- the same per-cell argument the shape-1 rows used ("both sessions
2026-10-23 daytime ... so this 2026-10-24 run is a later-day run"). The
2026-10-25 floor stays correct for the cells with unstamped run-logs;
this row claims nothing about them.

Driver (named verbatim, never paraphrased; the default --variant
subgroup-reduce is this family's compared arm; --elements equals the
shape-2 records' 1048576 and --op-order the default sum,max,min):

    python3 scripts/gpu-subgroup-reduce-metal-measure.py --runs 6
      --workgroup 256 --elements 1048576 --op-order sum,max,min
      --out docs/evidence/gpu-subgroup-reduce-m1max-crossday-shape2-20261024/w256
      --compare-historical docs/evidence/gpu-subgroup-reduce-m1max-shape2-20261023/w256/summary.md

The emitted shaders are byte-identical to the basis cell's (`diff -r`
empty, checked this tick). The run-log reads n=1048576 (checked this
tick) -- the shape2-band record's shape-forwarding defect (`argc == 4`)
is fixed (`argc >= 4`) and this run carries the requested shape. The
classpath resolution is the driver's named route 2
(`AMU_KBB_TEST_CLASSPATH`; route 1 `kbb -Spath -M:test` fails at the tree
root, "no deps.edn" -- the merge 7b8f6488 retired deps.edn; the
compile-log names the fallback route, never silent).

Host condition, named because the machine was busy: load averages 37.74 /
36.88 / 31.42 at run start (uptime, 2026-10-24 13:24 JST). The harness
times Metal GPU timestamps, not host wall time (host submit->completion ns
recorded as secondary only).

## FINDING (real measurement, this host, this tick)

- This cell's own verdict (claim protocol rule 2): **REGIME-INVARIANT
  SLOWER** -- 18/18 per-run ratios above 1.0, every observed regime
  one-sided; paired median ratios 1.226/1.223/1.224 for :sum/:max/:min
  (:subgroup-reduce / :baseline gpu ns).
- Historical sessions of this cell (both 2026-10-23): the basis record
  1.227/1.223/1.220 and the same-day re-session 1.226/1.225/1.225
  (sum/max/min medians). This row's medians sit inside that day's span --
  the ~22% penalty band the demotion rests on reproduces at the second
  shape on a later day.
- The rule-3 regime-matched comparison against the basis record (the
  driver's --compare-historical auto-wiring): sign -- **"reproduces in
  sign strictly"** at every operator (all 6 per-run ratios hold the
  historical sign: slower, at each operator); magnitude -- "magnitude
  reproduces within 0.001" (:sum) and "magnitude splits by clock regime"
  (:max, :min) -- mixed strata draws at :max/:min. Cell roll-up: sign --
  reproduces in sign strictly (every operator); magnitude -- magnitude
  splits by clock regime (mixed: max, min).
- The regime-matched datum: within-stratum deltas 0.000 (:sum, all 6/6
  runs matched at level 1/1), 0.006 / 0.003 (:max, matched stratum pairs
  1/3 and 2/4) and 0.009 / 0.001 (:min, pairs 1/1 and 5/3). The unmatched
  levels (historical min levels 2, 3, 4; new max levels 1, 2 and new min
  level 2) are published in the summary's table, not hidden. The claim
  names the split and attributes it to session mixing -- never "failed to
  reproduce".
- Rule 1 this run: four levels at :max (34000 / 44250 / 86000 /
  107271..107750), three at :min (34146..34375 / 64979 /
  107500..107562), one at :sum (107312..107938); cross-operator level
  identity REFUTED (12 of 15 run pairs) -- the intra-session clock-regime
  shift the shape-1 rows name at this W recurs (baseline per-run medians
  fall ~107k -> ~34k gpu ns across the six processes at :max/:min; :sum
  stayed at the ~107k level throughout).
- Read-back: 36 verify lines, ok=1 on every one (ok=0: 0); :max/:min
  bit-exact vs the reference and between arms (24/24 lines); :sum
  max_abs_vs_ref 1.57952309e-05 and max_abs_vs_other 3.05175781e-05.
- Penalty band: this row 1.223..1.226. Cross-shape context on the same
  later day: the shape-1 anchor's cross-day row (earlier today) recorded
  1.212..1.220 against ITS basis 1.216..1.223 -- the shape-2 anchor sits
  within a couple of points of its shape-1 sibling, and at both shapes
  the anchor cell is sign-strict with a mixed-draw magnitude phrase.

Series context (each record's own roll-up), the :subgroup-reduce
cross-day rows so far: shape-1 part -- w256 anchor sign strict /
magnitude "splits by clock regime"; w64 sign strict / magnitude "splits
by clock regime (mixed: min)"; w128 sign does NOT reproduce strictly
(:max straddle) / magnitude "splits by clock regime"; w512 sign strict
and the series' only cell-level magnitude REPRODUCTION; w1024 sign
strict at every operator / magnitude reproduces at :sum/:max but splits
on the :min draw (PARTIAL). This row opens the shape-2 part with the
anchor cell: sign strict at every operator, magnitude splits on the
:max/:min draws -- the same roll-up shape as its own shape-1 sibling
row.

## What this slice does NOT license

- No `:measured?` flag moves (the :baseline answers of the measured class
  were already MEASURED on the 2026-10-23 refutation; this run is
  corroboration of one cell's demotion basis at the second shape on a
  later day, nothing more). No selection answer changes and no workgroup
  row (ADR-0355/0358) is touched. W = 32 stays the decided cell
  (apple-w32-note): its answer is the low-band decision's, and this run
  says nothing about it.
- This is a REPLICATION record, not a new measured cell: this tick
  changed no code namespace -- naming this record's family in
  accelerator-variants' apple-measured-evidence / apple-narrow-note is
  its own later slice (the same named debt the shape-1 rows carry). The
  variant's basis text and every map are unchanged by this commit.

## Gate (this tick changed no code namespace)

1. python3 scripts/gpu_regime_classify.py --self-test
   -> TOTAL: 1749 assertions passed, 0 failed.
      (1718 at the W = 1024 shape-1 record; the growth is this record
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

- Cross-day replication of the remaining :subgroup-reduce shape-2 cells
  -- W = 64/128/512/1024, each its own later-day MEASUREMENT row. The
  shape-2 W = 32 cell's membership in "the shape-2 cells" of the LEFT
  list is NOT settled by any record (the shape-1 part excluded W = 32 as
  the decided cell; the LEFT list's phrase does not say either way) --
  it stays OPEN here rather than assumed in either direction.
- Cross-day replication of the :simdgroup-reduce cells other than the
  two measured rows (W = 256 anchor, W = 512): runnable 2026-10-25+
  (W = 32/64/128 and the shape-2 cells; W = 1024 treated as needing
  2026-10-25+, its run-log carries no date stamps).
- The shape-2 W = 512 REGIME-SCOPED refusal stands; resolving it is a
  protocol decision on the refusal's scope, not a re-run.
- Naming this replication record in accelerator-variants' flip note /
  basis evidence lists (a docstring slice, with the scoped gate), and
  applying the same-day-resweep naming rule to this family's lists.
- The blocked rows stay exactly as prior records left them: no wire-42
  route (ADR 0371's provider not implemented), the GLSL arm stays
  LABELED BOOTSTRAP, every non-Apple vendor and every other Apple device
  UNMEASURED.
