# NOTES -- the cross-day replication of the W = 512 (shape 1) :subgroup-reduce cell

## What row this is, and its eligibility

ADR-0373's LEFT row 4 ("Cross-day replication of the existing
`:subgroup-reduce` cells (needs a later-day cron tick)") continued, in the
anchor replication record's own Honest LEFT ("Cross-day replication of the
remaining :subgroup-reduce cells -- shape 1 at W = 64/128/512/1024 and the
shape-2 cells -- each its own later-day MEASUREMENT row; eligibility per
the cell's own session date"). This is that later-day run, ONE cell:
W = 512 (shape 1, n = 1,000,003) -- the third cell of that LEFT list
(the W = 128 record carried the list's second row; the W = 64 record
named the list's order).

Eligibility, per the cell's OWN session date (the resweep record's
correction: "cross-day eligibility is per cell's OWN session date, not the
directory's date suffix"): this cell's sessions are all 2026-10-23
daytime -- the basis session (docs/evidence/
gpu-subgroup-reduce-m1max-wsweep-20261023/w512, record commit 7c80f56f,
2026-10-23 10:09 JST) and the same-day re-session (docs/evidence/
gpu-subgroup-reduce-m1max-resweep-20261023/w512, record commit 7da5c367,
2026-10-23 15:34 JST). The run-logs carry no date stamps; the record
commits name the session dates (the anchor record's idiom). This run,
2026-10-24, is a later calendar day on the same host (Apple M1 Max,
reported simdgroup size 32), the same conforming native-Metal channel
(ADR-0360 question (1)'s decision, the emitters' own bytes), the
byte-identical protocol (6 fresh processes, 20 interleaved AB/BA pairs
per operator per run, 2 warmup submits per arm discarded, verified
read-back).

Driver (named verbatim, never paraphrased; the default --variant
subgroup-reduce is this family's compared arm; --elements and --op-order
are passed explicitly and equal the defaults the wsweep cell used):

    python3 scripts/gpu-subgroup-reduce-metal-measure.py --runs 6
      --workgroup 512 --elements 1000003 --op-order sum,max,min
      --out docs/evidence/gpu-subgroup-reduce-m1max-crossday-20261024/w512
      --compare-historical docs/evidence/gpu-subgroup-reduce-m1max-wsweep-20261023/w512/summary.md

The emitted shaders are byte-identical to the wsweep cell's (`diff -r`
empty, checked this tick). Classpath: the driver's named route 2
(`AMU_KBB_TEST_CLASSPATH`; route 1 `kbb -Spath -M:test` fails at the tree
root, "no deps.edn" -- the merge 7b8f6488 retired deps.edn; the
compile-log names the fallback route, never silent).

Host condition, named because the run took place on a busy machine:
load averages 40.20 / 22.36 / 18.42 at run start (uptime, 2026-10-24
12:47 JST). The harness times Metal GPU timestamps, not host wall time
(host submit->completion ns is recorded as secondary only).

## FINDING (real measurement, this host, this tick)

The cross-day sign scoping of the W = 128 row does NOT recur here: this
row replicates in sign AND in magnitude at every operator, and it is the
first row of this family's cross-day series whose cell-level magnitude
phrase is a reproduction rather than "magnitude splits by clock regime".

- Paired median ratios (:subgroup-reduce / :baseline gpu ns):
  1.197 / 1.193 / 1.193 for :sum/:max/:min. Per-run: sum 1.199, 1.198,
  1.197, 1.195, 1.194, 1.198; max 1.195, 1.192, 1.194, 1.193, 1.194,
  1.193; min 1.193, 1.194, 1.195, 1.191, 1.192, 1.194. All 18 per-run
  ratios lie in 1.191..1.199 -- no sub-1.0 ratio anywhere in this row.
- This cell's own verdict (claim protocol rule 2): **REGIME-INVARIANT
  SLOWER** -- every operator 6/6 slower, every observed regime one-sided;
  cell roll-up 18/18 slower.
- The rule-3 regime-matched comparison against the wsweep record (the
  driver's --compare-historical auto-wiring): sign -- "reproduces in sign
  strictly" at all three operators (every per-run ratio holds the
  historical sign); magnitude -- "magnitude reproduces within 0.002"
  (:max), "within 0.004" (:min), "within 0.001" (:sum). Cell roll-up:
  sign -- reproduces in sign strictly (every operator); magnitude --
  **magnitude reproduces within 0.004**. The magnitude phrase's deltas
  are the published paired medians (historical / new): max 1.195/1.193,
  min 1.197/1.193, sum 1.196/1.197. Within matched strata the deltas are
  0.000 / 0.002 / 0.002 (max/min/sum); the wsweep cell's run 3 (max
  1.648, min 1.231) sits outside every matched stratum and is named
  here, not hidden.
- Cross-day series context (the four rows' cell roll-ups, quoted from
  each record's summary.md): w256 anchor -- sign strict, magnitude
  "splits by clock regime"; w64 -- sign strict, magnitude "splits by
  clock regime (mixed: min)"; w128 -- sign does NOT reproduce strictly
  (:max straddle), magnitude "splits by clock regime"; this row (w512) --
  sign strict at every operator and the series' first cell-level
  magnitude REPRODUCTION phrase. This does not re-scope the w128 row:
  that row's single sub-1.0 ratio (run 1 at :max) stands named in its
  own record, and one row's clean replication is not evidence about
  another row's sign.
- Penalty band by cell (the four cross-day rows' median ratios): w512
  1.193..1.197 is the lowest band of the series (w256 1.212..1.220, w64
  1.216..1.220, w128 1.227..1.245). The ~20% penalty at this cell
  reproduces on a later day with all 18 ratios inside a 0.008-wide band.
- Historical sessions of this cell (both 2026-10-23): the wsweep record
  1.196/1.195/1.197 and the same-day re-session 1.197/1.194/1.193
  (sum/max/min medians) -- consistent with this row's 1.197/1.193/1.193.
- Rule 1 this run: ONE level at every operator (max 114521..114875, min
  114562..114896, sum 114542..115021), and cross-operator level identity
  **holds** (all 15 run pairs agree; the w128 row's identity refutation
  is not contradicted -- it was about that run's four-level mix).
- Read-back: 36 verify lines, ok=1 on every one (ok=0: 0); :max/:min
  bit-exact vs the reference and between arms (24/24 lines); :sum
  max_abs_vs_ref 1.63316727e-05 (both arms) and max_abs_vs_other
  3.05175781e-05.

## What this slice does NOT license

- No `:measured?` flag moves: the :baseline answers of the measured class
  were already MEASURED on the 2026-10-23 refutation; this run is
  corroboration of one cell's demotion basis (W = 512, shape 1) on a
  later day, nothing more. No selection answer changes and no workgroup
  row (ADR-0355/0358) is touched.
- W = 32 stays the decided cell (apple-w32-note); this run says nothing
  about it. The shape-1 W = 1024 cell (the LEFT list's next row -- "W =
  1024 is next in the LEFT's order") and the shape-2 cells keep their
  2026-10-23 basis until their own later-day runs; eligibility per the
  cell's own session date, and the anchor's conservative "2026-10-25
  runs qualify for every remaining cell regardless of straddle
  questions" stays true.
- The :simdgroup-reduce family is untouched; its remaining cross-day rows
  are its own (runnable 2026-10-25+ per its record). The shape-2 W = 512
  measured-but-REFUSED cell (that family's) stands: replication of a
  REFUSED cell is its own decision, not a way to re-run a refusal.
- This is a REPLICATION record, not a new measured cell: this tick
  changed no code namespace -- naming this record (and the anchor's, W =
  64's and W = 128's) in accelerator-variants' apple-measured-evidence /
  apple-narrow-note, and applying the same-day-re-session naming rule to
  this family's lists, are their own later slices. The record's basis
  text and every map are unchanged by this commit.

## Gate (this tick changed no code namespace)

1. python3 scripts/gpu_regime_classify.py --self-test
   -> TOTAL: 1687 assertions passed, 0 failed
      (1656 at the W = 128 record; the growth is this record joining the
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
