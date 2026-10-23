# ADR-0373 -- The Metal-native SIMD-group reduce row (`:simdgroup-reduce`)

- Status: **accepted as design (2026-10-23); rule 3's steps 1 and 2 are
  IMPLEMENTED the same day.** [UPDATE 2026-10-23, rule 3 step 1 landed: the
  MSL EMISSION of this variant is IMPLEMENTED
  (kotoba.compiler.accelerator-simdgroup-reduce, `lower` admits the
  (:msl-v1, :simdgroup-reduce) pair in both readings, tests exist --
  docs/evidence/gpu/simdgroup-reduce-msl-emission-20261023/). UPDATE
  2026-10-23, rule 3 step 2 landed (the later same-day slice): the
  SELECTION predicate is IMPLEMENTED -- the MSL ladder, the measured-cell
  carve-out and the `:simd-reduce` gate fact are code in
  kotoba.compiler.accelerator-variants' `select-variant`, pinned by
  tests (docs/evidence/gpu/simdgroup-reduce-selection-20261023/). UPDATE
  2026-10-23, rule 3 step 3 STARTED (the later same-day slice): the first
  hardware measurement of this variant ran on M1 Max at W = 256, n =
  1000003 through the conforming native-Metal channel
  (docs/evidence/gpu-simdgroup-reduce-m1max-20261023/,
  docs/evidence/gpu/simdgroup-reduce-m1max-measure-20261023.txt): paired
  median ratios 0.790/0.800/0.799 (sum/max/min vs :baseline), claim-
  protocol rule 2 REGIME-INVARIANT FASTER (18/18 per-run ratios below
  1.0). The flip is NOT done and the remaining cells are unmeasured:
  every answer this row carries is still UNMEASURED as a selection
  basis.] ADR-0356 rule 3 (emission admission
  first) gates its IMPLEMENTATION, which is its own
  later slice [now split: step 1 emission DONE, step 2 selection DONE,
  step 3 measurement STARTED (the W = 256 cell measured 2026-10-23; the
  flip and the remaining cells OPEN)]. Every answer this row will carry is UNMEASURED
  (`:measured? false`, rule 4's lock) until a hardware measurement replaces the
  basis text of the answer's cell.
- Date: 2026-10-23
- Tracking: JUN-58 (Apple). Parent JUN-55. One vendor per decision, the
  rule ADR-0356 set and ADR-0357/0360/0361/0364 followed.

## Decision

A new variant **`:simdgroup-reduce`** is DESIGNED: the reduce shape
(operators `:sum`/`:max`/`:min`, `W >= 32`) on the **MSL route only**,
whose intra-SIMD-group fold is Metal's own SIMD-group reduction
intrinsics -- `simd_sum` / `simd_max` / `simd_min` -- followed by the SAME
cross-SIMD-group tree over the `W/S` partials that the shared
`:subgroup-reduce` fold uses.

This is the row every Apple record has parked as "a Metal-native
`simd_sum`/`simd_max`/`simd_min` simdgroup row (still NOT designed)" --
PROPOSED in ADR-0356's row-prose reconciliation and in ADR-0360's
narrowing amendment, DECIDED here (as design; nothing is implemented by
this ADR).

## What the variant is (and is not)

- The intra-SIMD-group stage changes and only that stage: the
  `:subgroup-reduce` shuffle loop (the `simd_shuffle_down` ladder) is
  replaced by one SIMD-group reduction intrinsic per operator. Everything
  above it -- the partials array sized from the emitted `W`, the one write
  barrier, the cross-SIMD-group tree -- is the shared fold, unchanged.
- It is a SEPARATE variant keyword, never a rewrite of `:subgroup-reduce`.
  The negative pins that keep `:subgroup-reduce`'s fold the shuffle loop
  ("never a `simd_sum`/`simd_max`/`simd_min` rewrite",
  `accelerator-subgroup-reduce-test`) bind that variant unchanged and are
  the reason this row exists as its own variant.
- Rule 3 admits it on the MSL route only. GLSL/WGSL spellings for
  subgroup reduction belong to `:subgroup-reduce`'s arms and are out of
  scope here (one vendor per decision).

## Normative emission conditions (P1/P2, ADR-0357's text binds)

- **P1 (`:sum` association scope), option (b).** ADR-0357 P1 binds this
  fold as it bound the shuffle fold. Option (a) -- reproducing the
  baseline `W/2` tree's operand order -- is not available to an intrinsic
  reduction: `simd_sum`'s association order inside the SIMD-group is out
  of the emitter's hands and is not pinned by the vendor documentation
  this decision cites (the spec text was NOT re-read this tick; the P1
  scope does not depend on it). The `:sum` claim is therefore scoped:
  **low bits only, for inputs without catastrophic cancellation**;
  the cancellation-sensitive regime is recorded as UNMEASURED divergence
  from `:baseline`. `:max`/`:min` keep their bit-for-bit rule within the
  ordinary-value domain (non-NaN payloads, no negative zeros; ADR-0356
  rule 2 as amended by P1).
- **P2 (partial compaction).** The partial index is the SIMD-group index
  (`simdgroup_index_in_threadgroup` / `thread_index_in_simdgroup`), never
  `lid` arithmetic. The `S`-strided cross-SIMD-group tree over the dense
  partial array stands (ADR-0357 P2's own allowance).
- **Safety: `S` divides `W`.** Same mechanical check as every row of the
  family; a workgroup the reported SIMD-group width does not divide
  answers `:baseline` (rule 1).

## Emission admission first (rule 3) -- the implementation contract

The row lands ONLY in this order: (1) an MSL emission of the fold above,
admitted by `lower` for the `(:msl-v1, :simdgroup-reduce)` pair in both
readings, with tests in the MSL arm's style (operator meaning pins, P1/P2
pins, spec-spelling pins, determinism); then (2) the selection predicate
below. A selection row whose emission is not admitted is a defect, rule 3.

## Selection: the measured-cell carve-out, then the MSL ladder

[IMPLEMENTED 2026-10-23, rule 3 step 2: this section is code in
kotoba.compiler.accelerator-variants' `select-variant` (the
`:simd-reduce` gate, the ladder's cond rows, the carve-out note); the
ladder is pinned by `the-msl-ladder-selects-simdgroup-reduce-first` and
`simdgroup-selection-has-landed-under-the-msl-ladder`.]

1. **Measured-cell carve-out (measurement beats design).** A device class
   whose reduce-shape answers are measured or decided keeps those answers;
   no unmeasured design row overrides them. Today that is exactly the
   narrowed M1 Max class (name fragment `m1 max`): it keeps `:baseline`
   at every `W` (W = 64/128/256/512/1024 where `:subgroup-reduce` was
   measured slower, W = 32 by the low-band fail-safe decision).
   `:simdgroup-reduce` does NOT answer there until a measurement of THIS
   variant on that class flips the cell through the flip contract (below).
   The rejected alternative is on the record: treating the refutation as
   variant-scoped and handing M1 Max this unmeasured row as a fresh design
   choice. It is rejected because a cell an answer has already been given
   for -- by measurement or by fail-safe decision -- is closed to design
   choices, and because the one device where evidence exists is exactly
   where an unmeasured choice is least defensible. The reverse reading of
   the uB5G rule also binds: the refutation of `:subgroup-reduce` does
   NOT condemn or bless this variant anywhere. [IMPLEMENTED reading,
   step 2: the carve-out suppresses rung 1 by the name fragment (uB5G
   idiom) at every reported subgroup size -- the name is the key, exactly
   as the narrowing's. Where the shuffle row's gate also holds, the
   class's answers are byte-for-byte what they were before this variant
   existed -- the flip's `:measured?` true cells included, whose
   `:measured-cell` record's `:evidence` names the `:subgroup-reduce`
   runs only (the added carve-out note says so). Where ONLY this row's
   gate holds, the `:baseline` answer carries the carve-out note and
   `:measured? false`: nothing measured this variant, and the answer is
   the carve-out's decision.]
2. **The MSL ladder (the ADR-0361 CUDA-ladder idiom).** Outside the
   carved-out class, an Apple MSL descriptor that reports the fold's
   facts (rule 6, below) answers `:simdgroup-reduce` -- the vendor-native
   first rung; a descriptor that reports the shuffle fold's facts but not
   the reduction facts falls to `:subgroup-reduce` (the second rung);
   everything else answers `:baseline` (rule 1, total, no throw). This
   supersedes ADR-0360's "keep as designed is what every other Apple
   device gets" clause AS TO THE MSL ROUTE, and only from the moment the
   row is IMPLEMENTED; until then selection is byte-for-byte unchanged
   and that clause governs.
3. **Rule 6, one new capability fact.** The fold's subgroup ops are the
   SIMD-group reductions: the gate's vocabulary (this table's own
   capability vocabulary, the stance of ADR-0360's MSL-route amendment
   Part 2) grows one fact, **`:simd-reduce`** -- evidence that the
   device's SIMD-group exposes `simd_sum`/`simd_max`/`simd_min` -- plus
   the reported `:subgroup-size` (= SIMD-group width) dividing `W`.
   `:basic` and `:shuffle-relative` are the SHUFFLE fold's facts and are
   NOT required here: the cross-SIMD-group tree uses threadgroup
   barriers, not subgroup operations. No fact, no answer -- the row fails
   closed to `:baseline` exactly like every other row. This ADR produces
   no facts on any route: the producer gap (ADR-0362's `SUBGROUP`
   request, the absent Metal-native probe) stands unchanged.

## Measurement contract and the flip (composed, nothing new)

This row's measurement contract is ADR-0360's contract machinery as it
stands after question (1)'s decision and the flip: a conforming channel
runs the emitters' own bytes under the sweep protocol on a named device;
the flip records the tested device class (`:measured-cell` keys: name
fragment AND reported subgroup size, route, channel, the measured cells'
`W` set and shapes); the claim protocol (the regime-robust rules 1-4,
ADR-0360's amendment) binds every claim a record may make. Nothing in
this ADR amends any of it. The flip's gates key this VARIANT's own cells
when a measurement exists; until then every answer carries
`:measured? false` and a basis naming the design choice.

## What this decision is NOT

- **No speed claim.** The family's rationale ("removing most of the
  barrier cascade wins") is MEASURED-CONTRADICTED for `:subgroup-reduce`
  on the one device tested; nothing measures `simd_sum` against the
  shuffle loop anywhere. Stage counting is not a speed claim: the
  intra-SIMD-group stage becomes one reduction intrinsic per operator and
  the tree above it is the shared fold -- that is the whole structural
  difference, stated, not priced.
- **No :measured? movement. No workgroup row movement.** The workgroup
  table (ADR-0355/0358) is a different axis and is untouched.
- **No execution path claim.** Like every variant in the table today, this
  row will have no in-repo execution path (the wire-42 route died with the
  C loader; ADR 0371's provider is the replacement track); the
  measurement channel is the harness family of ADR-0360's contract.

## What moved in the repository (the diff)

[This section first recorded the design slice; the 2026-10-23 rule-3
step-1 slice added the rows below it.]
- `docs/adr/0373-gpu-metal-native-simdgroup-reduce.md`: this ADR.
- `docs/adr/0356-gpu-kernel-variant-selection.md`: the rows table gains
  the designed-not-implemented row; the "two design questions PROPOSED"
  clause is marked decided as to both questions.
- `docs/adr/0360-gpu-apple-subgroup-reduce.md`: the "still NOT designed
  (a separate decision)" / "keep as designed" clauses marked with this
  decision's effect.
- `docs/evidence/gpu/simdgroup-row-design-20261023.txt`: the slice record
  (probe and gate output included).
- `src/kotoba/compiler/accelerator_simdgroup_reduce.cljk`: the MSL
  emission (rule 3 step 1, IMPLEMENTED).
- `src/kotoba/compiler/accelerator.cljk`: `lower` admission for the
  (:msl-v1, :simdgroup-reduce) pair in both readings; kernel-variants
  grows the keyword; seal/re-lower admits it.
- `src/kotoba/compiler/accelerator_variants.cljk`: the honesty mark in the
  `variants` docstring only (selection answers unchanged).
  [STEP 2, rule 3 step 2 (2026-10-23):] the `:simd-reduce` rule-6 gate,
  the MSL ladder's first cond row (Apple + MSL route + the gate +
  `simdgroup/applicable?`, the carve-out excepted),
  `apple-simdgroup-carveout-note`, the `:simdgroup-reduce`
  `variant-bases` entry, and the state marks (rung 2 and the flip are
  byte-for-byte unchanged).
- `src/kotoba/compiler/accelerator.cljk`, `src/kotoba/compiler/accelerator-simdgroup-reduce.cljk`:
  honesty marks updated for step 2 (docstrings only).
- `test/kotoba/compiler/accelerator_variants_test.cljk`:
  `the-msl-ladder-selects-simdgroup-reduce-first` (rung precedence, the
  whole reduce row, fail-closed cells, route/vendor scope, the carve-out
  and its flag scope, rule-3 end to end, determinism) and the
  wire-vocabulary negative pin in
  `rule-6-reads-the-facts-the-subgroup-answer-parses`.
- `test/kotoba/compiler/accelerator_simdgroup_reduce_test.cljk`:
  `simdgroup-selection-has-not-landed` replaced by
  `simdgroup-selection-has-landed-under-the-msl-ladder`.
- `docs/evidence/gpu/simdgroup-reduce-msl-emission-20261023.txt`: the
  step-1 slice record (toolchain probe and gate output included).
- `docs/evidence/gpu/simdgroup-reduce-selection-20261023.txt`: the step-2
  slice record (gate output included).
- [STEP 3, started 2026-10-23 (the later same-day slice):]
  `scripts/gpu-subgroup-reduce-metal-measure.cljk`,
  `scripts/gpu-subgroup-reduce-metal-measure.py`,
  `scripts/gpu-subgroup-reduce-metal-measure.m`: the measurement
  instrument grows one variable -- `--variant` selects the compared arm
  (`:simdgroup-reduce` emits through the same `lower` admission) and the
  harness's `[variant-prefix]` positional (argv[5]) names its metallibs;
  the historical default path is byte-for-byte unchanged, and a
  non-default `--variant` requires `--out` at the driver so the
  historical record directory cannot be rewritten by another variant's
  run. `docs/evidence/gpu-simdgroup-reduce-m1max-20261023/`: the first
  measurement record (W = 256, n = 1000003, 6 fresh processes).
  `docs/evidence/gpu/simdgroup-reduce-m1max-measure-20261023.txt`: the
  step-3 slice record.

## What did NOT move (named so nothing is silently upgraded)

- [Step 2 moved the selection row (the ladder) as scoped above; these
  stay unmoved:] no `:measured?` flag movement on any answer, no new
  `:measured-cell` record, no workgroup row (ADR-0355/0358 untouched), no
  speed claim, no wire vocabulary change
  (device-from-subgroup keeps ADR-0362's eight
  VkSubgroupFeatureFlagBits tokens -- the `:simd-reduce` fact's producer
  gap is NAMED, not filled). Outside the ladder's scope `select-variant`
  answers byte-for-byte what it answered before: rung 2's answers, the
  flip's records and every non-Apple or non-MSL cell are unchanged (tests
  pin it).

## State (the honesty rule's three states)

[After rule 3 steps 1-2 (2026-10-23): IMPLEMENTED is the MSL emission +
`lower` admission + tests, AND the selection ladder -- the measured-cell
carve-out, the MSL ladder's two rungs, the `:simd-reduce` rule-6 gate --
+ its tests (the ladder's step-2 slice). STEP 3 (the later same-day
slice) adds MEASURED DATA, not implementation: the W = 256, n = 1000003
cell ran on M1 Max and its record is in the repo (ratio 0.790/0.800/0.799
vs `:baseline`, rule 2 regime-invariant faster). ACCEPTED DESIGN ONLY:
any wording above that governs this variant's own future measurement
cells (the flip contract as applied to `:simdgroup-reduce` -- no cell has
flipped).
PROPOSED, unchanged: every performance question about this variant off
the one measured cell.] The
two design
questions ADR-0356's reconciliation parked are now both DECIDED
(narrowing: ADR-0360's second decision; this row: this ADR).

## UNMEASURED, named

Everything about this variant's performance on every device but the one
measured cell (M1 Max, W = 256, n = 1000003 -- measured 2026-10-23,
faster than `:baseline` at that cell, see the step-3 record); every other
W of this variant (32/64/128/512/1024); shape 2 for this variant;
`simd_sum`'s association order as a spec-text claim (the spec was NOT
re-read this tick -- the P1 scope does not depend on it); every Apple
device but this M1 Max for any variant; the GLSL arm of
`:subgroup-reduce` at W = 512/1024 (unchanged).

## Toolchain probe (compiler verification, NOT a measurement)

This host's Apple Metal compiler admits the intrinsics this row cites.
`probe.metal` (scratch, not in the repo) using `simd_sum`, `simd_max`,
`simd_min` and `simd_shuffle_down` over a `simd_sum`-reduced block with
`simdgroup_index_in_threadgroup` / `thread_index_in_simdgroup`
compaction compiled to AIR with no diagnostics:

    xcrun metal -c probe.metal -o probe.air   -> exit 0
    Apple metal version 32023.883 (metalfe-32023.883)

This is the MSL arm's "compiler-verified, not folklore" idiom. It says
nothing about performance and nothing about any device but the toolchain.

## Gate (real runs, this host, kbb --backend sci)

Scoped GPU gate (the 7 GPU-owned test namespaces, scratch runner
`gpu_scoped_gate.cljk`, not in the repo), from the chain worktree root:

    kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)" \
      /Users/junkawasaki/.hermes/profiles/amu-gpu/cache/scratch/gpu_scoped_gate.cljk

(this slice adds no test and changes no code namespace; the gate runs to
prove nothing broke -- counts recorded in the evidence record).

Full suite (`run-tests.cljk`): RED AT BASE at namespace load on
`kotoba.form` (the W3 port path, documented red at base in ADR 0362),
outside this diff. No green full suite is claimed.

## LEFT (the next rows)

1. [STEPS 1-2 DONE 2026-10-23: (1) the MSL emission + `lower` admission
   + tests; (2) the selection predicate (the ladder, the carve-out, the
   `:simd-reduce` gate fact) + tests. STEP 3 STARTED 2026-10-23: the
   W = 256, n = 1000003 cell measured on M1 Max (faster than
   `:baseline`, rule 2 regime-invariant).] Rule 3's order keeps the rest
   of (3) next: the flip slice and the remaining cells.
2. (step 3) The flip: what the W = 256 numbers license under the flip
   contract -- this VARIANT's own cells keyed by name fragment, reported
   subgroup size, route, channel, W set and shapes -- one cell set at a
   time. Until it lands no `:measured?` flag moves.
3. (step 3) Measure the remaining cells (W = 32/64/128/512/1024, shape
   2, cross-day replication) under the same claim protocol.
4. Cross-day replication of the existing `:subgroup-reduce` cells (needs a
   later-day cron tick).
5. The GLSL arm of `:subgroup-reduce` stays blocked on ADR 0371's provider
   route.
