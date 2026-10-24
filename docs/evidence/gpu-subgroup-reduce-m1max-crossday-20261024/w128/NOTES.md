# NOTES -- the cross-day replication of the W = 128 (shape 1) :subgroup-reduce cell

## What row this is, and its eligibility

ADR-0373's LEFT row 4 ("Cross-day replication of the existing
`:subgroup-reduce` cells (needs a later-day cron tick)") continued, in the
anchor replication record's own Honest LEFT ("Cross-day replication of the
remaining :subgroup-reduce cells -- shape 1 at W = 64/128/512/1024 and the
shape-2 cells -- each its own later-day MEASUREMENT row; eligibility per
the cell's own session date"). This is that later-day run, ONE cell:
W = 128 (shape 1, n = 1,000,003) -- the second cell of that LEFT list
(the W = 64 record named "W = 128 is next in the LEFT's order").

Eligibility, per the cell's OWN session date (the resweep record's
correction: "cross-day eligibility is per cell's OWN session date, not the
directory's date suffix"): this cell's sessions are all 2026-10-23
daytime -- the basis session (docs/evidence/
gpu-subgroup-reduce-m1max-wsweep-low-20261023/w128, record commit
2026-10-23 11:15 JST) and the same-day re-session
(docs/evidence/gpu-subgroup-reduce-m1max-resweep-20261023/w128, record
commit 2026-10-23 15:17 JST). The run-logs carry no date stamps; the
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
      --workgroup 128 --elements 1000003 --op-order sum,max,min
      --out docs/evidence/gpu-subgroup-reduce-m1max-crossday-20261024/w128
      --compare-historical docs/evidence/gpu-subgroup-reduce-m1max-wsweep-low-20261023/w128/summary.md

The emitted shaders are byte-identical to the wsweep-low cell's
(`diff -r` empty, checked this tick). Classpath: the driver's named
route 2 (`AMU_KBB_TEST_CLASSPATH`; route 1 `kbb -Spath -M:test` fails at
the tree root, "no deps.edn" -- the merge 7b8f6488 retired deps.edn; the
compile-log names the fallback route, never silent).

## FINDING (real measurement, this host, this tick)

This family's FIRST cross-day row whose sign does not reproduce strictly
at every operator.

- Paired median ratios (:subgroup-reduce / :baseline gpu ns):
  1.245 / 1.227 / 1.230 for :sum/:max/:min. Per-run: sum 1.245, 1.245,
  1.243, 1.247, 1.248, 1.243; max 0.955, 1.241, 1.240, 1.230, 1.224,
  1.221; min 1.252, 1.240, 1.232, 1.228, 1.226, 1.220.
- This cell's own verdict (claim protocol rule 2): **REGIME-SCOPED** --
  :sum and :min are REGIME-INVARIANT SLOWER (6/6 each), but :max
  STRADDLES 1.0 (run 1's paired median ratio 0.955 -- variant faster in
  that run; the other five 1.221..1.241 slower). The straddle is inside
  ONE regime (rule 1's level 3 holds both sides: run 1 0.955 below,
  run 3 1.240 above), so no regime is one-sided at :max. Cell roll-up:
  17 of 18 per-run ratios above 1.0, one below -- not a selection basis.
- The two earlier cross-day rows of this family (w256 anchor, w64) were
  REGIME-INVARIANT SLOWER 18/18; this is the first cross-day row that is
  not. (Within the family overall this is not the first sub-1.0 ratio --
  the 2026-10-23 W = 32 op-order/decision records carry those; the claim
  is scoped to the cross-day replication rows.)
- The historical cell (2026-10-23 11:15) recorded 1.246/1.243/1.242 and
  the same-day re-session (15:17) 1.244/1.243/1.234 -- both 36/36 slower.
  The ~24% penalty band reproduces in median at this cell on a later day;
  what does not reproduce strictly is the sign claim at :max.
- The rule-3 regime-matched comparison against the wsweep-low record (the
  driver's --compare-historical auto-wiring): sign -- "reproduces in sign
  strictly" for :sum and :min (all 6 per-run ratios hold the historical
  sign: slower), **"sign does not reproduce strictly"** for :max
  (new-cell per-run ratio sides: faster, slower); magnitude --
  "magnitude splits by clock regime" at all three operators (mixed
  strata draws). Within-stratum deltas: sum 0.001 (1.246/1.245), max
  0.003 (1.244/1.241), min 0.002..0.003 (1.242/1.240, 1.229/1.232).
  Cell roll-up: sign -- does NOT reproduce strictly; magnitude --
  "magnitude splits by clock regime". The claim names the split and
  attributes the movement to session mixing -- never "failed to
  reproduce" at the magnitude axis.
- Read-back: 36 verify lines, ok=1 on every one (ok=0: 0); :max/:min
  bit-exact vs the reference and between arms (24/24 lines); :sum
  max_abs_vs_ref 9.23871994e-06 (baseline) / 9.77516174e-06 (variant) and
  max_abs_vs_other 1.52587891e-05 -- the same figures the historical
  cell recorded.
- Rule 1 this run: four levels at :max and :min, two at :sum (the widest
  intra-session clock mix yet in this family's cross-day rows), and
  cross-operator level identity **refuted** (10 of 15 run pairs diverge;
  max/min cross-cut, max/sum cross-cut, min's partition refines sum's).
- Named, not hidden: the single sub-1.0 ratio is run 1 at :max (baseline
  per-run median 76312, variant 72854 -- both mid-regime). One run of
  six at one operator; it moves the :max median from the historical
  1.243 to 1.227 and it is the entire reason the sign claim is scoped.

## What this slice does NOT license

- No `:measured?` flag moves: the :baseline answers of the measured
  class were already MEASURED on the 2026-10-23 refutation; this run is
  corroboration of one cell's demotion basis (W = 128, shape 1) on a
  later day, with a regime-scoped sign at one operator, nothing more. No
  selection answer changes and no workgroup row (ADR-0355/0358) is
  touched.
- W = 32 stays the decided cell (apple-w32-note); this run says nothing
  about it. The shape-1 W = 512/1024 cells and the shape-2 cells keep
  their 2026-10-23 basis until their own later-day runs (session-date
  evidence in the W = 64 record: eligible 2026-10-24; the anchor's
  conservative "2026-10-25 runs qualify for every remaining cell
  regardless of straddle questions" stays true).
- The :simdgroup-reduce family is untouched; its remaining cross-day rows
  are its own (runnable 2026-10-25+ per its record). The shape-2 W = 512
  measured-but-REFUSED cell (that family's) stands: replication of a
  REFUSED cell is its own decision, not a way to re-run a refusal.
- This is a REPLICATION record, not a new measured cell: this tick
  changed no code namespace -- naming this record (and the anchor's and
  W = 64's) in accelerator-variants' apple-measured-evidence /
  apple-narrow-note, and applying the same-day-re-session naming rule to
  this family's lists, are their own later slices. The record's basis
  text and every map are unchanged by this commit.

## Gate (this tick changed no code namespace)

1. python3 scripts/gpu_regime_classify.py --self-test
   -> TOTAL: 1656 assertions passed, 0 failed
      (1624 at the W = 64 record; the growth is this record joining the
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
   re-verified live this tick. No green full suite is claimed.
