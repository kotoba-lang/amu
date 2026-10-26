# NOTES -- the cross-day replication of the W = 64 (shape 1) :subgroup-reduce cell

## What row this is, and its eligibility

ADR-0373's LEFT row 4 ("Cross-day replication of the existing
`:subgroup-reduce` cells (needs a later-day cron tick)") continued, in the
anchor replication record's own Honest LEFT ("Cross-day replication of the
remaining :subgroup-reduce cells -- shape 1 at W = 64/128/512/1024 and the
shape-2 cells -- each its own later-day MEASUREMENT row; eligibility per
the cell's own session date"). This is that later-day run, ONE cell:
W = 64 (shape 1, n = 1,000,003), the first cell of that LEFT list.

Eligibility, per the cell's OWN session date (the resweep record's
correction: "cross-day eligibility is per cell's OWN session date, not the
directory's date suffix"): this cell's sessions are all 2026-10-23
daytime -- the basis session (docs/evidence/
gpu-subgroup-reduce-m1max-wsweep-low-20261023/w64, record commit
2026-10-23 11:15 JST) and the same-day re-session
(docs/evidence/gpu-subgroup-reduce-m1max-resweep-20261023/w64, record
commit 2026-10-23 15:07 JST). The run-logs carry no date stamps; the
record commits name the session dates (the anchor record's idiom). This
run, 2026-10-24, is a later calendar day on the same host (Apple M1 Max,
reported simdgroup size 32), the same conforming native-Metal channel
(ADR-0360 question (1)'s decision, the emitters' own bytes), the
byte-identical protocol (6 fresh processes, 20 interleaved AB/BA pairs
per operator per run, 2 warmup submits per arm discarded, verified
read-back).

Driver (named verbatim, never paraphrased; the default --variant
subgroup-reduce is this family's compared arm; --elements and --op-order
are passed explicitly and equal the defaults the wsweep-low cell used):

    python3 scripts/gpu-subgroup-reduce-metal-measure.py --runs 6
      --workgroup 64 --elements 1000003 --op-order sum,max,min
      --out docs/evidence/gpu-subgroup-reduce-m1max-crossday-20261024/w64
      --compare-historical docs/evidence/gpu-subgroup-reduce-m1max-wsweep-low-20261023/w64/summary.md

The emitted shaders are byte-identical to the wsweep-low cell's
(`diff -r` empty, checked this tick). Classpath: the driver's named
route 2 (`AMU_KBB_TEST_CLASSPATH`; route 1 `kbb -Spath -M:test` fails at
the tree root, "no deps.edn" -- the merge 7b8f6488 retired deps.edn; the
compile-log names the fallback route, never silent).

## FINDING (real measurement, this host, this tick)

- This cell's own verdict (claim protocol rule 2): **REGIME-INVARIANT
  SLOWER** -- 18/18 per-run ratios above 1.0, every observed regime
  one-sided; paired median ratios 1.220/1.216/1.217 for :sum/:max/:min
  (:subgroup-reduce / :baseline gpu ns).
- The historical cell (2026-10-23 11:15) recorded 1.221/1.216/1.202 --
  the ~22% penalty band the demotion rests on reproduces on a later day.
- The rule-3 regime-matched comparison against that record (the driver's
  --compare-historical auto-wiring): sign -- **"reproduces in sign
  strictly"** at every operator (all 6 per-run ratios hold the historical
  sign: slower, at each); magnitude -- "magnitude reproduces within
  0.001" for :sum and "within 0.000" for :max, **"magnitude splits by
  clock regime"** for :min (mixed strata draws). The regime-matched
  datum (within-stratum deltas): sum 0.000 (strata 1/1, all runs both
  days, 1.220/1.220); max 0.000 (matched strata 3/1, runs 1,5,6 / 1-6,
  1.216/1.216); min 0.001 (matched strata 3/1, run 1 / runs 1-6,
  1.217/1.216). The cell roll-up: sign "reproduces in sign strictly"
  (every operator); magnitude "magnitude splits by clock regime" (mixed:
  min). The claim names the split and attributes it to session mixing --
  never "failed to reproduce". Note the shape of this row: the RAW :min
  median moved 1.202 -> 1.217 across days, but the matched-stratum delta
  is 0.001 -- the raw-median movement is the historical day's mixed
  regime draw, not a magnitude change; this is exactly why the
  comparison is published regime-matched.
- Read-back: 36 verify lines, ok=1 on every one (ok=0: 0); :max/:min
  bit-exact vs the reference and between arms (24/24 lines); :sum
  max_abs_vs_ref 3.4570694e-06 (baseline) / 4.529953e-06 (variant) and
  max_abs_vs_other 3.81469727e-06 (regrouping) -- the same figures the
  historical cell recorded.
- Rule 1 this run: ONE level at every operator (baseline per-run medians
  91833..92188), and cross-operator level identity **HOLDS** (15/15 run
  pairs agree). The historical day's record is identity-REFUTED (13
  divergent pairs; levels max 3, min 3, sum 1) -- the two days sampled
  different regime structures, which is why the comparison is published
  regime-matched and not as raw-median agreement.

## What this slice does NOT license

- No `:measured?` flag moves: the :baseline answers of the measured
  class (W = 64/128/256/512/1024) were already MEASURED on the
  2026-10-23 refutation; this run is corroboration of one cell's demotion
  basis (W = 64, shape 1) on a later day, nothing more. No selection
  answer changes and no workgroup row (ADR-0355/0358) is touched.
- W = 32 stays the decided cell (apple-w32-note): its answer is the
  low-band decision's, and this run says nothing about it. The shape-1
  W = 128/512/1024 cells and the shape-2 cells keep their 2026-10-23
  basis until their own later-day runs. On the eligibility evidence
  checked this tick (record commits): the remaining shape-1 cells'
  sessions are 2026-10-23 daytime (W = 512/W = 1024 at commit
  2026-10-23 10:09, W = 128 at 11:15; the re-sweep series 14:38-15:34),
  and the shape-2 cells' are too (12:11, 12:56 and their re-sweeps) --
  so a 2026-10-24 run is a later-day run for each of them; the anchor
  record's "2026-10-25 runs qualify for every remaining cell regardless
  of straddle questions" stays true and is the conservative date it
  named. W = 128 is next in the LEFT's order.
- The :simdgroup-reduce family is untouched; its remaining cross-day rows
  are its own (runnable 2026-10-25+ per its record). The shape-2 W = 512
  measured-but-REFUSED cell (that family's) stands: replication of a
  REFUSED cell is its own decision, not a way to re-run a refusal.
- This is a REPLICATION record, not a new measured cell: this tick
  changed no code namespace -- naming this record (and the anchor's) in
  accelerator-variants' apple-measured-evidence / apple-narrow-note, and
  applying the same-day-re-session naming rule to this family's lists,
  are their own later slices. The record's basis text and every map are
  unchanged by this commit.

## Gate (this tick changed no code namespace)

1. python3 scripts/gpu_regime_classify.py --self-test
   -> TOTAL: 1624 assertions passed, 0 failed.
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
