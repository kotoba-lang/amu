# NOTES -- the cross-day replication of the :simdgroup-reduce shape-1 W = 32 cell

## What row this is

S5 (docs/evidence/gpu/simdgroup-reduce-w512-refusal-scope-20261024.txt) narrowed
the :simdgroup-reduce cross-day replication LEFT list to nine rows: the
shape-1 pairs W = 32/64/128/1024 and the shape-2 pairs W =
256/32/64/128/1024, each runnable 2026-10-25+ per its own pair's session
date. This record fills the FIRST of the nine: the shape-1 W = 32 pair.
Its flip basis is the 2026-10-23 W-sweep cell
docs/evidence/gpu-simdgroup-reduce-m1max-wsweep-20261023/w32 (the W = 32
flip record is docs/evidence/gpu/simdgroup-reduce-flip-w32-20261024.txt;
the cell is ALREADY flipped, this replication corroborates its basis and
flips nothing).

Cross-day eligibility, named exactly: the replication session date is
readable from this record's own run-log -- the instrument's calendar
stamps (run_started= / run_finished=, commit ba925e133) date the six
fresh processes 2026-10-25T02:06:39+09:00 .. 2026-10-25T02:06:41+09:00.
The original's session date is the wsweep record's own dated record
(2026-10-23); its run-log carries NO calendar (the pre-instrument
corpus) -- this pair is therefore certified cross-day by the replica's
stamp plus the original record's dating, never by an original run-log
line, and that asymmetry is named here rather than glossed.

Driver (named verbatim, never paraphrased):

    python3 scripts/gpu-subgroup-reduce-metal-measure.py --runs 6
      --workgroup 32 --elements 1000003 --variant simdgroup-reduce
      --out docs/evidence/gpu-simdgroup-reduce-m1max-crossday-20261025/w32
      --compare-historical docs/evidence/gpu-simdgroup-reduce-m1max-wsweep-20261023/w32/summary.md

The emitted shaders are byte-identical to the flip basis record's
(`diff -r` empty, checked this tick). The classpath resolution is the
driver's named route 2 (AMU_KBB_TEST_CLASSPATH; route 1 `kbb -Spath
-M:test` fails at this root -- no deps.edn -- and the fallback is named
in compile-log.txt, never silent).

## FINDING (real measurement, this host, this tick)

- This cell's own verdict (claim protocol rule 2): **REGIME-INVARIANT
  FASTER** -- 18/18 per-run ratios below 1.0, every observed regime
  one-sided; paired median ratios 0.728/0.865/0.821 for :sum/:max/:min.
- The flip basis (2026-10-23) recorded 0.657/0.658/0.650.
- The rule-3 regime-matched comparison against that record (the driver's
  --compare-historical auto-wiring): sign -- **"reproduces in sign
  strictly"** at every operator (all 6 per-run ratios hold the
  historical sign at each operator); magnitude -- **"magnitude splits by
  clock regime"** at every operator (mixed strata draws), never "failed
  to reproduce". Within-stratum deltas (matched stratum pairs, hist/new
  median ratios): :max 0.747/0.911 (0.164) and 0.658/0.637 (0.021);
  :min 0.820/0.821 (0.001) and 0.639/0.644 (0.005); :sum 0.679/0.877
  (0.198) and 0.650/0.636 (0.014) -- the bulk stratum agrees within
  0.005-0.021 at all three operators, the fast-level draws diverge at
  :max/:sum. Strata match is gpu-ns-compatible, not verified clock
  identity (the harness reads no clock).
- Read-back: 36 verify lines, ok=1 on every one; :max/:min bit-exact vs
  the reference and between arms; :sum 2.15e-06 vs the reference and
  1.91e-06 between arms (regrouping).
- Rule 1 this run: three levels for :sum, four for :max, four for :min;
  cross-operator level identity REFUTED (5/15 run pairs) -- and this is
  the classified corpus's FIRST cross-cutting-only refutation (every
  operator pair cross-cuts; no strict refinement edge), which is what
  surfaces the structural pin below.

## The pin surfaced -- named, not hidden

`python3 scripts/gpu_regime_classify.py --self-test` is RED on this
record. Verbatim:

    AssertionError: every refuted record has a strict refinement edge (36/37)

The pin (scripts/gpu_regime_classify.py, _self_test_identity_corpus)
was written for exactly this event: "a record with cross-cutting-only
divergence would fail this pin and surface instead of hiding". This
session's real data is the corpus's first such record (37 scanned
records, 36 with a strict refinement edge). The pin's own comment
frames the failure as the surfacing mechanism, so this slice changes NO
instrument: the DECISION -- whether cross-cutting-only is a legal
refuted shape and what the pin asserts afterwards -- is its own next
slice, decided before the pin is touched. [UPDATE 2026-10-25: that
slice landed the same day -- the decision is YES, a legal refuted
shape, and the pin it authorizes is the named crossing-only set pin
(docs/evidence/gpu/cross-cutting-only-decision-20261025.txt; ADR-0360
Amendment 2026-10-25; the classify self-test is GREEN again at 2035
assertions with this record's shape pinned per record).] Everything
the aborted self-test would have run after the pin (the named-record
pins, the comparison-cell checks) did NOT run this tick.

## What this slice does NOT license

- No `:measured?` flag moves: this replication re-measures an ALREADY
  flipped cell (flip record simdgroup-reduce-flip-w32-20261024.txt). No
  selection answer changes and no workgroup row (ADR-0355/0358) is
  touched.
- This is a REPLICATION record, not a new flip cell: the flip contract's
  cell set and the record's basis text are unchanged. Naming this record
  in the flip note / basis evidence lists is its own later slice (the
  anchor cross-day record's rule, applied identically).
- The remaining eight cross-day rows stay pending (shape-1 W =
  64/128/1024, shape-2 W = 256/32/64/128/1024).
- Shapes beyond the two measured ones stay UNMEASURED at every cell;
  every non-Apple vendor, every other Apple device and every workgroup
  row not already flipped stay UNMEASURED, exactly as prior records
  left them.

## Gate (this tick changed no code namespace; real runs, this host, this
tick, from the chain worktree root; classpath route 2,
AMU_KBB_TEST_CLASSPATH)

1. python3 scripts/gpu-subgroup-reduce-metal-measure.py --self-test
   -> driver self-test: 17 assertions passed, 0 failed.
2. python3 scripts/gpu_regime_classify.py --self-test
   -> RED: AssertionError: every refuted record has a strict refinement
      edge (36/37) -- the surfaced pin above, named in full. The prior
      tick quoted 1873 assertions passed on a corpus without this
      record; this record is what moved 36/36 to 36/37.
3. Scoped GPU gate (the 8 GPU-owned test namespaces, scratch runner
   gpu_scoped_gate.cljk, not in the repo):
     kbb --backend sci --classpath "src:test:$AMU_KBB_TEST_CLASSPATH" \
       /Users/junkawasaki/.hermes/profiles/amu-gpu/cache/scratch/gpu_scoped_gate.cljk
   -> Ran 106 tests containing 11002 assertions. 0 failures, 0 errors.
      scoped: 106 tests, 11002 passed, 0 failed, 0 errors.
4. Full suite (run-tests.cljk, same route-2 classpath): RED AT BASE,
   outside this diff, at namespace load on `kotoba.form` ("Could not
   find namespace: kotoba.form"; the W3 port path documented red at
   base in ADR 0362), re-verified live this tick. No green full suite
   is claimed.

## Honest LEFT (the real remainder after this row)

- The cross-cutting-only decision and the pin update it authorizes (its
  own slice, decided before the pin is edited; until then the classify
  self-test stays RED at 36/37 and named). [DONE 2026-10-25, same day:
  the decision (YES, legal) and the named crossing-only set pin landed
  as the two follow-up commits of the next tick; the classify
  self-test is GREEN at 2035 assertions. The rest of this LEFT list
  stands unchanged.]
- The eight remaining pending :simdgroup-reduce cross-day rows.
- The naming slice: name this record in the flip note / basis evidence
  lists.
- A later-day DATA run at the refused shape-2 W = 512 pair: neither
  scheduled nor forbidden (its own decision row if wanted).
- The blocked rows stay exactly as prior records left them: no wire-42
  route (ADR 0371's provider not implemented), the GLSL arm stays
  LABELED BOOTSTRAP, every non-Apple vendor and every other Apple
  device UNMEASURED.
- Push/PR step skipped this tick by the blocker-first rule: open
  kotoba-lang/amu PRs with `hermes/` heads (#1561, #1553) are blockers;
  this commit stays local and pushes on the first tick after they
  clear.
