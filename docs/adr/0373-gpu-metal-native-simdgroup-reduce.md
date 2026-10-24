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
  1.0). UPDATE 2026-10-23 (later same-day slices): the W = 256 and
  W = 512 cells FLIPPED (the flip slices, below) -- two answers of this
  row carry `:measured? true` on the narrowed M1 Max class -- and the
  W-sweep's second cell measured W = 512 (paired median ratios
  0.815/0.823/0.824, rule 2 REGIME-INVARIANT FASTER, 18/18). UPDATE
  2026-10-24 (the W-sweep's third cell, measured and flipped in its own
  same-day slices): W = 1024 measured (paired median ratios
  0.840/0.847/0.850, rule 2 REGIME-INVARIANT FASTER, 18/18) and FLIPPED
  (the W = 1024 flip slice, below) -- three answers of this row carry
  `:measured? true` on the narrowed M1 Max class. UPDATE 2026-10-24
  (the W-sweep's fourth cell, measured and flipped in its own
  same-day slices): W = 128 measured (paired median ratios
  0.775/0.789/0.789, rule 2 REGIME-INVARIANT FASTER, 18/18) and FLIPPED
  (the W = 128 flip slice, below) -- four answers of this row carry
  `:measured? true` on the narrowed M1 Max class. UPDATE 2026-10-24
  (the W-sweep's fifth cell, measured and flipped in its own
  same-day slices): W = 64 measured (paired median ratios
  0.719/0.728/0.729, rule 2 REGIME-INVARIANT FASTER, 18/18) and FLIPPED
  (the W = 64 flip slice, below) -- five answers of this row carry
  `:measured? true` on the narrowed M1 Max class. UPDATE 2026-10-24
  (the W-sweep's sixth and last cell, measured and flipped in its own
  same-day slices): W = 32 measured (paired median ratios
  0.657/0.658/0.650, rule 2 REGIME-INVARIANT FASTER, 18/18) and FLIPPED
  (the W = 32 flip slice, below) -- six answers of this row carry
  `:measured? true` on the narrowed M1 Max class, the class's whole W
  band [32, 1024] (the six are every width the row admits). UPDATE
  2026-10-24 (the shape-2 series, six cells): W = 256 measured and
  FLIPPED at n = 2^20 (the shape-2 anchor -- its record names both
  shapes), W = 512 measured at n = 2^20 and REFUSED as a selection
  basis (claim-protocol rule 2 REGIME-SCOPED -- the first
  measured-but-scoped cell; the flip contract's scoped-cell answer is
  decided in the measurement-contract section below and pinned by
  tests), W = 1024 measured and FLIPPED at n = 2^20 (the W = 1024
  record now names both shapes) and W = 128 measured and FLIPPED at
  n = 2^20 (the W = 128 record now names both shapes; the shape-2
  series' first identity-HOLDS cell) and W = 64 measured and FLIPPED at
  n = 2^20 (the W = 64 record now names both shapes; the shape-2
  series' second identity-HOLDS cell) and W = 32 measured and FLIPPED
  at n = 2^20 (the W = 32 record now names both shapes; the shape-2
  series' sixth and last cell). Every other
  cell is unmeasured and every answer outside the six flip cells still
  carries `:measured? false`.] ADR-0356 rule 3 (emission admission
  first) gates its IMPLEMENTATION, which is its own
  later slice [now split: step 1 emission DONE, step 2 selection DONE,
  step 3 measurement STARTED (the W = 256, W = 512, W = 1024,
  W = 128, W = 64 and W = 32 cells
  measured and
  flipped 2026-10-23/24, and shape 2 measured and flipped at W = 256
  -- the shape-2 series' anchor -- 2026-10-24, and measured at W = 512
  2026-10-24 but REFUSED as a selection basis (rule 2 REGIME-SCOPED),
  and measured and flipped at W = 1024 2026-10-24, and measured and
  flipped at W = 128 2026-10-24 (the shape-2 series' first
  identity-HOLDS cell) and measured and flipped at W = 64 2026-10-24
  (the shape-2 series' second identity-HOLDS cell) and measured and
  flipped at W = 32 2026-10-24 (the shape-2 series' sixth and last
  cell);
  the remaining cells --
  cross-day
  replication -- OPEN)]. Every answer this row
  carries outside the six flip cells is UNMEASURED
  (`:measured? false`, rule 4's lock) until a hardware measurement
  replaces the basis text of the answer's cell.
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
   no unmeasured design row overrides them. At the design slice that was
   exactly the narrowed M1 Max class (name fragment `m1 max`): it kept
   `:baseline`
   at every `W` (W = 64/128/256/512/1024 where `:subgroup-reduce` was
   measured slower, W = 32 by the low-band fail-safe decision) -- every
   one of those cells has since flipped through the flip contract below,
   the flip keys' own refusals the carve-out's only live cells.
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
   [UPDATE 2026-10-23, the FLIP SLICE (rule 3 step 3, later same-day):
   a measurement of THIS variant on that class ran at ONE cell -- W = 256,
   n = 1000003, the native-Metal channel (the step-3 record,
   `docs/evidence/gpu-simdgroup-reduce-m1max-20261023`) -- and measured
   it FASTER than `:baseline` (paired median ratios 0.790/0.800/0.799
   for `:sum`/`:max`/`:min`, claim-protocol rule 2 REGIME-INVARIANT
   FASTER, 18/18 per-run ratios below 1.0). The flip contract's keys
   hold exactly there (name fragment `m1 max`, reported subgroup size
   32, the MSL route, this row's `:simd-reduce` gate, W = 256), the
   carve-out lifts exactly there, and the cell answers
   `:simdgroup-reduce` with `:measured? true` and the row's OWN
   `:measured-cell` record (`:shapes [1000003]` -- ONE measured shape at
   that slice; shape 2 stayed UNMEASURED at that slice, later measured
   and flipped at five cells by the shape-2 series below and refused at
   W = 512). Every other W of this class kept the
   carve-out's `:baseline` with the lock on at that slice (every one
   flipped by its own later slice below). The flip is code in
   `select-variant` (`simd-flip?`,
   `apple-simdgroup-measured-workgroups #{256}`), pinned by
   `the-simdgroup-rows-own-flip-cell-flips-the-honesty-lock`.]
   [UPDATE 2026-10-23, the W = 512 FLIP SLICE (rule 3 step 3's W-sweep
   second cell, flipped later the same day): the W-sweep measurement of
   THIS variant at W = 512, n = 1000003 (the W-sweep record,
   `docs/evidence/gpu-simdgroup-reduce-m1max-wsweep-20261023/w512`) ran
   the byte-identical protocol and measured it FASTER than `:baseline`
   (paired median ratios 0.815/0.823/0.824 for `:sum`/`:max`/`:min`,
   claim-protocol rule 2 REGIME-INVARIANT FASTER, 18/18 per-run ratios
   below 1.0). The flip contract's keys hold exactly there too (same
   class, route and gate; W = 512), the carve-out lifts exactly there,
   and the cell answers `:simdgroup-reduce` with `:measured? true` and
   the row's OWN `:measured-cell` record (`:shapes [1000003]`, the
   `:evidence` naming this cell's own runs -- each flip cell names ITS
   OWN record). The flip is code in `select-variant`
   (`apple-simdgroup-measured-workgroups #{256 512}`,
   `apple-simdgroup-measured-evidence` keyed per W). Every other W of
   this class (32/64/128/1024) kept the carve-out's `:baseline` with
   the lock on at that slice (every one flipped by its own later slice
   below). Slice record:
   `docs/evidence/gpu/simdgroup-reduce-flip-w512-20261023.txt`.]
   [UPDATE 2026-10-24, the W = 1024 FLIP SLICE (rule 3 step 3's W-sweep
   third cell, measured and flipped 2026-10-24): the W-sweep measurement
   of THIS variant at W = 1024, n = 1000003 (the W-sweep record,
   `docs/evidence/gpu-simdgroup-reduce-m1max-wsweep-20261023/w1024`) ran
   the byte-identical protocol and measured it FASTER than `:baseline`
   (paired median ratios 0.840/0.847/0.850 for `:sum`/`:max`/`:min`,
   claim-protocol rule 2 REGIME-INVARIANT FASTER, 18/18 per-run ratios
   below 1.0). The flip contract's keys hold exactly there too (same
   class, route and gate; W = 1024), the carve-out lifts exactly there,
   and the cell answers `:simdgroup-reduce` with `:measured? true` and
   the row's OWN `:measured-cell` record (`:shapes [1000003]`, the
   `:evidence` naming this cell's own runs -- each flip cell names ITS
   OWN record). The flip is code in `select-variant`
   (`apple-simdgroup-measured-workgroups #{256 512 1024}`,
   `apple-simdgroup-measured-evidence` keyed per W). Every other W of
   this class (32/64/128) kept the carve-out's `:baseline` with
   the lock on at that slice (every one flipped by its own later slice
   below). Slice record:
   `docs/evidence/gpu/simdgroup-reduce-flip-w1024-20261024.txt`.]
   [UPDATE 2026-10-24, the W = 128 FLIP SLICE (rule 3 step 3's W-sweep
   fourth cell, measured and flipped 2026-10-24): the W-sweep measurement
   of THIS variant at W = 128, n = 1000003 (the W-sweep record,
   `docs/evidence/gpu-simdgroup-reduce-m1max-wsweep-20261023/w128`) ran
   the byte-identical protocol and measured it FASTER than `:baseline`
   (paired median ratios 0.775/0.789/0.789 for `:sum`/`:max`/`:min`,
   claim-protocol rule 2 REGIME-INVARIANT FASTER, 18/18 per-run ratios
   below 1.0 -- the opposite sign to `:subgroup-reduce` at the identical
   cell, 1.244/1.243/1.234). The flip contract's keys hold exactly there
   too (same
   class, route and gate; W = 128), the carve-out lifts exactly there,
   and the cell answers `:simdgroup-reduce` with `:measured? true` and
   the row's OWN `:measured-cell` record (`:shapes [1000003]`, the
   `:evidence` naming this cell's own runs -- each flip cell names ITS
   OWN record). The flip is code in `select-variant`
   (`apple-simdgroup-measured-workgroups #{128 256 512 1024}`,
   `apple-simdgroup-measured-evidence` keyed per W). Every other W of
   this class (32/64) kept the carve-out's `:baseline` with
   the lock on at that slice (both flipped by their own later slices
   below). Slice record:
   `docs/evidence/gpu/simdgroup-reduce-flip-w128-20261024.txt`.]
   [UPDATE 2026-10-24, the W = 64 FLIP SLICE (rule 3 step 3's W-sweep
   fifth cell, measured and flipped 2026-10-24): the W-sweep measurement
   of THIS variant at W = 64, n = 1000003 (the W-sweep record,
   `docs/evidence/gpu-simdgroup-reduce-m1max-wsweep-20261023/w64`) ran
   the byte-identical protocol and measured it FASTER than `:baseline`
   (paired median ratios 0.719/0.728/0.729 for `:sum`/`:max`/`:min`,
   claim-protocol rule 2 REGIME-INVARIANT FASTER, 18/18 per-run ratios
   below 1.0 -- the opposite sign to `:subgroup-reduce` at the identical
   cell, 1.218/1.216/1.214). The flip contract's keys hold exactly there
   too (same
   class, route and gate; W = 64), the carve-out lifts exactly there,
   and the cell answers `:simdgroup-reduce` with `:measured? true` and
   the row's OWN `:measured-cell` record (`:shapes [1000003]`, the
   `:evidence` naming this cell's own runs -- each flip cell names ITS
   OWN record). The flip is code in `select-variant`
   (`apple-simdgroup-measured-workgroups #{64 128 256 512 1024}`,
   `apple-simdgroup-measured-evidence` keyed per W). Every other W of
   this class (32) kept the carve-out's `:baseline` with
   the lock on at that slice (flipped by the W = 32 slice below) -- and
   with W = 64 flipped, the carve-out note's
   flag-scope clause is HISTORY: no cell carries both the note and a
   `:measured? true` flag. Slice record:
   `docs/evidence/gpu/simdgroup-reduce-flip-w64-20261024.txt`.]
   [UPDATE 2026-10-24, the W = 32 FLIP SLICE (rule 3 step 3's W-sweep
   sixth and last cell, measured and flipped 2026-10-24): the W-sweep
   measurement of THIS variant at W = 32, n = 1000003 (the W-sweep
   record,
   `docs/evidence/gpu-simdgroup-reduce-m1max-wsweep-20261023/w32`) ran
   the byte-identical protocol and measured it FASTER than `:baseline`
   (paired median ratios 0.657/0.658/0.650 for `:sum`/`:max`/`:min`,
   claim-protocol rule 2 REGIME-INVARIANT FASTER, 18/18 per-run ratios
   below 1.0). The contrast with `:subgroup-reduce` at this cell reaches
   only the WEAKER form: the shuffle ladder measures MIXED here
   (0.918/0.923/1.019 -- the `:min` operator's per-run ratios straddle
   1.0, that cell's verdict is regime-scoped) and only THIS fold is
   one-sided, so the W = 32 flip rests on this fold's own 18/18, not on
   the opposite-sign contrast (which holds at W = 64/128/256/512/1024
   only). The flip contract's keys hold exactly here too (same
   class, route and gate; W = 32), the carve-out lifts exactly here,
   and the cell answers `:simdgroup-reduce` with `:measured? true` and
   the row's OWN `:measured-cell` record (`:shapes [1000003]`, the
   `:evidence` naming this cell's own runs -- each flip cell names ITS
   OWN record). The flip is code in `select-variant`
   (`apple-simdgroup-measured-workgroups #{32 64 128 256 512 1024}`,
   `apple-simdgroup-measured-evidence` keyed per W). These six are
   every width the row admits (a power of two in [32, 1024]): the
   class's W band is flipped end to end and NO admitted width of the
   class keeps the carve-out at the measured reported width any more --
   the carve-out's remaining live cells are the flip keys' own refusals
   (a `m1 max` descriptor whose reported SIMD-group width is not the
   measured 32). The class's last `:baseline` cell is gone with this
   slice. Slice record:
   `docs/evidence/gpu/simdgroup-reduce-flip-w32-20261024.txt`.]
   [UPDATE 2026-10-24, the SHAPE-2 W = 256 FLIP SLICE (the shape-2
   series' anchor cell, measured and flipped 2026-10-24): the shape-2
   measurement of THIS variant at W = 256, n = 2^20
   (`docs/evidence/gpu-simdgroup-reduce-m1max-shape2-20261024/w256`) ran
   the byte-identical protocol (the padded-lane tail gone -- n = 2^20 is
   a clean multiple of every W in [32, 1024]) and measured it FASTER
   than `:baseline` again (paired median ratios 0.794/0.811/0.812 for
   `:sum`/`:max`/`:min`, claim-protocol rule 2 REGIME-INVARIANT FASTER,
   18/18 per-run ratios below 1.0 -- within ~1-2 ratio points of the
   shape-1 anchor's 0.790/0.800/0.799, so the W = 256 win is not a
   padded-tail artifact of the ground shape). The sign contrast with
   `:subgroup-reduce` holds at this shape in its stronger form (one-sided
   slower at this cell in both its shape-2 records, 1.227/1.223/1.220
   and the re-sweep 1.226/1.225/1.225). The flip contract's keys hold at
   this second shape of the W = 256 cell, and the cell's
   `:measured-cell` record now names BOTH measured shapes
   (`:shapes [1000003 1048576]`) and both records in `:evidence`. The
   flip is code in `select-variant`
   (`apple-simdgroup-measured-shapes` keyed per W -- W = 256
   `[1000003 1048576]`, the other five widths `[1000003]` unchanged --
   `apple-simdgroup-measured-evidence`'s W = 256 entry gaining the
   shape-2 record). WHAT THIS SLICE DOES NOT LICENSE: shape 2 at the
   five widths but W = 256 stayed UNMEASURED at that slice (the
   shape-2 series' remaining cells -- all flipped by their own later
   slices below except the W = 512 refusal); no `:measured?` flag moves
   (the W = 256 answer was
   already MEASURED at the ground shape); no workgroup row
   (ADR-0355/0358) moves. Slice record:
   `docs/evidence/gpu/simdgroup-reduce-flip-shape2-w256-20261024.txt`.]
   [UPDATE 2026-10-24, the SHAPE-2 W = 512 FLIP SLICE (the shape-2
   series' second cell, measured earlier the same day -- REFUSED, the
   flip contract's first measured-but-scoped cell): the shape-2
   measurement of THIS variant at W = 512, n = 2^20
   (`docs/evidence/gpu-simdgroup-reduce-m1max-shape2-20261024/w512`) ran
   the byte-identical protocol and measured pooled medians
   0.812/0.821/0.822 for `:sum`/`:max`/`:min` (in family with the
   shape-1 same-W record 0.815/0.823/0.824) -- but claim-protocol rule 2
   classifies the CELL REGIME-SCOPED, NOT a selection basis: `:sum` and
   `:max` are REGIME-INVARIANT FASTER (6/6 each) yet `:min` straddles
   1.0 INSIDE one regime (run 3 at 1.054, run 5 at 0.821; 1 of 18 pooled
   per-run ratios above 1.0). Rule 2's second sentence denies a
   regime-scoped sign any selection role whatever its shape, so the flip
   REFUSES this cell and NOTHING extends: the W = 512 record keeps
   `:shapes [1000003]` and the W-sweep w512 runs as its `:evidence`, no
   `:measured?` flag moves (the W = 512 answer stands on the shape-1
   cell's REGIME-INVARIANT basis) and no workgroup row (ADR-0355/0358)
   moves. The contrast is the W = 256 cell's shape-2 record above
   (REGIME-INVARIANT FASTER at that shape): a shape enters a flip cell's
   record only on the cell's own rule-2 verdict at that shape. Slice
   record:
   `docs/evidence/gpu-simdgroup-reduce-flip-shape2-w512-refused-20261024.txt`.]
   [UPDATE 2026-10-24, the SHAPE-2 W = 1024 FLIP SLICE (the shape-2
   series' third cell, measured and flipped 2026-10-24): the shape-2
   measurement of THIS variant at W = 1024, n = 2^20
   (`docs/evidence/gpu-simdgroup-reduce-m1max-shape2-20261024/w1024`)
   ran the byte-identical protocol (no padded-lane tail) and measured it
   FASTER than `:baseline` again (paired median ratios
   0.836/0.843/0.841 for `:sum`/`:max`/`:min`, claim-protocol rule 2
   REGIME-INVARIANT FASTER, 18/18 per-run ratios below 1.0 -- every
   observed regime one-sided; in family with the shape-1 same-W record
   0.840/0.847/0.850 and the shape-2 anchor 0.794/0.811/0.812 --
   one-sided again after the W = 512 straddle). The flip contract's
   keys hold at this second shape of the W = 1024 cell, and the cell's
   `:measured-cell` record now names BOTH measured shapes
   (`:shapes [1000003 1048576]`) and both records in `:evidence`. The
   flip is code in `select-variant`
   (`apple-simdgroup-measured-shapes` keyed per W -- W = 256 and
   W = 1024 `[1000003 1048576]`, the other four widths `[1000003]`
   unchanged -- `apple-simdgroup-measured-evidence`'s W = 1024 entry
   gaining the shape-2 record). No `:measured?` flag moves (the W = 1024
   answer was already MEASURED at the ground shape) and no workgroup row
   (ADR-0355/0358) moves. WHAT THIS SLICE DOES NOT LICENSE: shape 2 at
   W = 32/64/128 stayed UNMEASURED at that slice (the shape-2 series'
   remaining cells -- all flipped by the SHAPE-2 W = 128, W = 64 and
   W = 32 slices below) and stays measured-but-REFUSED at W = 512.
   Slice record:
   `docs/evidence/gpu-simdgroup-reduce-flip-shape2-w1024-20261024.txt`.]
   [UPDATE 2026-10-24, the SHAPE-2 W = 128 FLIP SLICE (the shape-2
   series' fourth cell, measured and flipped 2026-10-24): the shape-2
   measurement of THIS variant at W = 128, n = 2^20
   (`docs/evidence/gpu-simdgroup-reduce-m1max-shape2-20261024/w128`)
   ran the byte-identical protocol (no padded-lane tail) and measured it
   FASTER than `:baseline` again (paired median ratios
   0.769/0.780/0.780 for `:sum`/`:max`/`:min`, claim-protocol rule 2
   REGIME-INVARIANT FASTER, 18/18 per-run ratios below 1.0 -- every
   observed regime one-sided; in family with the shape-1 same-W record
   0.775/0.789/0.789 and faster than the shape-2 anchor
   0.794/0.811/0.812 at every operator). Rule 1 sees ONE level per
   operator and cross-operator level identity HOLDS (all 15 run pairs
   agree) -- the shape-2 series' first cell this clean (the anchor 8/15
   divergent pairs, W = 512 11/15 plus the `:min` straddle, W = 1024
   5/15 -- all published identity REFUTED). The flip contract's keys
   hold at this second shape of the W = 128 cell, and the cell's
   `:measured-cell` record now names BOTH measured shapes
   (`:shapes [1000003 1048576]`) and both records in `:evidence`. The
   flip is code in `select-variant`
   (`apple-simdgroup-measured-shapes` keyed per W -- W = 256, W = 1024
   and W = 128 `[1000003 1048576]`, the other three widths
   `[1000003]` unchanged -- `apple-simdgroup-measured-evidence`'s
   W = 128 entry gaining the shape-2 record). No `:measured?` flag
   moves (the W = 128 answer was already MEASURED at the ground shape)
   and no workgroup row (ADR-0355/0358) moves. WHAT THIS SLICE DOES
   NOT LICENSE: shape 2 at W = 32/64 stayed UNMEASURED at that slice
   (the shape-2 series' remaining cells -- both flipped by the SHAPE-2
   W = 64 and W = 32 slices below) and stays measured-but-REFUSED at
   W = 512. Slice record:
   `docs/evidence/gpu-simdgroup-reduce-flip-shape2-w128-20261024.txt`.]
   [UPDATE 2026-10-24, the SHAPE-2 W = 64 FLIP SLICE (the shape-2
   series' fifth cell, measured and flipped 2026-10-24): the shape-2
   measurement of THIS variant at W = 64, n = 2^20
   (`docs/evidence/gpu-simdgroup-reduce-m1max-shape2-20261024/w64`)
   ran the byte-identical protocol (no padded-lane tail) and measured it
   FASTER than `:baseline` again (paired median ratios
   0.721/0.732/0.729 for `:sum`/`:max`/`:min`, claim-protocol rule 2
   REGIME-INVARIANT FASTER, 18/18 per-run ratios below 1.0 -- every
   observed regime one-sided; in family with the shape-1 same-W record
   0.719/0.728/0.729 and the fastest shape-2 cell of the series at
   every operator). Rule 1 sees ONE level per operator and
   cross-operator level identity HOLDS (all 15 run pairs agree) -- the
   shape-2 series' second identity-HOLDS cell after W = 128. The
   opposite-sign contrast with `:subgroup-reduce` at the identical cell
   holds in its stronger form (one-sided slower at this shape in both
   its shape-2 W = 64 records, 1.224/1.220/1.220 and the re-sweep
   1.223/1.217/1.219). The flip contract's keys hold at this second
   shape of the W = 64 cell, and the cell's `:measured-cell` record now
   names BOTH measured shapes (`:shapes [1000003 1048576]`) and both
   records in `:evidence`. The flip is code in `select-variant`
   (`apple-simdgroup-measured-shapes` keyed per W -- W = 256, W = 1024,
   W = 128 and W = 64 `[1000003 1048576]`, the other two widths
   `[1000003]` unchanged -- `apple-simdgroup-measured-evidence`'s
   W = 64 entry gaining the shape-2 record). No `:measured?` flag
   moves (the W = 64 answer was already MEASURED at the ground shape)
   and no workgroup row (ADR-0355/0358) moves. WHAT THIS SLICE DOES
   NOT LICENSE: shape 2 at W = 32 stayed UNMEASURED at that slice
   (flipped by the SHAPE-2 W = 32 slice below) and stays
   measured-but-REFUSED at
   W = 512. Slice record:
   `docs/evidence/gpu/simdgroup-reduce-flip-shape2-w64-20261024.txt`.]
   [UPDATE 2026-10-24, the SHAPE-2 W = 32 FLIP SLICE (the shape-2
   series' sixth and last cell, measured and flipped 2026-10-24): the
   shape-2 measurement of THIS variant at W = 32, n = 2^20
   (`docs/evidence/gpu-simdgroup-reduce-m1max-shape2-20261024/w32`)
   ran the byte-identical protocol (no padded-lane tail; S = 32
   divides W = 32 exactly -- one SIMD-group per workgroup) and
   measured it FASTER than `:baseline` again (paired median ratios
   0.639/0.656/0.659 for `:sum`/`:max`/`:min`, claim-protocol rule 2
   REGIME-INVARIANT FASTER, 18/18 per-run ratios below 1.0 -- every
   observed regime one-sided; in family with the shape-1 same-W record
   0.657/0.658/0.650). Rule 1 sees ONE level for `:max` and `:sum` but
   TWO for `:min` (the fresh-process clock ramp in `:min`'s runs only;
   both levels one-sided faster) and cross-operator level identity is
   REFUTED (8 of 15 run pairs diverge: min splits what max and sum
   pool) -- the shape-2 series' fourth identity-refuted cell against
   two identity-HOLDS cells (W = 128, W = 64). The opposite-sign
   contrast with `:subgroup-reduce` at the identical cell holds in its
   family form (the shuffle ladder's shape-2 W = 32 record measures
   near parity and straddling, 0.919/0.921/0.918, while THIS fold is
   one-sided faster at 18/18). The flip contract's keys hold at this
   second shape of the W = 32 cell, and the cell's `:measured-cell`
   record now names BOTH measured shapes (`:shapes [1000003 1048576]`)
   and both records in `:evidence`. The flip is code in `select-variant`
   (`apple-simdgroup-measured-shapes` keyed per W -- W = 256, W = 1024,
   W = 128, W = 64 and W = 32 `[1000003 1048576]`, W = 512
   `[1000003]` unchanged -- `apple-simdgroup-measured-evidence`'s
   W = 32 entry gaining the shape-2 record). No `:measured?` flag
   moves (the W = 32 answer was already MEASURED at the ground shape)
   and no workgroup row (ADR-0355/0358) moves. With this cell the
   shape-2 series covers the W band [32, 1024] end to end -- the
   series complete. WHAT THIS SLICE DOES NOT LICENSE: shape 2 stays
   measured-but-REFUSED at W = 512 (the shape-2 series' only unflipped
   cell) and every shape beyond the two measured ones stays
   UNMEASURED. Slice record:
   `docs/evidence/gpu/simdgroup-reduce-flip-shape2-w32-20261024.txt`.]
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

The composed contract's answer for a MEASURED-BUT-SCOPED cell (decided
2026-10-24 by the shape-2 W = 512 cell, the first of its kind -- nothing
new: rule 2's second sentence already denies a regime-scoped sign any
selection role whatever its shape): the cell is MEASURED (its runs are
recorded in `docs/evidence`) but it is NEVER a selection basis. It
extends no `:measured-cell` record's `:shapes` or `:evidence`, moves no
`:measured?` flag and moves no workgroup row; the flip at the cell's
other shapes stands on those shapes' own verdicts. A shape enters a
flip cell's record only when the cell's own rule-2 verdict at that
shape is REGIME-INVARIANT FASTER (the W = 256, W = 1024, W = 128,
W = 64 and W = 32
shape-2 records), and the
reduce shape is selected as a whole (`:operators #{:sum :max :min}`) --
the cell's pooled verdict governs; the contract has no per-operator
flip and none is invented here.

The composed contract's NAMING rule for same-day re-session records
(decided 2026-10-24, answering the question the W = 32 re-session
record deferred -- "Whether same-day re-session records are named in
the flip note / basis evidence lists at all"; the record:
`docs/evidence/gpu/same-day-resweep-naming-20261024.txt`): a same-day
re-session is NAMED in the flip note's prose only -- its own scoped
paragraph, carrying exactly the scoping its own record carries (not a
cross-day replication; extends no `:shapes`; moves no `:measured?`
flag, selection answer or workgroup row; magnitude phrases
regime-scoped within the day) -- and is NOT NAMED in the basis
evidence lists (`apple-simdgroup-measured-evidence` and the
`:measured-cell` `:evidence` maps), which stay closed under the
contract's record kinds: each cell's own flip runs (one per measured
shape) and its sanctioned cross-day replication runs. The rule's
ground is the re-session's own measured facts (sign replicates 18/18
same-day; medians moved 0.021/0.033/0.081 within one calendar day and
the cross-operator identity flipped HOLDS -> REFUTED) -- a same-day
session licenses nothing the cell's own run did not. The naming
implementation landed in the later same-day slice of 2026-10-24 (the
W = 32 SAME-DAY RE-SESSION paragraph in `apple-simdgroup-flip-note`,
the basis-lists docstring tightening, and tests pinning that no
basis-evidence list names a resweep directory) -- the rule is
IMPLEMENTED from that slice on.

The composed contract's cross-day replication LIST MEMBERSHIP rule
(decided 2026-10-24, answering the question the shape-2 cross-day
anchor record left OPEN -- "The shape-2 W = 32 cell's membership in
`the shape-2 cells` of the LEFT list is NOT settled by any record (the
shape-1 part excluded W = 32 as the decided cell; the LEFT list's
phrase does not say either way)"; the record:
`docs/evidence/gpu/subgroup-w32-leftlist-membership-20261024.txt`):
the cross-day replication row covers the FLIP CELLS -- the cells whose
own contract-satisfying runs chose the answer the flip marks (the
`:subgroup-reduce` demotion's W = 64/128/256/512/1024 at the two
measured shapes; the `:simdgroup-reduce` flip's own six cells). A
DECIDED cell -- the W = 32 cell (`apple-w32-note`: measured, but its
verdicts are regime-scoped at every cell that sampled both clock
levels, so no regime-robust verdict ever chose its answer; the
decision did; `:measured? false`) -- is NOT a member at any shape:
the temporal row's role is corroboration of a flip basis ("its
sanctioned cross-day replication runs -- corroboration that flipped
nothing"), and a cell that never flipped has no basis for a
replication to corroborate. The membership decision also holds that
no re-run revisits the decision -- the same standing the shape-2
W = 512 refusal's scope row has ("resolving it is a protocol decision
on the refusal's scope, not a re-run"): if the W = 32 cell's data
story is ever reopened, it is reopened by a DECISION row on the
decision note's scope, never by a run on the LEFT list. What the
decision does NOT license: no `:measured?` flag, `:shapes` value,
selection answer or workgroup row (ADR-0355/0358) moves; the
`:simdgroup-reduce` family's W = 32 cross-day row is UNAFFECTED (that
cell IS a flip cell and keeps its own later-day row); the shape-2
W = 512 REGIME-SCOPED refusal's scope decision stays OPEN (its own
row -- closed later the same day by the REFUSAL SCOPE rule, below);
and a later-day W = 32 DATA run (pure data, explicitly
non-basis) is neither scheduled nor forbidden by this decision -- if
wanted, it is its own decision row. The rule is ACCEPTED DESIGN as of
this slice; naming it in `apple-w32-note`'s prose rides the
`:subgroup-reduce` naming slice the cross-day records already owe --
which landed later the same day (the SUBGROUP CROSS-DAY NAMING slice's
diff row below: the ten records named in `apple-narrow-note` /
`apple-measured-evidence`, the naming rule applied to that family's
lists, the membership decision named in `apple-w32-note`; the rule is
IMPLEMENTED for that family from that slice on).

The composed contract's REFUSAL SCOPE rule (decided 2026-10-24,
answering the standing row every record since the shape-2 W = 512
refusal carried -- "resolving it is a protocol decision on the
refusal's scope, not a re-run"; the record:
`docs/evidence/gpu/simdgroup-reduce-w512-refusal-scope-20261024.txt`):
the measured-but-scoped refusal's scope is the CELL-PAIR (W = 512,
n = 2^20) and its selection roles, in five parts. (S1) The denial
reaches exactly that pair's selection roles -- the pooled verdict, the
reduce shape selected as a whole (`:operators #{:sum :max :min}`), no
per-operator resurrection -- and no other cell, answer or workgroup
row: the W = 512 answer stands on the shape-1 pair's own
REGIME-INVARIANT basis, the refusal removes nothing from it. (S2) The
refused record (`docs/evidence/gpu-simdgroup-reduce-m1max-shape2-
20261024/w512`) is a regime-structure record in `docs/evidence` and
names no contract key; it never becomes a contract-satisfying record.
(S3) The refusal denies SELECTION, not DATA: no claim carrying a
selection or measured-answer role covers the pair (the standing
"no measured claim covers (W = 512, n = 2^20)" is scoped here to
exactly that), while the pair's measured facts stay citable as data
beside the refusal named. (S4) No run revisits the refusal -- not a
re-run, not a cross-day replication, not a data run; if the pair is
ever reopened it is by a DECISION row on this note's scope. (S5) The
refused pair is NOT a member of the cross-day replication LEFT list at
shape 2 (the temporal row corroborates a flip basis and the pair has
none at that shape -- the membership decision's own ground), so the
pending `:simdgroup-reduce` cross-day rows are the shape-1 pairs
W = 32/64/128/1024 and the shape-2 pairs W = 256/32/64/128/1024 --
nine rows, no shape-2 W = 512 row owed -- and a later-day DATA run at
the refused pair is neither scheduled nor forbidden (its own decision
row if wanted). The rule is ACCEPTED DESIGN as of this slice; naming
it in the flip note's SHAPE-2 W = 512 paragraph and the cross-day LEFT
prose landed later the same day (the REFUSAL SCOPE NAMING slice's diff
row below: the rule is IMPLEMENTED in the code prose from that slice
on).

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
- [FLIP SLICE, 2026-10-23 (rule 3 step 3's flip, the W = 256 cell
  flips):] `src/kotoba/compiler/accelerator_variants.cljk`: `simd-flip?`
  (the flip's key conjunction), `apple-simdgroup-measured-workgroups
  #{256}`, `apple-simdgroup-measured-shapes`,
  `apple-simdgroup-measured-evidence`, `apple-simdgroup-flip-note`, the
  flip's own `:measured-cell` record and the flip-aware ladder cond;
  `src/kotoba/compiler/accelerator_simdgroup_reduce.cljk`: honesty marks
  for the flip cell (docstrings only);
  `test/kotoba/compiler/accelerator_variants_test.cljk`:
  `the-simdgroup-rows-own-flip-cell-flips-the-honesty-lock` (new) plus
  the flip-aware carve-out block in
  `the-msl-ladder-selects-simdgroup-reduce-first`;
  `test/kotoba/compiler/accelerator_simdgroup_reduce_test.cljk`:
  `simdgroup-selection-has-landed-under-the-msl-ladder` updated to the
  flip contract (W = 256 answers the row, MEASURED).
  `docs/evidence/gpu/simdgroup-reduce-flip-20261023.txt`: the flip slice
  record (gate output included).
- [W = 512 FLIP SLICE, 2026-10-23 (rule 3 step 3's W-sweep second cell,
  flipped later the same day):] `src/kotoba/compiler/accelerator_variants.cljk`:
  `apple-simdgroup-measured-workgroups #{256 512}`,
  `apple-simdgroup-measured-evidence` keyed per W (each flip cell's
  record names ITS OWN runs), `apple-simdgroup-measured-shapes`,
  `apple-simdgroup-flip-note` (both cells), the carve-out note and the
  flip-aware ladder prose;
  `src/kotoba/compiler/accelerator_simdgroup_reduce.cljk`: honesty marks
  for the two flip cells (docstrings only);
  `test/kotoba/compiler/accelerator_variants_test.cljk` and
  `test/kotoba/compiler/accelerator_simdgroup_reduce_test.cljk`: the
  flip pins extended to both cells (per-W records), the carve-out
  blocks' W sets narrowed to 32/64/128/1024;
  `docs/evidence/gpu/simdgroup-reduce-flip-w512-20261023.txt`: the slice
  record (gate output included).
- [W = 1024 FLIP SLICE, 2026-10-24 (rule 3 step 3's W-sweep third cell,
  measured and flipped 2026-10-24):]
  `src/kotoba/compiler/accelerator_variants.cljk`:
  `apple-simdgroup-measured-workgroups #{256 512 1024}`,
  `apple-simdgroup-measured-evidence` keyed per W (each flip cell's
  record names ITS OWN runs), `apple-simdgroup-measured-shapes`,
  `apple-simdgroup-flip-note` (all three cells), the carve-out note and
  the flip-aware ladder prose;
  `src/kotoba/compiler/accelerator_simdgroup_reduce.cljk`: honesty marks
  for the three flip cells (docstrings only);
  `test/kotoba/compiler/accelerator_variants_test.cljk` and
  `test/kotoba/compiler/accelerator_simdgroup_reduce_test.cljk`: the
  flip pins extended to three cells (per-W records), the carve-out
  blocks' W sets narrowed to 32/64/128;
  `docs/evidence/gpu/simdgroup-reduce-flip-w1024-20261024.txt`: the slice
  record (gate output included).
- [W = 128 FLIP SLICE, 2026-10-24 (rule 3 step 3's W-sweep fourth cell,
  measured and flipped 2026-10-24):]
  `src/kotoba/compiler/accelerator_variants.cljk`:
  `apple-simdgroup-measured-workgroups #{128 256 512 1024}`,
  `apple-simdgroup-measured-evidence` keyed per W (each flip cell's
  record names ITS OWN runs), `apple-simdgroup-measured-shapes`,
  `apple-simdgroup-flip-note` (all four cells), the carve-out note and
  the flip-aware ladder prose;
  `src/kotoba/compiler/accelerator_simdgroup_reduce.cljk`: honesty marks
  for the four flip cells (docstrings only);
  `test/kotoba/compiler/accelerator_variants_test.cljk` and
  `test/kotoba/compiler/accelerator_simdgroup_reduce_test.cljk`: the
  flip pins extended to four cells (per-W records), the carve-out
  blocks' W sets narrowed to 32/64 (the non-flip-W carve-out cases moved
  from W = 128 to W = 64);
  `docs/evidence/gpu/simdgroup-reduce-flip-w128-20261024.txt`: the slice
  record (gate output included).
- [W = 64 FLIP SLICE, 2026-10-24 (rule 3 step 3's W-sweep fifth cell,
  measured and flipped 2026-10-24):]
  `src/kotoba/compiler/accelerator_variants.cljk`:
  `apple-simdgroup-measured-workgroups #{64 128 256 512 1024}`,
  `apple-simdgroup-measured-evidence` keyed per W (each flip cell's
  record names ITS OWN runs), `apple-simdgroup-measured-shapes`,
  `apple-simdgroup-flip-note` (all five cells), the carve-out note (the
  class keeps `:baseline` at W = 32 only now, and its flag-scope clause
  is named as history -- no cell carries both the note and a true flag
  after this flip) and
  the flip-aware ladder prose;
  `src/kotoba/compiler/accelerator_simdgroup_reduce.cljk`: honesty marks
  for the five flip cells (docstrings only);
  `test/kotoba/compiler/accelerator_variants_test.cljk` and
  `test/kotoba/compiler/accelerator_simdgroup_reduce_test.cljk`: the
  flip pins extended to five cells (per-W records), the carve-out
  blocks' W sets narrowed to 32 (the non-flip-W carve-out cases moved
  from W = 64 to W = 32 -- the "both fact sets" case there now asserts
  the DECIDED cell's answer, `:measured? false` and no record, since
  W = 32 is not verdict-chosen);
  `docs/evidence/gpu/simdgroup-reduce-flip-w64-20261024.txt`: the slice
  record (gate output included).
- [SHAPE-2 W = 512 FLIP SLICE, 2026-10-24 (the shape-2 series' second
  cell, measured earlier the same day; REFUSED as a selection basis --
  the flip contract's first measured-but-scoped cell):]
  `src/kotoba/compiler/accelerator_variants.cljk`: the refusal named in
  `apple-simdgroup-measured-workgroups`,
  `apple-simdgroup-measured-shapes`, `apple-simdgroup-flip-note` (the
  SHAPE-2 W = 512 CELL paragraph) and the `simd-flip?` comment
  (docstrings and comments only -- NO map, NO lookup and NO answer
  moves: the W = 512 record keeps `:shapes [1000003]` and the W-sweep
  w512 runs as its `:evidence`);
  `src/kotoba/compiler/accelerator_simdgroup_reduce.cljk`: honesty marks
  for the refusal (docstring only);
  `test/kotoba/compiler/accelerator_variants_test.cljk`:
  `the-shape2-w512-scoped-cell-is-refused-as-a-selection-basis` (new --
  pins the refusal and the W = 256 contrast);
  `docs/evidence/gpu/simdgroup-reduce-flip-shape2-w512-refused-20261024.txt`:
  the slice record (gate output included).
- [SHAPE-2 W = 1024 FLIP SLICE, 2026-10-24 (the shape-2 series' third
  cell, measured and flipped the same day):]
  `src/kotoba/compiler/accelerator_variants.cljk`:
  `apple-simdgroup-measured-shapes` (W = 1024 now `[1000003 1048576]`,
  keyed per W; W = 256 unchanged), `apple-simdgroup-measured-evidence`'s
  W = 1024 entry gaining the shape-2 record (each flip cell names ITS
  OWN runs), `apple-simdgroup-flip-note` (the SHAPE-2 W = 1024 CELL
  paragraph), `apple-simdgroup-measured-workgroups` (the shape-2 scope
  prose), the `simd-flip?` comment unchanged (no lookup key changed --
  the flip keys were already per-W per-shape);
  `src/kotoba/compiler/accelerator_simdgroup_reduce.cljk`: honesty marks
  for the shape-2 flip (docstring only);
  `test/kotoba/compiler/accelerator_variants_test.cljk`: both flip-cell
  record blocks pin the W = 1024 two-shape record, the shapes block
  names W = 256 AND W = 1024 as the both-shapes cells, and
  `the-shape2-w512-scoped-cell-is-refused-as-a-selection-basis`'s
  contrast block gains the W = 1024 record;
  `docs/evidence/gpu-simdgroup-reduce-flip-shape2-w1024-20261024.txt`:
  the slice record (gate output included).
- [SHAPE-2 W = 128 FLIP SLICE, 2026-10-24 (the shape-2 series' fourth
  cell, measured and flipped the same day):]
  `src/kotoba/compiler/accelerator_variants.cljk`:
  `apple-simdgroup-measured-shapes` (W = 128 now `[1000003 1048576]`,
  keyed per W; W = 256 and W = 1024 unchanged),
  `apple-simdgroup-measured-evidence`'s W = 128 entry gaining the
  shape-2 record (each flip cell names ITS OWN runs),
  `apple-simdgroup-flip-note` (the SHAPE-2 FLIP OF THE W = 128 CELL
  paragraph), `apple-simdgroup-measured-workgroups` (the shape-2 scope
  prose), the `simd-flip?` comment unchanged (no lookup key changed --
  the flip keys were already per-W per-shape);
  `src/kotoba/compiler/accelerator_simdgroup_reduce.cljk`: honesty marks
  for the shape-2 flip (docstring only);
  `test/kotoba/compiler/accelerator_variants_test.cljk`: both flip-cell
  record blocks pin the W = 128 two-shape record and the basis names
  the shape-2 record and its ratios, the shapes block names W = 256,
  W = 1024 AND W = 128 as the both-shapes cells, and
  `the-shape2-w512-scoped-cell-is-refused-as-a-selection-basis`'s
  contrast block gains the W = 128 record;
  `docs/evidence/gpu-simdgroup-reduce-flip-shape2-w128-20261024.txt`:
  the slice record (gate output included).
- [SHAPE-2 W = 64 FLIP SLICE, 2026-10-24 (the shape-2 series' fifth
  cell, measured and flipped the same day):]
  `src/kotoba/compiler/accelerator_variants.cljk`:
  `apple-simdgroup-measured-shapes` (W = 64 now `[1000003 1048576]`,
  keyed per W; W = 256, W = 1024 and W = 128 unchanged),
  `apple-simdgroup-measured-evidence`'s W = 64 entry gaining the
  shape-2 record (each flip cell names ITS OWN runs),
  `apple-simdgroup-flip-note` (the SHAPE-2 FLIP OF THE W = 64 CELL
  paragraph), `apple-simdgroup-measured-workgroups` (the shape-2 scope
  prose), the `simd-flip?` comment unchanged (no lookup key changed --
  the flip keys were already per-W per-shape);
  `src/kotoba/compiler/accelerator_simdgroup_reduce.cljk`: honesty marks
  for the shape-2 flip (docstring only);
  `test/kotoba/compiler/accelerator_variants_test.cljk`: both flip-cell
  record blocks pin the W = 64 two-shape record and the basis names
  the shape-2 record and its ratios (0.721/0.732/0.729), the shapes
  block names W = 256, W = 1024, W = 128 AND W = 64 as the both-shapes
  cells, and
  `the-shape2-w512-scoped-cell-is-refused-as-a-selection-basis`'s
  contrast block gains the W = 64 record;
  `docs/evidence/gpu/simdgroup-reduce-flip-shape2-w64-20261024.txt`:
  the slice record (gate output included).
- [SHAPE-2 W = 32 FLIP SLICE, 2026-10-24 (the shape-2 series' sixth
  and last cell, measured and flipped the same day):]
  `src/kotoba/compiler/accelerator_variants.cljk`:
  `apple-simdgroup-measured-shapes` (W = 32 now `[1000003 1048576]`,
  keyed per W; W = 256, W = 1024, W = 128 and W = 64 unchanged),
  `apple-simdgroup-measured-evidence`'s W = 32 entry gaining the
  shape-2 record (each flip cell names ITS OWN runs),
  `apple-simdgroup-flip-note` (the SHAPE-2 FLIP OF THE W = 32 CELL
  paragraph, and the earlier paragraphs' shape-2 scope clauses
  corrected to what this flip makes true),
  `apple-simdgroup-measured-workgroups` (the shape-2 scope
  prose), the `simd-flip?` comment unchanged (no lookup key changed --
  the flip keys were already per-W per-shape);
  `src/kotoba/compiler/accelerator_simdgroup_reduce.cljk`: honesty marks
  for the shape-2 flip (docstring only);
  `test/kotoba/compiler/accelerator_variants_test.cljk`: both flip-cell
  record blocks pin the W = 32 two-shape record and the basis names
  the shape-2 record and its ratios (0.639/0.656/0.659), the shapes
  block names W = 256, W = 1024, W = 128, W = 64 AND W = 32 as the
  both-shapes cells (W = 512 alone names the ground shape), and
  `the-shape2-w512-scoped-cell-is-refused-as-a-selection-basis`'s
  contrast block gains the W = 32 record;
  `docs/evidence/gpu/simdgroup-reduce-flip-shape2-w32-20261024.txt`:
  the slice record (gate output included).
- [SAME-DAY RE-SESSION NAMING DECISION SLICE, 2026-10-24 (no code
  namespace, no test):] `docs/evidence/gpu/same-day-resweep-naming-20261024.txt`
  (the decision record) and this ADR (the NAMING rule paragraph in
  "Measurement contract and the flip" above, this diff row, and the
  LEFT row below). The naming implementation (the W = 32 SAME-DAY
  RE-SESSION paragraph, the basis-lists docstring tightening, their
  tests) is its own later slice and is NOT in this diff.
- [SAME-DAY RE-SESSION NAMING IMPLEMENTATION SLICE, 2026-10-24 (the
  later same-day slice):] the naming decision's follow-through, exactly
  its own scope:
  `src/kotoba/compiler/accelerator_variants.cljk` -- the W = 32
  SAME-DAY RE-SESSION paragraph in `apple-simdgroup-flip-note` (scoped
  exactly as the decision's part 1 names: not a cross-day replication;
  extends no `:shapes`; moves no `:measured?` flag, selection answer or
  workgroup row; magnitude phrases regime-scoped within the day) and
  the part-2 docstring tightening on both loci
  (`apple-simdgroup-measured-evidence`'s docstring and the
  `:measured-cell` `:evidence` map's construction comment -- closed
  under the flip contract's record kinds, stated not inferred);
  `test/kotoba/compiler/accelerator_variants_test.cljk` -- a naming
  block pinning the paragraph's scoping phrases and record name in
  `:basis` and pinning that no `:evidence` list names a resweep
  directory at any of the six cells;
  this ADR (the NAMING rule paragraph above, this diff row, the LEFT
  row below). No `:measured?` flag, `:shapes` value, selection answer
  or workgroup row moves: the exact `:measured-cell` record equality
  tests are byte-for-byte unchanged.
- [DIFF-RECORD RECONCILIATION SLICE, 2026-10-24 (this ADR only -- no
  code namespace, no test, no measurement):] the prose debt every slice
  record since the W = 32 flip slice has named -- the State and
  UNMEASURED sections' "five measured cells" / "only the W = 64,
  W = 128, W = 256, W = 512 and W = 1024 cells have flipped" / "every
  other W of this variant (32)" phrasings -- is PAID here: those
  phrasings are corrected in place to the record as it stands (six flip
  cells including W = 32, both measured shapes named at five of them,
  the W = 512 shape-2 refusal, cross-day replication measured at
  exactly two cells -- the W = 256 anchor and the W = 512 cell -- and
  UNMEASURED at every other), the flip and shape-2 UPDATE paragraphs'
  stale scope clauses ("Every other W of this class ... keeps the
  carve-out's `:baseline`", "shape 2 stays UNMEASURED") are brought to
  the past-tense per-slice form the W = 64 paragraph already carries,
  the Selection section's design-time carve-out clause ("Today ...
  keeps `:baseline` at every `W`") is framed as the design slice's
  state with the flips named as what followed, the LEFT rows'
  five-cell enumerations gain the sixth cell, and the "What did NOT
  move" debt marker is closed with its RECONCILED bracket. Nothing is
  re-measured (every number cited is the committed record's) and no
  `:measured?` flag, `:shapes` value, selection answer or workgroup row
  moves.
  `docs/evidence/gpu/adr0373-diffrecord-reconciliation-20261024.txt`:
  the slice record (gate output included).
- [SUBGROUP CROSS-DAY NAMING SLICE, 2026-10-24 (docstrings, tests, this
  ADR -- no measurement, no selection logic):] the `:subgroup-reduce`
  naming slice the ten cross-day records and the membership decision
  owed, exactly its own scope:
  `src/kotoba/compiler/accelerator_variants.cljk` -- the ten sanctioned
  cross-day records named in `apple-narrow-note` (the CROSS-DAY
  REPLICATION OF THE FLIP CELLS paragraph, per-row paired medians and
  rule-2 verdicts cited from the committed records, the shape-1
  w128 row's sign scoping named not hidden) and in
  `apple-measured-evidence` (the list widens to flip runs + sanctioned
  cross-day replication runs); the same-day-resweep naming rule applied
  to this family's lists (the docstring's closed-under-the-flip-contract's-
  record-kinds reading, stated not inferred; no resweep directory
  (`docs/evidence/gpu-subgroup-reduce-m1max-resweep-20261023/`) named in
  any list); the membership decision named in `apple-w32-note` (W = 32
  DECIDED OUT of the cross-day list at both measured shapes, decided not
  silent, no re-run revisits it);
  `test/kotoba/compiler/accelerator_variants_test.cljk` -- a naming
  block pinning the paragraph's scoping phrases and all ten record names
  in `:basis` and `:evidence`, the list's 15-entry shape, and that no
  `:evidence` list names a resweep directory; the W = 32 block pins the
  membership-decision paragraph and record name; the exact
  `:measured-cell` record equality block's `:evidence` vector names the
  ten records (the values moved, so its pins moved with them -- the
  record KEYS, `:shapes` values and every answer are byte-for-byte
  unchanged). Slice record:
  `docs/evidence/gpu/subgroup-crossday-naming-20261024.txt`. No
  `:measured?` flag, `:shapes` value, selection answer or workgroup row
  moves.
- [REFUSAL SCOPE DECISION SLICE, 2026-10-24 (this ADR + the decision
  record -- no code namespace, no test, no measurement):] the standing
  OPEN row every record since the shape-2 W = 512 refusal carried is
  ANSWERED: the refusal's scope is the cell-pair (W = 512, n = 2^20)
  and its selection roles (the five parts S1-S5 of the REFUSAL SCOPE
  rule paragraph above). Operative addition: the refused pair owes NO
  cross-day row (S5) -- LEFT row 3's cross-day part is narrowed to
  nine pending rows (shape-1 W = 32/64/128/1024, shape-2 W =
  256/32/64/128/1024); the rest anchors what the refusal slice already
  pinned. No `:measured?` flag, `:shapes` value, selection answer or
  workgroup row moves. Slice record:
  `docs/evidence/gpu/simdgroup-reduce-w512-refusal-scope-20261024.txt`.
- [REFUSAL SCOPE NAMING SLICE, 2026-10-24 (docstrings, tests, this ADR
  -- no measurement, no selection logic):] the naming the REFUSAL SCOPE
  rule paragraph above owed ("its own later naming slice"), exactly its
  own scope: `src/kotoba/compiler/accelerator_variants.cljk` -- the
  decision named in `apple-simdgroup-flip-note`'s SHAPE-2 W = 512
  paragraph (the scope is the CELL-PAIR and its selection roles, the
  record's own S1-S6 enumeration named in full, every number cited from
  the committed records) and in the cross-day LEFT prose (the LEFT list
  read as the decision narrowed it: NINE rows -- shape-1 W = 32/64/128/1024 and
  shape-2 W = 256/32/64/128/1024 -- and NO shape-2 W = 512 row owed);
  `test/kotoba/compiler/accelerator_variants_test.cljk` -- a naming
  block pinning the decision's record name, the scope sentence, the
  S3/S4 clauses, the LEFT narrowing, the nine-row list and the
  no-row-owed clause. Slice record:
  `docs/evidence/gpu/simdgroup-reduce-w512-scope-naming-20261024.txt`.
  No `:measured?` flag, `:shapes` value, selection answer or workgroup
  row moves.
- [SIMDGROUP CROSS-DAY NAMING SLICE, 2026-10-25 (docstrings, tests,
  this ADR -- no measurement, no selection logic):] the naming the
  nine 2026-10-25 cross-day rows' own notes and the cross-day LEFT
  list's closing slice owed, exactly its own scope:
  `src/kotoba/compiler/accelerator_variants.cljk` -- the nine
  sanctioned 2026-10-25 cross-day records named in
  `apple-simdgroup-flip-note` (the CROSS-DAY REPLICATION OF THE FLIP
  CELLS -- THE NINE LEFT ROWS paragraph: per-row paired medians and
  rule-2 verdicts cited from the committed records -- all nine
  REGIME-INVARIANT FASTER 18/18, sign reproducing strictly at every
  operator -- the magnitude phrases scoped per row, the directory-
  naming rule named) and in `apple-simdgroup-measured-evidence` (each
  W's list gains its cross-day replication record(s); the W = 512 cell
  keeps its one 2026-10-24 row -- the refused shape-2 W = 512 pair
  owes none, S5); the stale cross-day scope clauses brought current in
  place (the WHAT THE NUMBERS DO NOT LICENSE clause, the W = 512
  paragraph's LEFT prose closing with `all nine filled 2026-10-25`,
  and `apple-simdgroup-measured-workgroups`'s UNMEASURED list naming
  no cross-day row any more);
  `test/kotoba/compiler/accelerator_variants_test.cljk` -- the exact
  `:measured-cell` record equality blocks' `:evidence` maps carry the
  nine names (the values moved, so its pins moved with them -- the
  record keys, `:shapes` values and every selection answer are
  byte-for-byte unchanged), the cross-day block pins every owed cell's
  records (W = 512 alone keeps the 2026-10-24 row only), and a naming
  block pins the paragraph's scoping phrases and all nine record names
  in `:basis`; this ADR (this diff row, the UNMEASURED row below,
  LEFT row 3's closure bracket). Slice record:
  `docs/evidence/gpu/simdgroup-crossday-naming-20261025.txt`. No
  `:measured?` flag, `:shapes` value, selection answer or workgroup
  row moves.

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
- [The flip slice (2026-10-23) moved exactly ONE `:measured?` flag and
  added exactly ONE `:measured-cell` record -- this row's own W = 256
  cell on the narrowed M1 Max class, as scoped above. Everything else in
  the step-2 list is still unmoved; the workgroup rows (ADR-0355/0358)
  remain untouched and no speed claim extends past the flip cell's own
  recorded scope.]
- [The W = 512 flip slice (2026-10-23, later same-day) moved exactly ONE
  more `:measured?` flag and added exactly ONE more `:measured-cell`
  record -- this row's own W = 512 cell on the same class, as scoped
  above. Nothing else moved: the W = 256 record is untouched, the
  workgroup rows (ADR-0355/0358) remain untouched, and no speed claim
  extends past the two flip cells' own recorded scopes.]
- [The W = 1024 flip slice (2026-10-24) moved exactly ONE more
  `:measured?` flag and added exactly ONE more `:measured-cell`
  record -- this row's own W = 1024 cell on the same class, as scoped
  above. Nothing else moved: the W = 256 and W = 512 records are
  untouched, the workgroup rows (ADR-0355/0358) remain untouched, and no
  speed claim extends past the three flip cells' own recorded scopes.]
- [The W = 128 flip slice (2026-10-24) moved exactly ONE more
  `:measured?` flag and added exactly ONE more `:measured-cell`
  record -- this row's own W = 128 cell on the same class, as scoped
  above. Nothing else moved: the W = 256, W = 512 and W = 1024 records
  are
  untouched, the workgroup rows (ADR-0355/0358) remain untouched, and no
  speed claim extends past the four flip cells' own recorded scopes.]
- [The W = 64 flip slice (2026-10-24) moved exactly ONE more
  `:measured?` flag and added exactly ONE more `:measured-cell`
  record -- this row's own W = 64 cell on the same class, as scoped
  above. Nothing else moved: the W = 256, W = 512, W = 1024 and W = 128
  records are
  untouched, the workgroup rows (ADR-0355/0358) remain untouched, and no
  speed claim extends past the five flip cells' own recorded scopes.]
- [The shape-2 W = 512 flip slice (2026-10-24) landed a REFUSAL: no
  `:measured?` flag, no `:measured-cell` record's `:shapes` or
  `:evidence`, no selection answer and no workgroup row moved. The
  measurement itself stands recorded in `docs/evidence` as a
  regime-structure record and is refused every selection role -- measured
  is a fact about runs, not a license.]
- [The shape-2 W = 1024 flip slice (2026-10-24) moved NO `:measured?`
  flag (the W = 1024 answer was already MEASURED at the ground shape)
  and extended exactly ONE `:measured-cell` record -- the W = 1024
  cell's `:shapes` gaining its second shape and its `:evidence` the
  shape-2 record. Nothing else moved: the W = 256 and W = 512 records
  are untouched, the workgroup rows (ADR-0355/0358) remain untouched,
  and no speed claim extends past the flip cells' own recorded scopes.]
- [The shape-2 W = 128 flip slice (2026-10-24) moved NO `:measured?`
  flag (the W = 128 answer was already MEASURED at the ground shape)
  and extended exactly ONE `:measured-cell` record -- the W = 128
  cell's `:shapes` gaining its second shape and its `:evidence` the
  shape-2 record. Nothing else moved: the W = 256, W = 512 and W = 1024
  records are untouched, the workgroup rows (ADR-0355/0358) remain
  untouched, and no speed claim extends past the flip cells' own
  recorded scopes.]
- [The shape-2 W = 64 flip slice (2026-10-24) moved NO `:measured?`
  flag (the W = 64 answer was already MEASURED at the ground shape)
  and extended exactly ONE `:measured-cell` record -- the W = 64
  cell's `:shapes` gaining its second shape and its `:evidence` the
  shape-2 record. Nothing else moved: the W = 256, W = 512, W = 1024
  and W = 128 records are untouched, the workgroup rows (ADR-0355/0358)
  remain untouched, and no speed claim extends past the flip cells'
  own recorded scopes.]
- [The shape-2 W = 32 flip slice (2026-10-24) moved NO `:measured?`
  flag (the W = 32 answer was already MEASURED at the ground shape)
  and extended exactly ONE `:measured-cell` record -- the W = 32
  cell's `:shapes` gaining its second shape and its `:evidence` the
  shape-2 record. Nothing else moved: the W = 256, W = 512, W = 1024,
  W = 128 and W = 64 records are untouched, the workgroup rows
  (ADR-0355/0358) remain untouched, and no speed claim extends past
  the flip cells' own recorded scopes.]
  The ADR's older diff-record prose that predates the W = 32 flip's
  reconciliation (the "five measured cells" / "only the W = 64,
  W = 128, W = 256, W = 512 and W = 1024 cells have flipped" phrasings
  in the State and UNMEASURED sections) was named prose debt in every
  slice record since the W = 32 flip slice, not silently rewritten
  there. [RECONCILED 2026-10-24, the DIFF-RECORD RECONCILIATION slice:
  the named phrasings are corrected in place (State and UNMEASURED,
  below) to the record as it stands -- six flip cells including W = 32,
  both measured shapes named at five of them, the W = 512 shape-2
  refusal, cross-day replication measured at exactly two cells -- and
  the flip and shape-2 UPDATE paragraphs' stale scope clauses and the
  LEFT rows' five-cell enumerations are brought current in the
  past-tense per-slice form (the Selection section's design-time
  carve-out clause reframed as the design slice's state). The per-slice
  diff rows of "What moved" are
  history and stay as written (each names its own slice's state at its
  own commit). Nothing was re-measured (every number cited is the
  committed record's) and no `:measured?` flag, `:shapes` value,
  selection answer or workgroup row moved. Slice record:
  `docs/evidence/gpu/adr0373-diffrecord-reconciliation-20261024.txt`.]

## State (the honesty rule's three states)

[After rule 3 steps 1-2 (2026-10-23): IMPLEMENTED is the MSL emission +
`lower` admission + tests, AND the selection ladder -- the measured-cell
carve-out, the MSL ladder's two rungs, the `:simd-reduce` rule-6 gate --
+ its tests (the ladder's step-2 slice). STEP 3 (the later same-day
slice) adds MEASURED DATA, not implementation: the W = 256, n = 1000003
cell ran on M1 Max and its record is in the repo (ratio 0.790/0.800/0.799
vs `:baseline`, rule 2 regime-invariant faster). THE FLIP SLICE (also
2026-10-23) then moved ONE `:measured?` flag: the W = 256 cell of THIS
variant on the narrowed M1 Max class answers `:simdgroup-reduce` with
`:measured? true` and the row's own `:measured-cell` record
(`:shapes [1000003]`) -- implemented (`simd-flip?` + tests). THE W = 512
FLIP SLICE (later same-day) moved ONE more flag the same way: the
W = 512 cell (the W-sweep's second measured cell, ratios
0.815/0.823/0.824) answers `:simdgroup-reduce` with `:measured? true`
and its OWN record. THE W = 1024 FLIP SLICE (2026-10-24) moved ONE more
flag the same way: the W = 1024 cell (the W-sweep's third measured
cell, ratios 0.840/0.847/0.850) answers `:simdgroup-reduce` with
`:measured? true` and its OWN record. THE W = 128 FLIP SLICE
(2026-10-24) moved ONE more
flag the same way: the W = 128 cell (the W-sweep's fourth measured
cell, ratios 0.775/0.789/0.789) answers `:simdgroup-reduce` with
`:measured? true` and its OWN record. THE W = 64 FLIP SLICE
(2026-10-24) moved ONE more
flag the same way: the W = 64 cell (the W-sweep's fifth measured
cell, ratios 0.719/0.728/0.729) answers `:simdgroup-reduce` with
`:measured? true` and its OWN record. THE SHAPE-2 W = 256 FLIP SLICE
(2026-10-24) moved NO flag but ONE record: the W = 256 cell's
`:measured-cell` record now names BOTH measured shapes
(`:shapes [1000003 1048576]`, the shape-2 anchor's runs named in its
`:evidence`) -- the shape-2 measurement (0.794/0.811/0.812, rule 2
REGIME-INVARIANT FASTER, 18/18) extends the flip contract to the second
shape of that cell, and to that cell only. THE SHAPE-2 W = 512 FLIP
SLICE (2026-10-24) moved NOTHING and decided the contract's
measured-but-scoped answer: that cell's shape-2 measurement
(0.812/0.821/0.822, rule 2 REGIME-SCOPED -- `:min` straddles 1.0 inside
one regime) is MEASURED but REFUSED as a selection basis, the W = 512
record keeps `:shapes [1000003]`, and the refusal is pinned by tests
(`the-shape2-w512-scoped-cell-is-refused-as-a-selection-basis`). THE
SHAPE-2 W = 1024 FLIP SLICE (2026-10-24) moved NO flag but ONE record:
the W = 1024 cell's `:measured-cell` record now names BOTH measured
shapes (`:shapes [1000003 1048576]`, the shape-2 third cell's runs
named in its `:evidence`) -- the shape-2 measurement at W = 1024
(0.836/0.843/0.841, rule 2 REGIME-INVARIANT FASTER, 18/18) extends the
flip contract to the second shape of that cell, and to that cell only
(shape 2 at W = 32/64/128 stayed UNMEASURED at that slice and at
W = 512 stays measured-but-REFUSED). THE SHAPE-2 W = 128 FLIP SLICE
(2026-10-24) moved NO flag but ONE record: the W = 128 cell's
`:measured-cell` record now names BOTH measured shapes
(`:shapes [1000003 1048576]`, the shape-2 fourth cell's runs named in
its `:evidence`) -- the shape-2 measurement at W = 128
(0.769/0.780/0.780, rule 2 REGIME-INVARIANT FASTER, 18/18, the
shape-2 series' first identity-HOLDS cell) extends the flip contract
to the second shape of that cell, and to that cell only (shape 2 at
W = 32/64 stayed UNMEASURED at that slice and at W = 512 stays
measured-but-REFUSED). THE SHAPE-2 W = 64 FLIP SLICE (2026-10-24)
moved NO flag but ONE record: the W = 64 cell's `:measured-cell`
record now names BOTH measured shapes (`:shapes [1000003 1048576]`,
the shape-2 fifth cell's runs named in its `:evidence`) -- the shape-2
measurement at W = 64 (0.721/0.732/0.729, rule 2 REGIME-INVARIANT
FASTER, 18/18, the shape-2 series' second identity-HOLDS cell) extends
the flip contract to the second shape of that cell (shape 2 at
W = 32 stayed UNMEASURED at that slice -- flipped by the SHAPE-2
W = 32 slice below -- and at W = 512 stays measured-but-REFUSED).
THE SHAPE-2 W = 32 FLIP SLICE (2026-10-24) moved NO flag but ONE
record: the W = 32 cell's `:measured-cell` record now names BOTH
measured shapes (`:shapes [1000003 1048576]`, the shape-2 sixth
cell's runs named in its `:evidence`) -- the shape-2 measurement at
W = 32 (0.639/0.656/0.659, rule 2 REGIME-INVARIANT FASTER, 18/18)
extends the flip contract to the second shape of that cell and
completes the shape-2 series (the W band [32, 1024] end to end at
both measured shapes but the W = 512 refusal).
ACCEPTED
DESIGN ONLY: any wording above that governs this variant's OTHER future
measurement cells (the flip contract as applied to `:simdgroup-reduce` --
the W = 32, W = 64, W = 128, W = 256, W = 512 and W = 1024 cells have
flipped, every width the row admits: the ground shape flipped at all
six, the second shape at five of them, the W = 512 shape-2 cell
measured-but-REFUSED). The REFUSAL SCOPE rule (2026-10-24, the
measurement-contract section above) is likewise ACCEPTED DESIGN ONLY
until its own naming slice.
PROPOSED, unchanged: every performance question about this variant off
the six measured cells.] The
two design
questions ADR-0356's reconciliation parked are now both DECIDED
(narrowing: ADR-0360's second decision; this row: this ADR).

## UNMEASURED, named

Everything about this variant's performance on every device but the six
measured cells (M1 Max, W = 32, W = 64, W = 128, W = 256, W = 512 and
W = 1024,
n = 1000003 --
measured and
flipped 2026-10-23/24,
faster than `:baseline` at those cells, see the step-3 and W-sweep
records); every shape beyond the two measured ones (n = 1000003 and
n = 2^20) at every cell; cross-day replication at every cell but the
eleven replication rows now recorded (the W = 256 anchor and the
W = 512 cell, both 2026-10-24, and the nine LEFT rows, all 2026-10-25
-- nothing owed remains; the refused shape-2 W = 512 pair owes none,
S5 -- the W = 32 same-day re-session is NOT a cross-day
replication and licenses nothing the cell's own run did not); shape 2
for this variant at W = 512 --
measured 2026-10-24 but REFUSED as a selection basis (rule 2
REGIME-SCOPED), so no measured claim covers it
(its W = 256, W = 1024, W = 128, W = 64 and W = 32 shape-2 flips
landed 2026-10-24 --
those cells are measured and flipped at both measured shapes);
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

(the SHAPE-2 W = 32 flip slice, 2026-10-24: this slice changes the
two accelerator namespaces' records and pins tests in
`accelerator-variants-test` -- targeted two namespaces green (27 tests,
8462 assertions, 0 failures) and the scoped GPU gate green (101 tests,
9624 assertions, 0 failures); counts in the slice record
`docs/evidence/gpu/simdgroup-reduce-flip-shape2-w32-20261024.txt`;
the gate's `$(kbb -Spath -M:test)` subshell is broken at this
branch's HEAD -- the host-manifest retirement the measure record's
CHANNEL NOTE names -- so the runs substituted the record's resolved
closure inline, named there).

Full suite (`run-tests.cljk`): RED AT BASE at namespace load on
`kotoba.form` (the W3 port path, documented red at base in ADR 0362),
outside this diff. No green full suite is claimed.

## LEFT (the next rows)

1. [STEPS 1-2 DONE 2026-10-23: (1) the MSL emission + `lower` admission
   + tests; (2) the selection predicate (the ladder, the carve-out, the
   `:simd-reduce` gate fact) + tests. STEP 3 STARTED 2026-10-23: the
   W = 256, n = 1000003 cell measured on M1 Max (faster than
   `:baseline`, rule 2 regime-invariant), as did the W-sweep's second
   cell (W = 512, 0.815/0.823/0.824, same day) and its third cell
   (W = 1024, 0.840/0.847/0.850, 2026-10-24), its fourth cell
   (W = 128, 0.775/0.789/0.789, 2026-10-24), its fifth cell
   (W = 64, 0.719/0.728/0.729, 2026-10-24) and its sixth and last cell
   (W = 32, 0.657/0.658/0.650, 2026-10-24). The flip slices (item 2)
   are
   DONE (W = 256 and W = 512 the same day, W = 1024, W = 128, W = 64
   and W = 32
   on
   2026-10-24).]
   Rule 3's order keeps the rest
   of (3) next: the remaining cells.
2. [(step 3) DONE 2026-10-23/24, the flip slices: what the W = 256,
   W = 512, W = 1024, W = 128 and W = 64 numbers
   license under the flip contract is ANSWERED -- this VARIANT's own
   cells keyed by name fragment, reported subgroup size, route, channel,
   W set and shapes, one cell set at a time: exactly the W = 64,
   W = 128,
   W = 256,
   W = 512 and W = 1024,
   n = 1000003 cells of the narrowed M1 Max class flipped
   (`simd-flip?`, `apple-simdgroup-measured-workgroups #{64 128 256 512 1024}`,
   `:shapes [1000003]`), every other cell keeps the lock. The flips'
   records: docs/evidence/gpu/simdgroup-reduce-flip-20261023.txt,
   docs/evidence/gpu/simdgroup-reduce-flip-w512-20261023.txt,
   docs/evidence/gpu/simdgroup-reduce-flip-w1024-20261024.txt,
   docs/evidence/gpu/simdgroup-reduce-flip-w128-20261024.txt and
   docs/evidence/gpu/simdgroup-reduce-flip-w64-20261024.txt. At that
   row exactly those five cells at the ground shape had flipped; the
   W = 32 cell flipped in its own later same-day slice
   (docs/evidence/gpu/simdgroup-reduce-flip-w32-20261024.txt) and the
   second shape landed at five cells in the shape-2 series -- the keys
   are now `apple-simdgroup-measured-workgroups #{32 64 128 256 512
   1024}` and per-W `:shapes` (five of them `[1000003 1048576]`, the
   W = 512 refusal `[1000003]`).] The
   flip: what the W = 256 numbers license under the flip
   contract -- this VARIANT's own cells keyed by name fragment, reported
   subgroup size, route, channel, W set and shapes -- one cell set at a
   time. Until it lands no `:measured?` flag moves.
3. (step 3) Measure the remaining cells (cross-day
   replication of every cell; the shape-2 series is COMPLETE -- its
   W = 256 anchor, W = 1024 third cell, W = 128
   fourth cell, W = 64 fifth cell and W = 32 sixth and last cell
   measured and
   flipped 2026-10-24 (the W = 128 and W = 64 cells the shape-2
   series' identity-HOLDS cells), its
   W = 512 cell measured 2026-10-24 and REFUSED as a selection basis
   (rule 2 REGIME-SCOPED) -- the shape-2 series' only unflipped
   cell) under the same claim protocol. [The shape-2 W = 512
   refusal's scope decision (2026-10-24,
   `docs/evidence/gpu/simdgroup-reduce-w512-refusal-scope-20261024.txt`)
   narrows this row's cross-day part: the refused pair owes NO
   cross-day row (S5 of the REFUSAL SCOPE rule), the pending rows are
   nine -- shape-1 W = 32/64/128/1024 and shape-2 W =
   256/32/64/128/1024.] [The eligibility check for those nine is
   SETTLED 2026-10-24
   (`docs/evidence/gpu/crossday-eligibility-stamps-20261024.txt`):
   all nine are 2026-10-25+ rows -- the shape-1 W = 1024 escape
   hatch ("unless its own run-log shows a 2026-10-23 run") is UNMET
   BY CONSTRUCTION (no instrument run-log carried a calendar), and
   the measurement driver now self-dates every fresh-process run
   (`run_started=`/`run_finished=` stamps), so from 2026-10-25 on
   the check reads the run-log's own stamps.] [The nine rows all
   FILLED 2026-10-25 and NAMED in the naming slice
   (`docs/evidence/gpu/simdgroup-crossday-naming-20261025.txt`): the
   cross-day part of this row is DONE -- zero pending rows; every row
   reproduces its flip basis in sign strictly (claim-protocol rule 2
   REGIME-INVARIANT FASTER, 18/18 per-run ratios below 1.0 at each
   row) at the paired medians cited in the flip note's CROSS-DAY
   REPLICATION OF THE FLIP CELLS -- THE NINE LEFT ROWS paragraph; the
   refused shape-2 W = 512 pair owes no row (S5). Nothing is
   re-measured by the naming slice (every number cited is the nine
   records') and no `:measured?` flag, `:shapes` value, selection
   answer or workgroup row moves.]
4. [DONE 2026-10-24 -- the list is COMPLETE at both shapes and the
   W = 32 cell's membership is DECIDED OUT of it (the cross-day
   replication list membership decision,
   `docs/evidence/gpu/subgroup-w32-leftlist-membership-20261024.txt`,
   answering the OPEN question every cross-day record since the shape-2
   anchor carried): ten later-day records corroborate the demotion basis
   at every flipped cell -- the anchor (W = 256) and W = 64/128/512/1024
   at shape 1 (`docs/evidence/gpu-subgroup-reduce-m1max-crossday-
   20261024/`) and the same five at shape 2
   (`docs/evidence/gpu-subgroup-reduce-m1max-crossday-shape2-20261024/`),
   all 2026-10-24. The decided cell (W = 32, `apple-w32-note`) is not a
   member at either shape: it never flipped, so the temporal row has no
   flip basis to corroborate, and no re-run revisits the decision --
   decided, not silent.] Cross-day replication of the existing
   `:subgroup-reduce` cells (needs a later-day cron tick).
5. The GLSL arm of `:subgroup-reduce` stays blocked on ADR 0371's provider
   route.
6. [DONE 2026-10-24, the later same-day slice -- the naming
   implementation landed, nothing left of this row:] the SAME-DAY
   RE-SESSION naming implementation (the 2026-10-24 naming decision's
   own follow-through, "its own slice" by that decision's terms): the
   W = 32 SAME-DAY RE-SESSION paragraph in
   `apple-simdgroup-flip-note` (scoped exactly as the decision's part 1
   names), the basis-lists docstring tightening (part 2), and tests
   pinning that no basis-evidence list names a resweep directory. The
   naming rule is IMPLEMENTED from that slice on (the NAMING rule
   paragraph above and the implementation diff row carry the scope).
