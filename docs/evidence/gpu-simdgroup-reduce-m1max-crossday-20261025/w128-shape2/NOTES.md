# NOTES -- the cross-day replication of the :simdgroup-reduce shape-2 W = 128 cell

## What row this is

S5 (docs/evidence/gpu/simdgroup-reduce-w512-refusal-scope-20261024.txt) narrowed
the :simdgroup-reduce cross-day replication LEFT list to nine rows: the
shape-1 pairs W = 32/64/128/1024 and the shape-2 pairs W =
256/32/64/128/1024, each runnable 2026-10-25+ per its own pair's session
date. The shape-1 W = 32 pair filled the first of the nine
(gpu-simdgroup-reduce-m1max-crossday-20261025/w32), the shape-1 W = 64 pair
the second (.../w64), the shape-1 W = 128 pair the third (.../w128), the
shape-1 W = 1024 pair the fourth (.../w1024, the shape-1 half complete), the
shape-2 W = 256 pair the fifth (.../w256, the shape-2 series' anchor), the
shape-2 W = 32 pair the sixth (.../w32-shape2) and the shape-2 W = 64 pair
the seventh (.../w64-shape2). This record fills the EIGHTH: the shape-2
W = 128 pair -- the fourth row of the shape-2 half (the ADR's named order,
shape-2 W = 256/32/64/128/1024). Its flip basis is the shape-2 fourth-cell
record docs/evidence/gpu-simdgroup-reduce-m1max-shape2-20261024/w128 (the
flip record is docs/evidence/gpu/simdgroup-reduce-flip-shape2-w128-20261024.txt;
the cell is ALREADY flipped at BOTH shapes, this replication corroborates
its shape-2 basis and flips nothing).

Directory naming (the w32-shape2 record's own decision, applied here
unchanged): the shape-2 replicas that collide with an already-filled
shape-1 record directory take the `-shape2` suffix (.../w128-shape2 here).
The shape-2 W = 256 replica sits at the bare .../w256 because the nine-row
list has no shape-1 W = 256 row and nothing collided. The naming-slice
prose (flip note / basis evidence lists) stays its own later slice.

Cross-day eligibility, named exactly: the replication session date is
readable from this record's own run-log -- the instrument's calendar
stamps (run_started= / run_finished=) date the six fresh processes
2026-10-25T04:17:42+09:00 through 2026-10-25T04:17:43+09:00 (all six,
first and last stamps checked this tick). The original's session date is
2026-10-24 on every available dating signal: the w128 shape-2 artifact
birth time (summary.md born 2026-10-24 05:17:50 JST, stat birth) and the
flip record simdgroup-reduce-flip-shape2-w128-20261024.txt ("the shape-2
series' fourth cell, measured 2026-10-24 and flipped the same day", the
record "taken earlier the same day"). The original run-log carries NO
calendar (0 run_started= lines -- the pre-instrument corpus); this pair is
therefore certified cross-day by the replica's stamps plus the original
record's dating (birth + flip-record text), never by an original run-log
line -- the same named asymmetry every earlier pair carries.

Driver (named verbatim, never paraphrased; --elements equals the
shape-2 records' 1048576; --op-order the default sum,max,min):

    python3 scripts/gpu-subgroup-reduce-metal-measure.py --runs 6
      --workgroup 128 --elements 1048576 --variant simdgroup-reduce
      --out docs/evidence/gpu-simdgroup-reduce-m1max-crossday-20261025/w128-shape2
      --compare-historical docs/evidence/gpu-simdgroup-reduce-m1max-shape2-20261024/w128/summary.md

The emitted shaders are byte-identical to the flip basis record's
(`diff -r` empty, checked this tick). The run-log reads n=1048576
(checked this tick, 6 lines). The classpath resolution is the driver's
named route 2 (AMU_KBB_TEST_CLASSPATH; route 1 `kbb -Spath -M:test`
fails at this root -- no deps.edn -- and the fallback is named in
compile-log.txt, never silent).

## FINDING (real measurement, this host, this tick)

- This cell's own verdict (claim protocol rule 2): **REGIME-INVARIANT
  FASTER** -- 18/18 per-run ratios below 1.0, every observed regime
  one-sided; paired median ratios 0.771/0.781/0.783 for :sum/:max/:min.
- The flip basis (the shape-2 fourth-cell record, session 2026-10-24)
  recorded 0.769/0.780/0.780.
- The rule-3 regime-matched comparison against that record (the driver's
  --compare-historical auto-wiring): sign -- **"reproduces in sign
  strictly"** at every operator (all 6 per-run ratios hold the
  historical sign at each operator); magnitude -- **"magnitude splits by
  clock regime"** at ALL THREE operators (the cell row names the split:
  "magnitude splits by clock regime", mixed: max, min, sum), never
  "failed to reproduce". This session ran a four-level regime mix at
  every operator (baseline per-run medians 32042..100042 gpu-ns at
  :max) against the basis session's single level; the matched stratum
  pair is the basis's level 1 against this session's slowest level 4.
  Within-stratum deltas (matched stratum pairs, hist/new median ratios):
  :max 0.780/0.782 (0.002); :min 0.780/0.780 (0.001); :sum 0.770/0.771
  (0.001). Unmatched strata are named as unmatched in the summary, not
  folded away (new levels 1, 2, 3 have no counterpart at every
  operator). Strata match is gpu-ns-compatible, not verified clock
  identity (the harness reads no clock).
- Read-back: 36 verify lines, ok=1 on every one; :max/:min bit-exact vs
  the reference and between arms; :sum 9.24e-06 (:baseline) and
  6.02e-06 (:variant) vs the reference and 1.53e-05 between arms
  (regrouping).
- Rule 1 this run: FOUR levels at every operator (max [[6], [4, 5],
  [3], [1, 2]], min [[5, 6], [4], [3], [1, 2]], sum [[5], [3], [6],
  [1, 2, 4]], GAP-1.15 fastest-first); cross-operator level identity is
  **REFUTED** (4 of 15 run pairs diverge: 1v4, 2v4, 4v5, 5v6) and
  EVERY operator pair cross-cuts (max/min, max/sum, min/sum: neither
  partition refines the other; refinements empty). So this record is
  the corpus's THIRD crossing-only refutation and its SECOND
  cross-cutting-only one (the w32 record's every-pair-cross-cutting
  shape, unlike the w32-shape2 record's max=min shape) -- at a
  four-level regime mix at every operator, and the fewest divergent
  run pairs of the three pinned crossing-only records (4 of 15).

## Pin status -- EXTENDED by this record, green, named

The crossing-only exact-set pin (scripts/gpu_regime_classify.py,
ADR-0360 Amendment 2026-10-25) surfaced this record exactly as its
idiom prescribes: the self-test FAILED on the new crossing-only member
before the edit ("a future crossing-only record fails this pin on
purpose"). This slice EXTENDS the named set to the three named 2026-10-25
cross-day records (shape-1 w32, shape-2 w32-shape2, shape-2
w128-shape2) and adds this record's own pinned machine story (4 of 15
divergent, refinements empty, the four-level partitions above). No
other pin edit, no classify machinery change in this slice.

`python3 scripts/gpu_regime_classify.py --self-test` is GREEN on the
corpus including this record: **2254 assertions passed, 0 failed** (the
W = 32 shape-1 record's post-pin corpus counted 2035, the W = 64
record's 2066, the W = 128 record's 2097, the W = 1024 record's 2128,
the W = 256 shape-2 record's 2159, the W = 32 shape-2 record's 2191,
the W = 64 shape-2 record's 2222; this record's own checks ran and
passed). Corpus roll-up printed by the self-test: 64 multi-operator
records -- 22 identity-holds (4 of them multi-level), 42
identity-refuted (39 with refinement structure, 3 crossing-only: the
named set pin's members).

## What this slice does NOT license

- No `:measured?` flag moves: this replication re-measures an ALREADY
  flipped cell (flip record simdgroup-reduce-flip-shape2-w128-20261024.txt
  already names both shapes at W = 128). No selection answer changes and
  no workgroup row (ADR-0355/0358) is touched.
- This is a REPLICATION record, not a new flip cell: the flip contract's
  cell set and the record's basis text are unchanged. Naming this record
  (and the seven earlier replication ones) in the flip note / basis
  evidence lists is its own later slice.
- The remaining one cross-day row stays pending (shape-2 W = 1024).
- Shapes beyond the two measured ones stay UNMEASURED at every cell;
  every non-Apple vendor, every other Apple device and every workgroup
  row not already flipped stay UNMEASURED, exactly as prior records
  left them.

## Gate (this tick changed one scripts/ namespace -- the classify
self-test pin; real runs, this host, this tick, from the chain worktree
root; classpath route 2, AMU_KBB_TEST_CLASSPATH)

1. python3 scripts/gpu-subgroup-reduce-metal-measure.py --self-test
   -> driver self-test: 17 assertions passed, 0 failed.
2. python3 scripts/gpu_regime_classify.py --self-test
   -> GREEN: 2254 assertions passed, 0 failed (corpus includes this
      record; the crossing-only exact-set pin names exactly the three
      named 2026-10-25 cross-day records after this slice's extension).
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

- The one remaining pending :simdgroup-reduce cross-day row (shape-2
  W = 1024).
- The naming slice: name the eight replication records (w32, w64, w128,
  w1024 at shape-1, w256, w32-shape2, w64-shape2, w128-shape2 at
  shape-2) in the flip note / basis evidence lists.
- A later-day DATA run at the refused shape-2 W = 512 pair: neither
  scheduled nor forbidden (its own decision row if wanted).
- The blocked rows stay exactly as prior records left them: no wire-42
  route (ADR 0371's provider not implemented), the GLSL arm stays
  LABELED BOOTSTRAP, every non-Apple vendor and every other Apple
  device UNMEASURED.
- Push/PR step skipped this tick by the blocker-first rule: open
  kotoba-lang/amu PRs with `hermes/` heads (#1561, #1553, re-checked
  this tick via `gh pr list`) are blockers; this commit stays local and
  pushes on the first tick after they clear.
