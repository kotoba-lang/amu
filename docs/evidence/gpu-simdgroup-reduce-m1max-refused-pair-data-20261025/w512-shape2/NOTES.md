# NOTES -- the later-day DATA run at the refused :simdgroup-reduce
# shape-2 W = 512 pair (the S5 carve-out's decision row, taken)

## What row this is

S5 of the refusal scope decision
(docs/evidence/gpu/simdgroup-reduce-w512-refusal-scope-20261024.txt)
carved this row out: "A later-day DATA run at the refused pair (pure
data, explicitly non-basis) is NEITHER scheduled NOR forbidden -- if
wanted, its own decision row, and never a basis row (the same carve-out
the membership decision gave the W = 32 cell's data run)." The naming
slice's HONEST LEFT (docs/evidence/gpu/simdgroup-crossday-naming-
20261025.txt) then carried it as the one actionable remainder row.
THIS RECORD IS THAT DECISION ROW: it decides the carve-out is TAKEN
(2026-10-25, this host) and the run below is its pure-data content. It
is not silent and not assumed -- it is decided here.

This record is NOT a cross-day replication record (S5: the refused pair
owes no cross-day row; the nine-row cross-day list stays COMPLETE and
untouched). It corroborates no flip basis and is not a member of any
replication list. It is a DATA run beside the refusal named.

Session dating (the run-log's own calendar stamps): the six fresh
processes stamp run_started=2026-10-25T05:22:03+09:00 through
run_finished=2026-10-25T05:22:04+09:00 (all six blocks carry
run_started=/run_finished=, checked this tick). The original refused
record (docs/evidence/gpu-simdgroup-reduce-m1max-shape2-20261024/w512)
is dated 2026-10-24 (its own flip record simdgroup-reduce-flip-shape2-
w512-refused-20261024.txt). So this run is LATER-DAY relative to the
refused record -- the carve-out's own precondition -- on the run-log
stamps alone.

Driver (named verbatim; --elements equals the shape-2 records' 1048576;
--op-order the default sum,max,min):

    python3 scripts/gpu-subgroup-reduce-metal-measure.py --runs 6
      --workgroup 512 --elements 1048576 --variant simdgroup-reduce
      --out docs/evidence/gpu-simdgroup-reduce-m1max-refused-pair-data-20261025/w512-shape2
      --compare-historical docs/evidence/gpu-simdgroup-reduce-m1max-shape2-20261024/w512/summary.md

The emitted shaders are byte-identical to the refused record's
(`diff -r` empty, checked this tick). The run-log reads n=1048576
(checked this tick, 6 lines). The classpath resolution is the driver's
named route 2 (AMU_KBB_TEST_CLASSPATH; route 1 `kbb -Spath -M:test`
fails at this root -- no deps.edn -- and the fallback is named in
compile-log.txt, never silent).

## FINDING (real measurement, this host, this tick -- DATA beside the
## refusal named, nothing more)

- Paired median ratios (:simdgroup-reduce / :baseline gpu ns):
  0.813/0.820/0.822 for :sum/:max/:min. The refused record (session
  2026-10-24) recorded 0.812/0.821/0.822.
- This session's own rule-2 verdict over its own runs: **regime-
  invariant, faster (18/18)** -- every per-run ratio of every operator
  below 1.0 (:sum 0.813/0.811/0.813/0.812/0.814/0.812, :max
  0.819/0.821/0.820/0.821/0.818/0.823, :min
  0.824/0.822/0.824/0.822/0.822/0.717), every observed regime
  one-sided. The refused record's 1-of-18 :min straddle inside one
  regime (run 3 at 1.054) is ABSENT from this session's runs. These
  are measured facts of THESE runs, citable AS DATA beside the refusal
  named (S3).
- THE REFUSAL STANDS EXACTLY AS SCOPE-DECIDED (S4): no run lifts or
  narrows it. This session's one-sidedness is NOT a selection basis
  over the pair, NOT a flip, NOT a narrowing of the refusal, and NOT
  an unqualified speed claim ("faster at W = 512, shape 2" stays
  forbidden over the pair, S3). The only claim form over the pair is
  the measured-but-refused description itself, beside the refusal
  named. If the pair's story is ever reopened, it is reopened by a
  DECISION row on the scope note (S4) -- never by a run, including
  this one.
- Rule-3 regime-matched comparison against the refused record (the
  driver's --compare-historical auto-wiring; data, licensing nothing):
  cell-level sign -- **does NOT reproduce strictly** (the per-operator
  detail: :sum and :max reproduce in sign strictly (faster, 6/6 each);
  :min has NO single historical sign to hold -- the historical cell is
  regime-scoped, within-regime). Magnitude -- **"magnitude reproduces
  within 0.001"** at :sum and :max and **"magnitude splits by clock
  regime"** at :min (the summary's cell row: "magnitude splits by
  clock regime", mixed: min). Within-stratum pairs (matched stratum
  pairs, hist/new median ratios): :sum 0.812/0.812 (0.000); :max
  0.821/0.821 (0.000); :min 0.823/0.717 (0.106, the one-run fast
  stratum pair) and 0.820/0.823 (0.003, the slow one). Unmatched
  strata are named as unmatched in the summary (hist level 1 / new
  level 1 at :max; hist 2 / new 2 at :min), never folded away. Strata
  match is gpu-ns-compatible, not verified clock identity (the harness
  reads no clock).
- Read-back: 36 verify lines, ok=1 on every one; :max/:min bit-exact
  vs the reference and between arms; :sum 1.63e-05 (:baseline and
  :variant) vs the reference and 3.05e-05 between arms (regrouping).
- Rule 1 this run: TWO levels at :max (runs fastest-first [[5],
  [1, 2, 3, 4, 6]]), THREE at :min ([[6], [5], [1, 2, 3, 4]]) and ONE
  at :sum ([[1, 2, 3, 4, 5, 6]]); cross-operator level identity is
  **REFUTED** (9 of 15 run pairs diverge) with a pure refinement
  chain: min's partition refines max's, max's refines sum's, min's
  refines sum's -- every edge one-way, nothing crossing. So this
  record is the corpus's 44th identity refutation and its 41st WITH
  refinement structure (the classify self-test roll-up: 66
  multi-operator records -- 22 identity-holds (4 multi-level), 44
  identity-refuted (41 with refinement structure, 3 crossing-only:
  the named set pin's members)).

## Pin status -- UNCHANGED by this record, green, named

The crossing-only exact-set pin (scripts/gpu_regime_classify.py,
ADR-0360 Amendment 2026-10-25) does NOT trip on this record and needs
no edit this slice: its idiom fires only on a CROSSING-only identity
refutation, and this record's refutation is a refinement chain (min <
max < sum, all edges one-way). The pin stands unchanged at its three
named 2026-10-25 cross-day records (shape-1 w32, shape-2 w32-shape2,
shape-2 w128-shape2). No pin edit, no classify machinery change in
this slice.

`python3 scripts/gpu_regime_classify.py --self-test` is GREEN on the
corpus including this record: **2316 assertions passed, 0 failed**
(the naming slice's corpus counted 2285; this record's own checks
account for the +31 -- the self-test discovered the record in its
corpus scan and printed its gap splits and its identity row "identity-
refuted (9 divergent pairs; levels max 2, min 3, sum 1)").

## What this slice does NOT license (named so nothing is silently
## upgraded)

- No `:measured?` flag moves. The W = 512 :measured-cell record keeps
  `:shapes [1000003]` and its `:evidence` keeps the W-sweep w512 runs
  (docs/evidence/gpu-simdgroup-reduce-m1max-wsweep-20261023/w512)
  alone. No selection answer moves (selection cannot vary with n) and
  no workgroup row (ADR-0355/0358) is touched.
- The refusal (S1) and its scope decision (S1-S5) stand untouched:
  this record revisits nothing. In particular this session's 18/18
  one-sidedness does NOT revive the cell -- S4 is absolute ("no later-
  day data run lifts or narrows it"), and the contract's rule (a shape
  enters a flip cell's record only on the cell's OWN rule-2 verdict at
  that shape) is not re-run here.
- This record names NO contract key (S2's extension: a pure-data run
  is never a contract-satisfying record): it is absent from
  apple-simdgroup-measured-evidence, from every basis evidence list,
  and never a basis row (S5). No code namespace and no test moved in
  this slice -- the scoped gate's unchanged counts are the check.
- Naming this data run in the flip note / the scope note's prose is
  its own later slice (the same deferment the nine cross-day records
  carried until their naming slice).
- Every non-Apple vendor, every other Apple device, the GLSL arm
  (LABELED BOOTSTRAP) and every shape beyond the two measured stay
  UNMEASURED, exactly as prior records left them.

## Gate (this tick changed no src/ or test/ namespace and no scripts/
## namespace -- evidence + this note only; real runs, this host, this
## tick, from the chain worktree root; classpath route 2,
## AMU_KBB_TEST_CLASSPATH)

1. python3 scripts/gpu-subgroup-reduce-metal-measure.py --self-test
   -> driver self-test: 17 assertions passed, 0 failed.
2. python3 scripts/gpu_regime_classify.py --self-test
   -> GREEN: 2316 assertions passed, 0 failed (corpus includes this
      record; the crossing-only exact-set pin still names exactly the
      three named 2026-10-25 cross-day records -- unchanged this
      slice).
3. Scoped GPU gate (the 8 GPU-owned test namespaces, scratch runner
   gpu_scoped_gate.cljk, not in the repo):
     kbb --backend sci --classpath "src:test:$AMU_KBB_TEST_CLASSPATH" \
       /Users/junkawasaki/.hermes/profiles/amu-gpu/cache/scratch/gpu_scoped_gate.cljk
   -> Ran 106 tests containing 11026 assertions. 0 failures, 0 errors.
      scoped: 106 tests, 11026 passed, 0 failed, 0 errors
      (unchanged from the naming slice -- this diff changed no code).
4. Full suite (run-tests.cljk, same route-2 classpath): RED AT BASE,
   outside this diff, at namespace load on `kotoba.form` ("Error: Could
   not find namespace: kotoba.form"; the W3 port path documented red at
   base in ADR 0362), re-verified live this tick. No green full suite
   is claimed.

## Honest LEFT (the real remainder after this row)

- Naming this data run in the flip note's SHAPE-2 W = 512 paragraph /
  the refusal-scope note's prose (a docstring slice, with the scoped
  gate) -- its own later slice, exactly as the nine cross-day records
  deferred their naming.
- The S5 data-run row is CONSUMED by this record (decided taken
  2026-10-25). A further later-day data run at the pair would be its
  own new decision row, not this one.
- The blocked rows stay exactly as prior records left them: no wire-42
  route (ADR 0371's provider not implemented), the GLSL arm stays
  LABELED BOOTSTRAP, every non-Apple vendor and every other Apple
  device UNMEASURED.
- Push/PR step skipped this tick by the blocker-first rule if any open
  kotoba-lang/amu PR with a `hermes/` head exists at push time
  (re-checked live this tick via `gh pr list`); otherwise this commit
  rides the chain PR.
