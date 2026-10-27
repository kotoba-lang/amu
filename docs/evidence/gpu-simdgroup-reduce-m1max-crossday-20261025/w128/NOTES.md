# NOTES -- the cross-day replication of the :simdgroup-reduce shape-1 W = 128 cell

## What row this is

S5 (docs/evidence/gpu/simdgroup-reduce-w512-refusal-scope-20261024.txt) narrowed
the :simdgroup-reduce cross-day replication LEFT list to nine rows: the
shape-1 pairs W = 32/64/128/1024 and the shape-2 pairs W =
256/32/64/128/1024, each runnable 2026-10-25+ per its own pair's session
date. The shape-1 W = 32 pair filled the first of the nine
(gpu-simdgroup-reduce-m1max-crossday-20261025/w32) and the shape-1
W = 64 pair the second (.../w64). This record fills the THIRD: the
shape-1 W = 128 pair. Its flip basis is the W-sweep cell
docs/evidence/gpu-simdgroup-reduce-m1max-wsweep-20261023/w128 (the
W = 128 flip record is docs/evidence/gpu/simdgroup-reduce-flip-w128-20261024.txt;
the cell is ALREADY flipped, this replication corroborates its basis and
flips nothing).

Cross-day eligibility, named exactly: the replication session date is
readable from this record's own run-log -- the instrument's calendar
stamps (run_started= / run_finished=) date the six fresh processes
2026-10-25T03:03:50+09:00 .. 2026-10-25T03:03:51+09:00. The original's
session date is 2026-10-24 on both dating signals: every w128 artifact
(run-log.txt, compile-log.txt, summary.md, shaders/) was BORN
2026-10-24 00:49:00-00:49:07 JST (stat birth times) and the cell's own
commit d1a05a8f4 landed 2026-10-24 00:54:12 +0900 -- and the flip record
simdgroup-reduce-flip-w128-20261024.txt dates it the same way ("taken
earlier the same day" as the 2026-10-24 flip slice). The family
directory says wsweep-20261023, but this cell's own session reads
2026-10-24; unlike the w32/w64 replicas (original session 2026-10-23),
this pair spans ONE day, and that difference is named here rather than
glossed. The original run-log carries NO calendar (the pre-instrument
corpus) -- this pair is therefore certified cross-day by the replica's
stamps plus the original record's dating (birth + commit + flip-record
text), never by an original run-log line.

Driver (named verbatim, never paraphrased):

    python3 scripts/gpu-subgroup-reduce-metal-measure.py --runs 6
      --workgroup 128 --elements 1000003 --variant simdgroup-reduce
      --out docs/evidence/gpu-simdgroup-reduce-m1max-crossday-20261025/w128
      --compare-historical docs/evidence/gpu-simdgroup-reduce-m1max-wsweep-20261023/w128/summary.md

The emitted shaders are byte-identical to the flip basis record's
(`diff -r` empty, checked this tick). The classpath resolution is the
driver's named route 2 (AMU_KBB_TEST_CLASSPATH; route 1 `kbb -Spath
-M:test` fails at this root -- no deps.edn -- and the fallback is named
in compile-log.txt, never silent).

## FINDING (real measurement, this host, this tick)

- This cell's own verdict (claim protocol rule 2): **REGIME-INVARIANT
  FASTER** -- 18/18 per-run ratios below 1.0, every observed regime
  one-sided; paired median ratios 0.775/0.787/0.787 for :sum/:max/:min.
- The flip basis (the wsweep cell, session 2026-10-24) recorded
  0.775/0.789/0.789.
- The rule-3 regime-matched comparison against that record (the driver's
  --compare-historical auto-wiring): sign -- **"reproduces in sign
  strictly"** at every operator (all 6 per-run ratios hold the
  historical sign at each operator); magnitude -- **"magnitude splits by
  clock regime"** at :max/:min (mixed strata draws) and "magnitude
  reproduces within 0.000" at :sum; the cell row names the split
  ("magnitude splits by clock regime", mixed: max, min), never "failed
  to reproduce". Within-stratum deltas (matched stratum pairs, hist/new
  median ratios): :max 0.792/0.792 (0.000) and 0.786/0.785 (0.001);
  :min 0.794/0.792 (0.002), 0.784/0.788 (0.004), 0.784/0.785 (0.001);
  :sum 0.775/0.775 (0.000) -- every matched stratum agrees within
  0.000-0.004. Unmatched strata are named as unmatched in the summary,
  not folded away: the new run's mid-level (:max level 2, run 4) and the
  historical record's (:min level 2, run 2) have no counterpart.
  Strata match is gpu-ns-compatible, not verified clock identity (the
  harness reads no clock).
- Read-back: 36 verify lines, ok=1 on every one; :max/:min bit-exact vs
  the reference and between arms; :sum 9.24e-06 (baseline) / 6.02e-06
  (variant) vs the reference and 1.53e-05 between arms (regrouping).
- Rule 1 this run: three levels for :max, three for :min, one for :sum;
  cross-operator level identity REFUTED (11/15 run pairs) -- and unlike
  the W = 32 record's cross-cutting-only shape, this refutation HAS
  strict refinement edges: max and min are EQUAL partitions and both
  strictly refine sum's (sum pools what max and min split). The named
  crossing-only set pin (scripts/gpu_regime_classify.py, ADR-0360
  Amendment 2026-10-25) is therefore unchanged by this record.

## Pin status -- green, named

`python3 scripts/gpu_regime_classify.py --self-test` is GREEN on the
corpus including this record: **2097 assertions passed, 0 failed** (the
W = 32 record's pre-pin corpus counted 1873, the post-pin corpus 2035,
the W = 64 record's 2066; this record's own checks ran and passed).
This record refutes cross-operator identity WITH strict refinement
edges, so the crossing-only exact-set pin still names exactly the
W = 32 cross-day record.

## What this slice does NOT license

- No `:measured?` flag moves: this replication re-measures an ALREADY
  flipped cell (flip record simdgroup-reduce-flip-w128-20261024.txt). No
  selection answer changes and no workgroup row (ADR-0355/0358) is
  touched.
- This is a REPLICATION record, not a new flip cell: the flip contract's
  cell set and the record's basis text are unchanged. Naming this record
  (and the w32/w64 ones) in the flip note / basis evidence lists is its
  own later slice (the anchor cross-day record's rule, applied
  identically).
- The remaining six cross-day rows stay pending (shape-1 W = 1024,
  shape-2 W = 256/32/64/128/1024).
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
   -> GREEN: 2097 assertions passed, 0 failed (corpus includes this
      record; the crossing-only exact-set pin still names only the
      W = 32 cross-day record).
3. Scoped GPU gate (the 8 GPU-owned test namespaces, scratch runner
   gpu_scoped_gate.cljk, not in the repo):
     kbb --backend sci --classpath "src:test:$AMU_KBB_TEST_CLASSPATH" \
       /Users/junkawasaki/.hermes/profiles/amu-gpu/cache/scratch/gpu_scoped_gate.cljk
   -> Ran 106 tests containing 11002 assertions. 0 failures, 0 errors.
      scoped: 106 tests, 11002 passed, 0 failed, 0 errors.
4. Full suite (run-tests.cljk, same route-2 classpath): RED AT BASE,
   outside this diff, at namespace load on `kotoba.form` ("Error: Could
   not find namespace: kotoba.form"; the W3 port path documented red at
   base in ADR 0362), re-verified live this tick. No green full suite
   is claimed.

## Honest LEFT (the real remainder after this row)

- The six remaining pending :simdgroup-reduce cross-day rows (shape-1
  W = 1024, shape-2 W = 256/32/64/128/1024).
- The naming slice: name the three replication records (w32, w64, w128)
  in the flip note / basis evidence lists.
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
