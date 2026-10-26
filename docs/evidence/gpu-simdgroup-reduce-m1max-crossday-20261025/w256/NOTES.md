# NOTES -- the cross-day replication of the :simdgroup-reduce shape-2 W = 256 cell

## What row this is

S5 (docs/evidence/gpu/simdgroup-reduce-w512-refusal-scope-20261024.txt) narrowed
the :simdgroup-reduce cross-day replication LEFT list to nine rows: the
shape-1 pairs W = 32/64/128/1024 and the shape-2 pairs W =
256/32/64/128/1024, each runnable 2026-10-25+ per its own pair's session
date. The shape-1 W = 32 pair filled the first of the nine
(gpu-simdgroup-reduce-m1max-crossday-20261025/w32), the shape-1 W = 64 pair
the second (.../w64), the shape-1 W = 128 pair the third (.../w128) and the
shape-1 W = 1024 pair the fourth (.../w1024, with it the shape-1 half
complete). This record fills the FIFTH: the shape-2 W = 256 pair -- the
anchor cell of the shape-2 series and the first row of its half (the ADR's
named order, shape-2 W = 256/32/64/128/1024). Its flip basis is the
shape-2 anchor cell
docs/evidence/gpu-simdgroup-reduce-m1max-shape2-20261024/w256 (the
W = 256 flip record is docs/evidence/gpu/simdgroup-reduce-flip-shape2-
w256-20261024.txt; the cell is ALREADY flipped at BOTH shapes, this
replication corroborates its shape-2 basis and flips nothing).

Cross-day eligibility, named exactly: the replication session date is
readable from this record's own run-log -- the instrument's calendar
stamps (run_started= / run_finished=) date the six fresh processes
2026-10-25T03:33:32+09:00 .. 2026-10-25T03:33:33+09:00. The original's
session date is 2026-10-24 on every available dating signal: the w256
artifact birth times (summary.md born 2026-10-24 03:19:38 JST, stat
birth) and the flip record simdgroup-reduce-flip-shape2-w256-20261024.txt
("measured 2026-10-24 and flipped the same day", the anchor record
"taken earlier the same day"). The original run-log carries NO calendar
(the pre-instrument corpus -- the stamps landed in commit ba925e133,
after this cell's session); this pair is therefore certified cross-day by
the replica's stamps plus the original record's dating (birth +
flip-record text), never by an original run-log line -- the same named
asymmetry the w32/w64/w128/w1024 pairs carry.

Driver (named verbatim, never paraphrased; --elements equals the
shape-2 records' 1048576; --op-order the default sum,max,min):

    python3 scripts/gpu-subgroup-reduce-metal-measure.py --runs 6
      --workgroup 256 --elements 1048576 --variant simdgroup-reduce
      --out docs/evidence/gpu-simdgroup-reduce-m1max-crossday-20261025/w256
      --compare-historical docs/evidence/gpu-simdgroup-reduce-m1max-shape2-20261024/w256/summary.md

The emitted shaders are byte-identical to the flip basis record's
(`diff -r` empty, checked this tick). The run-log reads n=1048576
(checked this tick). The classpath resolution is the driver's named route
2 (AMU_KBB_TEST_CLASSPATH; route 1 `kbb -Spath -M:test` fails at this
root -- no deps.edn -- and the fallback is named in compile-log.txt,
never silent).

## FINDING (real measurement, this host, this tick)

- This cell's own verdict (claim protocol rule 2): **REGIME-INVARIANT
  FASTER** -- 18/18 per-run ratios below 1.0, every observed regime
  one-sided; paired median ratios 0.795/0.806/0.810 for :sum/:max/:min.
- The flip basis (the shape-2 anchor record, session 2026-10-24)
  recorded 0.794/0.811/0.812.
- The rule-3 regime-matched comparison against that record (the driver's
  --compare-historical auto-wiring): sign -- **"reproduces in sign
  strictly"** at every operator (all 6 per-run ratios hold the
  historical sign at each operator); magnitude -- "magnitude reproduces
  within 0.001" at :sum and **"magnitude splits by clock regime"** at
  :max and :min (mixed strata draws on both sides); the cell row names
  the split ("magnitude splits by clock regime", mixed: max, min), never
  "failed to reproduce". Within-stratum deltas (matched stratum pairs,
  hist/new median ratios): :max 0.806/0.804 (0.002); :min 0.812/0.814
  (0.002), 0.812/0.812 (0.000), 0.817/0.790 (0.027), 0.817/0.814
  (0.003), 0.804/0.803 (0.001); :sum 0.795/0.795 (0.000) -- every
  matched stratum agrees within 0.000-0.027. Unmatched strata are named
  as unmatched in the summary, not folded away (historical max levels
  1-2, historical sum level 1, new min level 5 have no counterpart).
  Strata match is gpu-ns-compatible, not verified clock identity (the
  harness reads no clock).
- Read-back: 36 verify lines, ok=1 on every one; :max/:min bit-exact vs
  the reference and between arms; :sum 1.58e-05 (both arms) vs the
  reference and 3.05e-05 between arms (regrouping).
- Rule 1 this run: three levels at :max, six at :min, two at :sum;
  cross-operator level identity **REFUTED** (7 of 15 run pairs diverge)
  -- but every disagreement carries strict refinement edges (min's
  partition refines max's, max's refines sum's, min's refines sum's),
  so this is a refutation WITH refinement structure, never a
  crossing-only one. The crossing-only exact-set pin
  (scripts/gpu_regime_classify.py, ADR-0360 Amendment 2026-10-25) is
  therefore unchanged and still names exactly the W = 32 cross-day
  record.

## Pin status -- green, named

`python3 scripts/gpu_regime_classify.py --self-test` is GREEN on the
corpus including this record: **2159 assertions passed, 0 failed** (the
W = 32 record's pre-pin corpus counted 1873, the post-pin corpus 2035,
the W = 64 record's 2066, the W = 128 record's 2097, the W = 1024
record's 2128; this record's own checks ran and passed). Corpus roll-up
printed by the self-test: 61 multi-operator records -- 21 identity-holds
(3 of them multi-level), 40 identity-refuted (39 with refinement
structure, 1 crossing-only: the named set pin's members). This record
refutes nothing crossing-only, so the pin still names exactly the
W = 32 cross-day record.

## What this slice does NOT license

- No `:measured?` flag moves: this replication re-measures an ALREADY
  flipped cell (flip record simdgroup-reduce-flip-shape2-w256-20261024.txt
  already names both shapes at W = 256). No selection answer changes and
  no workgroup row (ADR-0355/0358) is touched.
- This is a REPLICATION record, not a new flip cell: the flip contract's
  cell set and the record's basis text are unchanged. Naming this record
  (and the w32/w64/w128/w1024 ones) in the flip note / basis evidence
  lists is its own later slice (the anchor cross-day record's rule,
  applied identically).
- The remaining four cross-day rows stay pending (shape-2 W =
  32/64/128/1024).
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
   -> GREEN: 2159 assertions passed, 0 failed (corpus includes this
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

- The four remaining pending :simdgroup-reduce cross-day rows (shape-2
  W = 32/64/128/1024).
- The naming slice: name the five replication records (w32, w64, w128,
  w1024 at shape-1, w256 at shape-2) in the flip note / basis evidence
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
