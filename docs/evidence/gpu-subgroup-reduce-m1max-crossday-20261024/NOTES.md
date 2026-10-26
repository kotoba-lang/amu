# NOTES -- the cross-day replication of the :subgroup-reduce ANCHOR cell (W = 256, shape 1)

## What row this is

ADR-0373's LEFT row 4 -- "Cross-day replication of the existing
`:subgroup-reduce` cells (needs a later-day cron tick)" -- and the
":subgroup-reduce family's" own later-day row of the same claim protocol
that governs the :simdgroup-reduce cross-day rows ("Cross-day replication
of any cell needs a later-day run (a cron tick on another day), not more
same-day sessions"). This is that later-day run, ONE cell: the anchor
(W = 256, n = 1,000,003, shape 1), whose original record is
docs/evidence/gpu-subgroup-reduce-m1max-20261023 (the MSL arm's first
hardware run, measured 2026-10-23 morning -- the record landed in commit
009c86ef at 08:34 JST that day, so the cell's own session date is
2026-10-23 unambiguously: no midnight straddle, unlike the :simdgroup-reduce
W = 1024 cell's run-log; this run 2026-10-24 is a later calendar day).

This replication ran 2026-10-24 on the same host (Apple M1 Max, reported
simdgroup size 32) through the same conforming native-Metal channel
(ADR-0360 question (1)'s decision, the emitters' own bytes), the
byte-identical protocol (6 fresh processes, 20 interleaved AB/BA pairs
per operator per run, 2 warmup submits per arm discarded, verified
read-back).

Driver (named verbatim, never paraphrased; the default --variant
subgroup-reduce is this family's compared arm):

    python3 scripts/gpu-subgroup-reduce-metal-measure.py --runs 6
      --workgroup 256 --elements 1000003 --op-order sum,max,min
      --out docs/evidence/gpu-subgroup-reduce-m1max-crossday-20261024/w256
      --compare-historical docs/evidence/gpu-subgroup-reduce-m1max-20261023/summary.md

The emitted shaders are byte-identical to the anchor record's (`diff -r`
empty, checked this tick). The classpath resolution is the driver's named
route 2 (`AMU_KBB_TEST_CLASSPATH`, the same `kbb -Spath -M:test` closure
the retired deps.edn resolved -- the merge 7b8f6488 removed deps.edn from
every current tree root; the compile-log names the fallback route, never
silent).

## FINDING (real measurement, this host, this tick)

- This cell's own verdict (claim protocol rule 2): **REGIME-INVARIANT
  SLOWER** -- 18/18 per-run ratios above 1.0, every observed regime
  one-sided; paired median ratios 1.220/1.216/1.212 for :sum/:max/:min
  (:subgroup-reduce / :baseline gpu ns).
- The historical anchor (2026-10-23) recorded 1.223/1.218/1.216 -- the
  ~22% penalty band the demotion rests on reproduces unchanged.
- The rule-3 regime-matched comparison against that record (the driver's
  --compare-historical auto-wiring): sign -- **"reproduces in sign
  strictly"** at every operator (all 6 per-run ratios hold the historical
  sign: slower, at each operator); magnitude -- "magnitude splits by
  clock regime" for all three operators (mixed strata draws -- the two
  sessions sampled different rule-1 level mixes). The regime-matched
  datum: within-stratum deltas 0.000-0.014 (max: 0.014 / 0.002 / 0.000 at
  matched strata 2/3/4; min: 0.002 / 0.000 / 0.001 at 1/2/4; sum: 0.002
  at the 2/1 draw). The claim names the split and attributes it to
  session mixing -- never "failed to reproduce".
- Read-back: 36 verify lines, ok=1 on every one; :max/:min bit-exact vs
  the reference and between arms; :sum 1.58e-05 vs the reference and
  3.05e-05 between arms (regrouping) -- the same figures as the anchor.
- Rule 1 this run: one level for :sum, four for :max, four for :min;
  cross-operator level identity REFUTED (12/15 run pairs) -- the regime
  structure differs from the anchor day's (the anchor sampled two levels
  in :max/:min), which is exactly why the comparison is published
  regime-matched and not as raw-median agreement.

## What this slice does NOT license

- No `:measured?` flag moves: the :baseline answers of the measured class
  (W = 64/128/256/512/1024) were already MEASURED on the 2026-10-23
  refutation; this run is corroboration of one cell's demotion basis
  (W = 256, shape 1) on a later day, nothing more. No selection answer
  changes and no workgroup row (ADR-0355/0358) is touched.
- W = 32 stays the decided cell (apple-w32-note): its answer is the
  low-band decision's, and this run says nothing about it. The other
  four W cells (64/128/512/1024) and the shape-2 cells keep their
  2026-10-23 basis until their own later-day runs.
- The :simdgroup-reduce family is untouched: its cross-day rows are its
  own (the W = 256 anchor and W = 512 rows already measured 2026-10-24;
  the rest runnable 2026-10-25+), and the shape-2 W = 512
  measured-but-REFUSED cell stands (replication of a REFUSED cell is its
  own decision, not a way to re-run a refusal).
- This is a REPLICATION record, not a new measured cell: this tick
  changed no code namespace -- naming this record in
  accelerator-variants' apple-measured-evidence / apple-narrow-note (and
  applying the same-day-re-session naming rule to this family's lists,
  the naming decision's own named follow-through) is its own later
  slice. The record's basis text and every map are unchanged by this
  commit.

## Gate (this tick changed no code namespace)

1. python3 scripts/gpu_regime_classify.py --self-test
   -> TOTAL: 1593 assertions passed, 0 failed.
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

- Cross-day replication of the remaining :subgroup-reduce cells -- shape
  1 at W = 64/128/512/1024 and the shape-2 cells -- each its own
  later-day MEASUREMENT row (eligibility per the cell's own session
  date; the shape-2 and W = 32/64/128 family cells ran 2026-10-23
  daytime by their record commits, so 2026-10-25 runs qualify for every
  remaining cell regardless of straddle questions).
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
