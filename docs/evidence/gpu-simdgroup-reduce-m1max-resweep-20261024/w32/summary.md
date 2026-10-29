# JUN-58: :baseline vs :simdgroup-reduce on Apple M1 Max at W = 32 -- the MSL arms on the native Metal route

- device: Apple M1 Max
- reported subgroup size ([[threads_per_simdgroup]]): 32
- n = 1000003 elements, workgroup W = 32 (a W-sweep cell, NOT the ADR-0358 row), 6 fresh-process runs
- shape: the historical shape (not a multiple of W: the padded-lane tail is exercised)
- emitted at W = 32 by the emitters' own bytes (shaders/; the variant arm's threadgroup partials array is sized from this W)
- protocol: 20 interleaved pairs per operator per run, alternating AB/BA order, 2 warmup submits per arm discarded (ADR-0358's sweep protocol)
- operator dispatch order: sum,max,min (the default fixed order every earlier cell used)
- timer: Metal GPU timestamps (command buffer GPUStartTime->GPUEndTime) around one reduce dispatch; host submit->completion ns recorded as secondary

| operator | arm | samples | median gpu ns | per-run medians | median host ns |
|---|---|---|---|---|---|
| sum | baseline | 120 | 109125 | 109104, 109270, 108312, 109438, 108854, 109438 | 316480 |
| sum | variant | 120 | 69396 | 70271, 70354, 68958, 69146, 68062, 69479 | 271938 |
| max | baseline | 120 | 108000 | 109375, 109188, 69021, 109375, 88438, 36166 | 289438 |
| max | variant | 120 | 64479 | 68229, 71750, 56812, 70229, 64062, 32666 | 250917 |
| min | baseline | 120 | 88979 | 109562, 109312, 59396, 109250, 68896, 36042 | 285916 |
| min | variant | 120 | 58084 | 69562, 67834, 54562, 68688, 56917, 32375 | 252666 |

Paired within-run comparison (the statistic of ADR-0358: per fresh process, median over its pairs of variant/baseline gpu-ns ratio, then the median of those):

| operator | per-run ratios | median ratio |
|---|---|---|
| sum | 0.644, 0.644, 0.637, 0.632, 0.625, 0.635 | 0.636 |
| max | 0.624, 0.657, 0.823, 0.642, 0.724, 0.903 | 0.691 |
| min | 0.635, 0.621, 0.919, 0.629, 0.826, 0.898 | 0.731 |

## Regime classification (claim protocol rule 1)

Published by scripts/gpu_regime_classify.py (GAP-1.15). The harness reads no GPU clock: a regime here is a cluster of the observed baseline per-run median gpu-ns levels, named by its gpu-ns range, per operator. Cross-operator level identity is tested mechanically and published in its own section below when the record has at least two operators. Rule 2's sign classification is published in its own section below when the record's per-run ratios are provided.

Clustering rule GAP-1.15: per operator, the per-run baseline medians sorted ascending, single-linkage -- the next median joins the current level at <= 1.15x the previous, else it starts a new level. 1.15 is the geometric midpoint of the committed records' decided separation window [1.075, 1.234] (within-level drift vs between-level step; see docs/evidence/gpu/regime-classification-20261023.txt).

| operator | level | gpu-ns range | runs (baseline per-run median) |
|---|---|---|---|
| max | 1 (fastest observed) | 36166 | 6 (36166) |
| max | 2 | 69021 | 3 (69021) |
| max | 3 | 88438 | 5 (88438) |
| max | 4 (slowest observed) | 109188..109375 | 1 (109375), 2 (109188), 4 (109375) |
| min | 1 (fastest observed) | 36042 | 6 (36042) |
| min | 2 | 59396 | 3 (59396) |
| min | 3 | 68896 | 5 (68896) |
| min | 4 (slowest observed) | 109250..109562 | 1 (109562), 2 (109312), 4 (109250) |
| sum | 1 (the only observed level) | 108312..109438 | 1 (109104), 2 (109270), 3 (108312), 4 (109438), 5 (108854), 6 (109438) |

## Cross-operator level identity (the rule-1 partition across operators)

Published by scripts/gpu_regime_classify.py: rule 1 classifies per operator; this section tests mechanically whether those classifications describe ONE regime structure. The test is partition agreement -- for every run pair, every operator must agree on whether the two runs sit in the same rule-1 level (GAP-1.15, applied per operator). The harness reads no GPU clock and asserts no clock identity: identity here is agreement of the run partitions, nothing more.

Verdict: **identity refuted** -- 12 of 15 run pairs diverge across max, min, sum (named below). Per-operator level names stay operator-scoped: one operator's fastest level is not another's.

Partition relations (the disagreement's shape where the partitions disagree): max and min: equal partitions; max's partition refines sum's (sum pools what max splits); min's partition refines sum's (sum pools what min splits).

Divergent run pairs (12 of 15):

| run pair | max | min | sum |
|---|---|---|---|
| 1 vs 3 | split-level | split-level | same-level |
| 1 vs 5 | split-level | split-level | same-level |
| 1 vs 6 | split-level | split-level | same-level |
| 2 vs 3 | split-level | split-level | same-level |
| 2 vs 5 | split-level | split-level | same-level |
| 2 vs 6 | split-level | split-level | same-level |
| 3 vs 4 | split-level | split-level | same-level |
| 3 vs 5 | split-level | split-level | same-level |
| 3 vs 6 | split-level | split-level | same-level |
| 4 vs 5 | split-level | split-level | same-level |
| 4 vs 6 | split-level | split-level | same-level |
| 5 vs 6 | split-level | split-level | same-level |

What this section does NOT do (rule 4, unchanged): it changes no rule-2 verdict, no rule-3 phrase, no selection answer, no `:measured?` flag, no workgroup row. Pair-level cross-operator identity is its own test at pair granularity (the pair-level section publishes it); nothing in this run-level section licenses or refutes a pair-level naming.

## Sign classification (claim protocol rule 2)

Published by scripts/gpu_regime_classify.py from the per-run paired ratios above and the rule-1 regime clusters. Rule 2: a sign is REGIME-INVARIANT when every per-run ratio of every observed regime lies on the same side of 1.0 -- only such a sign may be a selection basis. Any other cell is published REGIME-SCOPED and cannot choose a variant. The harness reads no clock: a regime is the rule-1 cluster. The cell row carries only the admissibility roll-up, no cross-operator regime structure -- cross-operator level identity (its own section) is a publication fact about the regime structure and never re-scopes a rule-2 verdict.

| operator | verdict | side | detail |
|---|---|---|---|
| max | regime-invariant | faster | all 6 per-run ratios below 1.0 (6/6 faster); every observed regime one-sided |
| min | regime-invariant | faster | all 6 per-run ratios below 1.0 (6/6 faster); every observed regime one-sided |
| sum | regime-invariant | faster | all 6 per-run ratios below 1.0 (6/6 faster); every observed regime one-sided |

Cell (all 18 per-run ratios pooled): **regime-invariant**, faster (18/18 faster).

Verified read-back (every fresh process):

```
run 1: verify op=sum arm=baseline max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=1.90734863e-06 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 1: verify op=sum arm=variant max_abs_vs_ref=1.43051147e-06 max_abs_vs_other=1.90734863e-06 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 1: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 1: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 1: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 1: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 2: verify op=sum arm=baseline max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=1.90734863e-06 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 2: verify op=sum arm=variant max_abs_vs_ref=1.43051147e-06 max_abs_vs_other=1.90734863e-06 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 2: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 2: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 2: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 2: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 3: verify op=sum arm=baseline max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=1.90734863e-06 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 3: verify op=sum arm=variant max_abs_vs_ref=1.43051147e-06 max_abs_vs_other=1.90734863e-06 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 3: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 3: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 3: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 3: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 4: verify op=sum arm=baseline max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=1.90734863e-06 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 4: verify op=sum arm=variant max_abs_vs_ref=1.43051147e-06 max_abs_vs_other=1.90734863e-06 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 4: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 4: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 4: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 4: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 5: verify op=sum arm=baseline max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=1.90734863e-06 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 5: verify op=sum arm=variant max_abs_vs_ref=1.43051147e-06 max_abs_vs_other=1.90734863e-06 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 5: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 5: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 5: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 5: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 6: verify op=sum arm=baseline max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=1.90734863e-06 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 6: verify op=sum arm=variant max_abs_vs_ref=1.43051147e-06 max_abs_vs_other=1.90734863e-06 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 6: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 6: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 6: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 6: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
```

## What this is, and what it is not

This is a REAL hardware measurement: the emitter's own bytes for the two arms ran on the Apple M1 Max GPU, interleaved, with verified read-back. ADR-0360 question (1)'s 2026-10-23 decision admits this native-Metal channel as contract-satisfying FOR THE MSL ARM: wire 42 executes SPIR-V through Vulkan and can never run MSL, so a wire-42-only contract could never measure this arm at all (the GLSL arm is a different story and keeps its LABELED BOOTSTRAP status). No `:measured?` flag moves in THIS run: the honesty-lock flip set is code (accelerator_variants' :measured-cell W set) and extends in its own slice, and no workgroup row (ADR-0355/0358) is touched.

## Regime-matched comparison (claim protocol rule 3)

Published by the measurement driver's --compare-historical auto-wiring (scripts/gpu-subgroup-reduce-metal-measure.py; rule-3 machinery: scripts/gpu_regime_classify.py): **docs/evidence/gpu-simdgroup-reduce-m1max-wsweep-20261023/w32/summary.md** (historical) against **docs/evidence/gpu-simdgroup-reduce-m1max-resweep-20261024/w32/summary.md**. Rule 3: a magnitude comparison across sessions or cells is drawn within matched regime strata; when the regime mixes differ the claim names the split ("magnitude splits by clock regime") and attributes the deviation to session mixing -- never "failed to reproduce". The reproduction vocabulary is exactly three phrases. Strata match across cells under rule 1's own single-linkage test at GAP-1.15 (the harness reads no clock: matched = gpu-ns-compatible, not verified clock identity). The magnitude phrase's delta is the observed deviation of the published paired medians.

| operator | sign phrase | magnitude phrase | median draw (historical / new) |
|---|---|---|---|
| max | reproduces in sign strictly (all 6 per-run ratios hold the historical sign: faster) | magnitude splits by clock regime | pure (level 2, runs 3, 6) / mixed (level 3: runs 5; level 4: runs 2) |
| min | reproduces in sign strictly (all 6 per-run ratios hold the historical sign: faster) | magnitude splits by clock regime | pure (level 2, runs 4, 6) / mixed (level 3: runs 5; level 4: runs 1) |
| sum | reproduces in sign strictly (all 6 per-run ratios hold the historical sign: faster) | magnitude reproduces within 0.021 | pure (level 2, runs 2, 3) / pure (level 1, runs 3, 6) |

Cell: sign -- reproduces in sign strictly (every operator); magnitude -- magnitude splits by clock regime (mixed: max, min).

Within-stratum comparison (the regime-matched datum; per matched stratum pair, the per-run ratio medians of the member runs):

| operator | strata (hist / new) | runs (hist / new) | median ratio (hist / new) | delta |
|---|---|---|---|---|
| max | 2 / 4 | 2, 3, 4, 5, 6 / 1, 2, 4 | 0.658 / 0.642 | 0.016 |
| max | unmatched levels | hist: 1; new: 1, 2, 3 | - | - |
| min | 1 / 2 | 1 / 3 | 0.820 / 0.919 | 0.099 |
| min | 1 / 3 | 1 / 5 | 0.820 / 0.826 | 0.006 |
| min | 2 / 4 | 2, 3, 4, 5, 6 / 1, 2, 4 | 0.639 / 0.629 | 0.010 |
| min | unmatched levels | hist: -; new: 1 | - | - |
| sum | 2 / 1 | 2, 3, 4, 5, 6 / 1, 2, 3, 4, 5, 6 | 0.650 / 0.636 | 0.014 |
| sum | unmatched levels | hist: 1; new: - | - | - |
