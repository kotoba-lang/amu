# NOTES -- the cross-day replication of the :simdgroup-reduce shape-1 W = 1024 cell

## What row this is

S5 (docs/evidence/gpu/simdgroup-reduce-w512-refusal-scope-20261024.txt) narrowed
the :simdgroup-reduce cross-day replication LEFT list to nine rows: the
shape-1 pairs W = 32/64/128/1024 and the shape-2 pairs W =
256/32/64/128/1024, each runnable 2026-10-25+ per its own pair's session
date. The shape-1 W = 32 pair filled the first of the nine
(gpu-simdgroup-reduce-m1max-crossday-20261025/w32), the shape-1 W = 64 pair
the second (.../w64) and the shape-1 W = 128 pair the third (.../w128).
This record fills the FOURTH: the shape-1 W = 1024 pair -- and with it the
shape-1 half of the nine is complete. Its flip basis is the W-sweep cell
docs/evidence/gpu-simdgroup-reduce-m1max-wsweep-20261023/w1024 (the
W = 1024 flip record is docs/evidence/gpu/simdgroup-reduce-flip-w1024-20261024.txt;
the cell is ALREADY flipped, this replication corroborates its basis and
flips nothing).

Cross-day eligibility, named exactly: the replication session date is
readable from this record's own run-log -- the instrument's calendar
stamps (run_started= / run_finished=) date the six fresh processes
2026-10-25T03:17:32+09:00 .. 2026-10-25T03:17:34+09:00. The original's
session date is 2026-10-24 on both available dating signals: every w1024
artifact (run-log.txt, compile-log.txt, summary.md, shaders/) was BORN
2026-10-24 00:03:29-00:03:36 JST (stat birth times) and the cell's own
commit 7a3dcfb04 landed 2026-10-24 00:05:45 +0900 -- and the flip record
simdgroup-reduce-flip-w1024-20261024.txt dates it the same way ("taken
earlier the same day" as the 2026-10-24 flip slice). The original run-log
carries NO calendar (the pre-instrument corpus -- this is the very
midnight-straddle cell whose missing calendar the driver docstring names
as the lesson the stamps were added for); this pair is therefore certified
cross-day by the replica's stamps plus the original record's dating (birth
+ commit + flip-record text), never by an original run-log line. Like the
w128 pair, this pair spans ONE day (original 2026-10-24, replica
2026-10-25).

Driver (named verbatim, never paraphrased):

    python3 scripts/gpu-subgroup-reduce-metal-measure.py --runs 6
      --workgroup 1024 --elements 1000003 --variant simdgroup-reduce
      --out docs/evidence/gpu-simdgroup-reduce-m1max-crossday-20261025/w1024
      --compare-historical docs/evidence/gpu-simdgroup-reduce-m1max-wsweep-20261023/w1024/summary.md

The emitted shaders are byte-identical to the flip basis record's
(`diff -r` empty, checked this tick). The classpath resolution is the
driver's named route 2 (AMU_KBB_TEST_CLASSPATH; route 1 `kbb -Spath
-M:test` fails at this root -- no deps.edn -- and the fallback is named
in compile-log.txt, never silent).

## FINDING (real measurement, this host, this tick)

- This cell's own verdict (claim protocol rule 2): **REGIME-INVARIANT
  FASTER** -- 18/18 per-run ratios below 1.0, every observed regime
  one-sided; paired median ratios 0.839/0.847/0.847 for :sum/:max/:min.
  Unlike every earlier replica this run sat in ONE clock regime per
  operator (rule 1: a single observed level at each of :max/:min/:sum).
- The flip basis (the wsweep cell, session 2026-10-24) recorded
  0.840/0.847/0.850.
- The rule-3 regime-matched comparison against that record (the driver's
  --compare-historical auto-wiring): sign -- **"reproduces in sign
  strictly"** at every operator (all 6 per-run ratios hold the
  historical sign at each operator); magnitude -- "magnitude reproduces
  within 0.000" at :max, "magnitude reproduces within 0.001" at :sum and
  **"magnitude splits by clock regime"** at :min (mixed strata draw on
  the historical side); the cell row names the split ("magnitude splits
  by clock regime", mixed: min), never "failed to reproduce".
  Within-stratum deltas (matched stratum pairs, hist/new median ratios):
  :max 0.846/0.847 (0.001); :min 0.849/0.847 (0.002); :sum 0.839/0.839
  (0.000) -- every matched stratum agrees within 0.000-0.002. Unmatched
  strata are named as unmatched in the summary, not folded away: the
  historical record's fast/mid levels (max levels 1-3, min levels 1-3,
  sum level 1) have no counterpart in this single-level run.
  Strata match is gpu-ns-compatible, not verified clock identity (the
  harness reads no clock).
- Read-back: 36 verify lines, ok=1 on every one; :max/:min bit-exact vs
  the reference and between arms; :sum 3.27e-05 (both arms) vs the
  reference and 6.10e-05 between arms (regrouping).
- Rule 1 this run: one level for :max, one for :min, one for :sum;
  cross-operator level identity **HOLDS** (15/15 run pairs agree, all
  partitions equal). This record is therefore NOT an identity refutation
  at all -- the first of the four cross-day replicas that is not one --
  so the crossing-only exact-set pin (scripts/gpu_regime_classify.py,
  ADR-0360 Amendment 2026-10-25) is unchanged and still names exactly
  the W = 32 cross-day record.

## Pin status -- green, named

`python3 scripts/gpu_regime_classify.py --self-test` is GREEN on the
corpus including this record: **2128 assertions passed, 0 failed** (the
W = 32 record's pre-pin corpus counted 1873, the post-pin corpus 2035,
the W = 64 record's 2066, the W = 128 record's 2097; this record's own
checks ran and passed). This record refutes nothing, so the crossing-only
exact-set pin still names exactly the W = 32 cross-day record.

## What this slice does NOT license

- No `:measured?` flag moves: this replication re-measures an ALREADY
  flipped cell (flip record simdgroup-reduce-flip-w1024-20261024.txt). No
  selection answer changes and no workgroup row (ADR-0355/0358) is
  touched.
- This is a REPLICATION record, not a new flip cell: the flip contract's
  cell set and the record's basis text are unchanged. Naming this record
  (and the w32/w64/w128 ones) in the flip note / basis evidence lists is
  its own later slice (the anchor cross-day record's rule, applied
  identically).
- The remaining five cross-day rows stay pending (shape-2 W =
  256/32/64/128/1024).
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
   -> GREEN: 2128 assertions passed, 0 failed (corpus includes this
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

- The five remaining pending :simdgroup-reduce cross-day rows (shape-2
  W = 256/32/64/128/1024).
- The naming slice: name the four replication records (w32, w64, w128,
  w1024) in the flip note / basis evidence lists.
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
