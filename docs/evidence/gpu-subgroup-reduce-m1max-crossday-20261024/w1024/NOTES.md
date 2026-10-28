# NOTES -- the cross-day replication of the W = 1024 (shape 1) :subgroup-reduce cell

## What row this is, and its eligibility

ADR-0373's LEFT row 4 ("Cross-day replication of the existing
`:subgroup-reduce` cells (needs a later-day cron tick)") continued, in the
anchor replication record's own Honest LEFT ("Cross-day replication of the
remaining :subgroup-reduce cells -- shape 1 at W = 64/128/512/1024 and the
shape-2 cells -- each its own later-day MEASUREMENT row; eligibility per
the cell's own session date"). This is that later-day run, ONE cell:
W = 1024 (shape 1, n = 1,000,003) -- the fourth and LAST cell of the
list's shape-1 part (the W = 512 record named "W = 1024 is next in the
LEFT's order"; W = 64 first, W = 128 second, W = 512 third).

Eligibility, per the cell's OWN session date ("cross-day eligibility is
per cell's OWN session date, not the directory's date suffix"): this
cell's sessions are all 2026-10-23 daytime -- the basis session
(docs/evidence/gpu-subgroup-reduce-m1max-wsweep-20261023/w1024, record
commit 7c80f56f, 2026-10-23 10:09 JST) and the same-day re-session
(docs/evidence/gpu-subgroup-reduce-m1max-resweep-20261023/w1024, record
commit bc498816, 2026-10-23 14:53 JST). The run-logs carry no date
stamps; the record commits name the session dates. This run, 2026-10-24,
is a later calendar day on the same host (Apple M1 Max, reported simdgroup
size 32), the same conforming native-Metal channel (ADR-0360 question
(1)'s decision, the emitters' own bytes), the byte-identical protocol
(6 fresh processes, 20 interleaved AB/BA pairs per operator per run,
2 warmup submits per arm discarded, verified read-back).

Driver (named verbatim, never paraphrased; the default --variant
subgroup-reduce is this family's compared arm; --elements and --op-order
are passed explicitly and equal the defaults the wsweep cell used):

    python3 scripts/gpu-subgroup-reduce-metal-measure.py --runs 6
      --workgroup 1024 --elements 1000003 --op-order sum,max,min
      --out docs/evidence/gpu-subgroup-reduce-m1max-crossday-20261024/w1024
      --compare-historical docs/evidence/gpu-subgroup-reduce-m1max-wsweep-20261023/w1024/summary.md

The emitted shaders are byte-identical to the wsweep cell's (`diff -r`
empty, checked this tick). Classpath: the driver's named route 2
(`AMU_KBB_TEST_CLASSPATH`; route 1 `kbb -Spath -M:test` fails at the tree
root, "no deps.edn" -- the merge 7b8f6488 retired deps.edn; the
compile-log names the fallback route, never silent).

Host condition, named because the run took place on a busy machine:
load averages 22.18 / 23.38 / 22.23 at run start (uptime, 2026-10-24
13:04 JST). The harness times Metal GPU timestamps, not host wall time
(host submit->completion ns is recorded as secondary only).

## FINDING (real measurement, this host, this tick)

The shape-1 remaining list closes with the cross-day series' first
PARTIAL magnitude reproduction: this row replicates in sign strictly at
every operator, reproduces in magnitude at :sum and :max, and splits by
clock regime at :min only -- the first row of the series whose magnitude
phrase differs by operator instead of being one cell-level phrase.

- Paired median ratios (:subgroup-reduce / :baseline gpu ns):
  1.186 / 1.182 / 1.181 for :sum/:max/:min. Per-run: sum 1.186, 1.185,
  1.185, 1.183, 1.187, 1.187; max 1.183, 1.186, 1.182, 1.169, 1.192,
  1.170; min 1.183, 1.181, 1.183, 1.180, 1.171, 1.168. All 18 per-run
  ratios above 1.0 -- no sub-1.0 ratio anywhere in this row.
- This cell's own verdict (claim protocol rule 2): **REGIME-INVARIANT
  SLOWER** -- every operator 6/6 slower, every observed regime one-sided;
  cell roll-up 18/18 slower.
- The rule-3 regime-matched comparison against the wsweep record (the
  driver's --compare-historical auto-wiring): sign -- "reproduces in sign
  strictly" at all three operators (every per-run ratio holds the
  historical sign); magnitude -- "magnitude reproduces within 0.000"
  (:sum), "within 0.004" (:max), "magnitude splits by clock regime"
  (:min). Cell roll-up: sign -- reproduces in sign strictly (every
  operator); magnitude -- magnitude splits by clock regime (mixed: min).
  The median-draw column (the runs whose ratios draw each operator's
  median, and the rule-1 levels they sit in): sum "pure (level 1, runs
  2, 3, 5) / pure (level 1, runs 1, 2, 3)"; max "pure (level 1, runs 1,
  3) / pure (level 4, runs 1, 3)"; min "pure (level 1, runs 3, 5) /
  mixed (level 2: runs 4; level 3: runs 2)" -- the :min split is that
  mixed draw, one member in an unmatched new level. Within matched
  strata the deltas are 0.000 / 0.003 / 0.002 (sum/max/min):
  1.186/1.185 (sum, all 6/6 runs matched at level 1/1), 1.186/1.183
  (max, hist level 1 / new level 4), 1.185/1.183 (min, hist level 1 /
  new level 3). The unmatched new levels (max 1, 2, 3 = runs 4, 5, 6;
  min 1, 2 = runs 4, 5, 6) are published in the summary's table, not
  hidden.
- Cross-day series context (the five rows' cell roll-ups, quoted from
  each record's summary.md): w256 anchor -- sign strict, magnitude
  "splits by clock regime"; w64 -- sign strict, magnitude "splits by
  clock regime (mixed: min)"; w128 -- sign does NOT reproduce strictly
  (:max straddle), magnitude "splits by clock regime"; w512 -- sign
  strict and the series' only cell-level magnitude REPRODUCTION so far;
  this row (w1024) -- sign strict at every operator, magnitude
  reproduces at :sum/:max but the cell roll-up still "splits by clock
  regime" on the :min draw. This does not re-scope the w128 row: that
  row's single sub-1.0 ratio (run 1 at :max) stands named in its own
  record, and one row's clean replication is not evidence about another
  row's sign.
- Penalty band by cell (the five cross-day rows' median ratios): w1024
  1.181..1.186 is the series' lowest band (w512 1.193..1.197, w256
  1.212..1.220, w64 1.216..1.220, w128 1.227..1.245) -- the MSL arm's
  penalty keeps narrowing with W on a later day, mirroring the wsweep
  day's own 1.22 -> 1.19 trend.
- Historical sessions of this cell (both 2026-10-23): the wsweep record
  1.186/1.186/1.185 and the same-day re-session 1.185/1.177/1.172
  (sum/max/min medians). This row's max/min medians (1.182/1.181) sit
  between the two historical draws, consistent with the re-session
  record's named regime term ("the ratio's magnitude carries a small
  regime term here"; its PROPOSED cross-regime verdict protocol stays
  PROPOSED, decided nowhere).
- Rule 1 this run: four levels at :max (40500 / 52750 / 66854 /
  128458..128604), three at :min (40562..40625 / 53021 /
  128312..128562), one at :sum (128188..128562); cross-operator level
  identity REFUTED (12 of 15 run pairs diverge). The intra-session
  clock-regime shift the resweep record named at this W recurs (baseline
  per-run medians fall ~128k -> ~40k gpu ns across the six processes at
  :max/:min; :sum stayed at the ~128k level throughout).
- Read-back: 36 verify lines, ok=1 on every one (ok=0: 0); :max/:min
  bit-exact vs the reference and between arms (24/24 lines); :sum
  max_abs_vs_ref 3.26633453e-05 and max_abs_vs_other 6.10351562e-05 --
  the exact figures of the historical wsweep w1024 cell.

## What this slice does NOT license

- No `:measured?` flag moves: the :baseline answers of the measured class
  were already MEASURED on the 2026-10-23 refutation; this run is
  corroboration of one cell's demotion basis (W = 1024, shape 1) on a
  later day, nothing more. No selection answer changes and no workgroup
  row (ADR-0355/0358) is touched.
- W = 32 stays the decided cell (apple-w32-note); this run says nothing
  about it. The shape-2 cells are the LEFT list's remainder -- they keep
  their 2026-10-23 basis until their own later-day runs; eligibility per
  the cell's own session date.
- The :simdgroup-reduce family is untouched; its remaining cross-day rows
  are its own (runnable 2026-10-25+ per its record). The shape-2 W = 512
  measured-but-REFUSED cell (that family's) stands: replication of a
  REFUSED cell is its own decision, not a way to re-run a refusal.
- This is a REPLICATION record, not a new measured cell: this tick
  changed no code namespace -- naming this record (and the anchor's, W =
  64's, W = 128's and W = 512's) in accelerator-variants'
  apple-measured-evidence / apple-narrow-note, and applying the
  same-day-re-session naming rule to this family's lists, are their own
  later slices. The record's basis text and every map are unchanged by
  this commit.

## Gate (this tick changed no code namespace)

1. python3 scripts/gpu_regime_classify.py --self-test
   -> TOTAL: 1718 assertions passed, 0 failed
      (1687 at the W = 512 record; the growth is this record joining the
      corpus the self-test classifies).
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
   re-verified live this tick. No green full suite is claimed. The
   canonical gate line's classpath leg `$(kbb -Spath -M:test)` itself
   fails at the current tree root ("no deps.edn", the merge 7b8f6488);
   the run used the same named route 2 closure as the measurement
   driver, and the failure it reaches is the same documented base
   failure.
