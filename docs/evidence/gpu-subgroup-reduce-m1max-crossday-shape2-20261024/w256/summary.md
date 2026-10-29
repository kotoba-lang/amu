# JUN-58: :baseline vs :subgroup-reduce on Apple M1 Max at W = 256 -- the MSL arms on the native Metal route

- device: Apple M1 Max
- reported subgroup size ([[threads_per_simdgroup]]): 32
- n = 1048576 elements, workgroup W = 256 (the measured Apple row, ADR-0358), 6 fresh-process runs
- shape: SHAPE 2: n = 2^20, a clean multiple of every W in [32, 1024] -- no padded-lane tail; the only variable changed from the historical cells (same LCG input prefix, byte-identical emitted arms)
- emitted at W = 256 by the emitters' own bytes (shaders/; the variant arm's threadgroup partials array is sized from this W)
- protocol: 20 interleaved pairs per operator per run, alternating AB/BA order, 2 warmup submits per arm discarded (ADR-0358's sweep protocol)
- operator dispatch order: sum,max,min (the default fixed order every earlier cell used)
- timer: Metal GPU timestamps (command buffer GPUStartTime->GPUEndTime) around one reduce dispatch; host submit->completion ns recorded as secondary

| operator | arm | samples | median gpu ns | per-run medians | median host ns |
|---|---|---|---|---|---|
| sum | baseline | 120 | 107542 | 107562, 107312, 107938, 107646, 107396, 107520 | 349958 |
| sum | variant | 120 | 131875 | 131875, 131896, 132000, 132042, 131750, 131812 | 377792 |
| max | baseline | 120 | 107125 | 107271, 107625, 107750, 86000, 44250, 34000 | 305667 |
| max | variant | 120 | 131417 | 131625, 131750, 131979, 105146, 53834, 41021 | 343625 |
| min | baseline | 120 | 106750 | 107500, 107542, 107562, 64979, 34146, 34375 | 307146 |
| min | variant | 120 | 130916 | 131834, 131604, 131750, 79688, 41188, 41896 | 326438 |

Paired within-run comparison (the statistic of ADR-0358: per fresh process, median over its pairs of variant/baseline gpu-ns ratio, then the median of those):

| operator | per-run ratios | median ratio |
|---|---|---|
| sum | 1.226, 1.229, 1.223, 1.227, 1.227, 1.226 | 1.226 |
| max | 1.227, 1.224, 1.225, 1.223, 1.217, 1.206 | 1.223 |
| min | 1.226, 1.224, 1.225, 1.226, 1.206, 1.219 | 1.224 |

## Regime classification (claim protocol rule 1)

Published by scripts/gpu_regime_classify.py (GAP-1.15). The harness reads no GPU clock: a regime here is a cluster of the observed baseline per-run median gpu-ns levels, named by its gpu-ns range, per operator. Cross-operator level identity is tested mechanically and published in its own section below when the record has at least two operators. Rule 2's sign classification is published in its own section below when the record's per-run ratios are provided.

Clustering rule GAP-1.15: per operator, the per-run baseline medians sorted ascending, single-linkage -- the next median joins the current level at <= 1.15x the previous, else it starts a new level. 1.15 is the geometric midpoint of the committed records' decided separation window [1.075, 1.234] (within-level drift vs between-level step; see docs/evidence/gpu/regime-classification-20261023.txt).

| operator | level | gpu-ns range | runs (baseline per-run median) |
|---|---|---|---|
| max | 1 (fastest observed) | 34000 | 6 (34000) |
| max | 2 | 44250 | 5 (44250) |
| max | 3 | 86000 | 4 (86000) |
| max | 4 (slowest observed) | 107271..107750 | 1 (107271), 2 (107625), 3 (107750) |
| min | 1 (fastest observed) | 34146..34375 | 5 (34146), 6 (34375) |
| min | 2 | 64979 | 4 (64979) |
| min | 3 (slowest observed) | 107500..107562 | 1 (107500), 2 (107542), 3 (107562) |
| sum | 1 (the only observed level) | 107312..107938 | 1 (107562), 2 (107312), 3 (107938), 4 (107646), 5 (107396), 6 (107520) |

## Cross-operator level identity (the rule-1 partition across operators)

Published by scripts/gpu_regime_classify.py: rule 1 classifies per operator; this section tests mechanically whether those classifications describe ONE regime structure. The test is partition agreement -- for every run pair, every operator must agree on whether the two runs sit in the same rule-1 level (GAP-1.15, applied per operator). The harness reads no GPU clock and asserts no clock identity: identity here is agreement of the run partitions, nothing more.

Verdict: **identity refuted** -- 12 of 15 run pairs diverge across max, min, sum (named below). Per-operator level names stay operator-scoped: one operator's fastest level is not another's.

Partition relations (the disagreement's shape where the partitions disagree): max's partition refines min's (min pools what max splits); max's partition refines sum's (sum pools what max splits); min's partition refines sum's (sum pools what min splits).

Divergent run pairs (12 of 15):

| run pair | max | min | sum |
|---|---|---|---|
| 1 vs 4 | split-level | split-level | same-level |
| 1 vs 5 | split-level | split-level | same-level |
| 1 vs 6 | split-level | split-level | same-level |
| 2 vs 4 | split-level | split-level | same-level |
| 2 vs 5 | split-level | split-level | same-level |
| 2 vs 6 | split-level | split-level | same-level |
| 3 vs 4 | split-level | split-level | same-level |
| 3 vs 5 | split-level | split-level | same-level |
| 3 vs 6 | split-level | split-level | same-level |
| 4 vs 5 | split-level | split-level | same-level |
| 4 vs 6 | split-level | split-level | same-level |
| 5 vs 6 | split-level | same-level | same-level |

What this section does NOT do (rule 4, unchanged): it changes no rule-2 verdict, no rule-3 phrase, no selection answer, no `:measured?` flag, no workgroup row. Pair-level cross-operator identity is its own test at pair granularity (the pair-level section publishes it); nothing in this run-level section licenses or refutes a pair-level naming.

## Sign classification (claim protocol rule 2)

Published by scripts/gpu_regime_classify.py from the per-run paired ratios above and the rule-1 regime clusters. Rule 2: a sign is REGIME-INVARIANT when every per-run ratio of every observed regime lies on the same side of 1.0 -- only such a sign may be a selection basis. Any other cell is published REGIME-SCOPED and cannot choose a variant. The harness reads no clock: a regime is the rule-1 cluster. The cell row carries only the admissibility roll-up, no cross-operator regime structure -- cross-operator level identity (its own section) is a publication fact about the regime structure and never re-scopes a rule-2 verdict.

| operator | verdict | side | detail |
|---|---|---|---|
| max | regime-invariant | slower | all 6 per-run ratios above 1.0 (6/6 slower); every observed regime one-sided |
| min | regime-invariant | slower | all 6 per-run ratios above 1.0 (6/6 slower); every observed regime one-sided |
| sum | regime-invariant | slower | all 6 per-run ratios above 1.0 (6/6 slower); every observed regime one-sided |

Cell (all 18 per-run ratios pooled): **regime-invariant**, slower (18/18 slower).

Verified read-back (every fresh process):

```
run 1: verify op=sum arm=baseline max_abs_vs_ref=1.57952309e-05 max_abs_vs_other=3.05175781e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 1: verify op=sum arm=variant max_abs_vs_ref=1.57952309e-05 max_abs_vs_other=3.05175781e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 1: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 1: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 1: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 1: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 2: verify op=sum arm=baseline max_abs_vs_ref=1.57952309e-05 max_abs_vs_other=3.05175781e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 2: verify op=sum arm=variant max_abs_vs_ref=1.57952309e-05 max_abs_vs_other=3.05175781e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 2: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 2: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 2: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 2: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 3: verify op=sum arm=baseline max_abs_vs_ref=1.57952309e-05 max_abs_vs_other=3.05175781e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 3: verify op=sum arm=variant max_abs_vs_ref=1.57952309e-05 max_abs_vs_other=3.05175781e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 3: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 3: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 3: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 3: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 4: verify op=sum arm=baseline max_abs_vs_ref=1.57952309e-05 max_abs_vs_other=3.05175781e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 4: verify op=sum arm=variant max_abs_vs_ref=1.57952309e-05 max_abs_vs_other=3.05175781e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 4: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 4: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 4: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 4: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 5: verify op=sum arm=baseline max_abs_vs_ref=1.57952309e-05 max_abs_vs_other=3.05175781e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 5: verify op=sum arm=variant max_abs_vs_ref=1.57952309e-05 max_abs_vs_other=3.05175781e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 5: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 5: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 5: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 5: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 6: verify op=sum arm=baseline max_abs_vs_ref=1.57952309e-05 max_abs_vs_other=3.05175781e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 6: verify op=sum arm=variant max_abs_vs_ref=1.57952309e-05 max_abs_vs_other=3.05175781e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 6: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 6: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 6: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 6: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
```

## What this is, and what it is not

This is a REAL hardware measurement: the emitter's own bytes for the two arms ran on the Apple M1 Max GPU, interleaved, with verified read-back. ADR-0360 question (1)'s 2026-10-23 decision admits this native-Metal channel as contract-satisfying FOR THE MSL ARM: wire 42 executes SPIR-V through Vulkan and can never run MSL, so a wire-42-only contract could never measure this arm at all (the GLSL arm is a different story and keeps its LABELED BOOTSTRAP status). No `:measured?` flag moves in THIS run: the honesty-lock flip set is code (accelerator_variants' :measured-cell W set) and extends in its own slice, and no workgroup row (ADR-0355/0358) is touched.

## Regime-matched comparison (claim protocol rule 3)

Published by the measurement driver's --compare-historical auto-wiring (scripts/gpu-subgroup-reduce-metal-measure.py; rule-3 machinery: scripts/gpu_regime_classify.py): **docs/evidence/gpu-subgroup-reduce-m1max-shape2-20261023/w256/summary.md** (historical) against **docs/evidence/gpu-subgroup-reduce-m1max-crossday-shape2-20261024/w256/summary.md**. Rule 3: a magnitude comparison across sessions or cells is drawn within matched regime strata; when the regime mixes differ the claim names the split ("magnitude splits by clock regime") and attributes the deviation to session mixing -- never "failed to reproduce". The reproduction vocabulary is exactly three phrases. Strata match across cells under rule 1's own single-linkage test at GAP-1.15 (the harness reads no clock: matched = gpu-ns-compatible, not verified clock identity). The magnitude phrase's delta is the observed deviation of the published paired medians.

| operator | sign phrase | magnitude phrase | median draw (historical / new) |
|---|---|---|---|
| max | reproduces in sign strictly (all 6 per-run ratios hold the historical sign: slower) | magnitude splits by clock regime | mixed (level 1: runs 6; level 2: runs 1) / mixed (level 3: runs 4; level 4: runs 2) |
| min | reproduces in sign strictly (all 6 per-run ratios hold the historical sign: slower) | magnitude splits by clock regime | mixed (level 2: runs 5; level 5: runs 2) / pure (level 3, runs 2, 3) |
| sum | reproduces in sign strictly (all 6 per-run ratios hold the historical sign: slower) | magnitude reproduces within 0.001 | pure (level 1, runs 1, 2, 4) / pure (level 1, runs 1, 4, 5, 6) |

Cell: sign -- reproduces in sign strictly (every operator); magnitude -- magnitude splits by clock regime (mixed: max, min).

Within-stratum comparison (the regime-matched datum; per matched stratum pair, the per-run ratio medians of the member runs):

| operator | strata (hist / new) | runs (hist / new) | median ratio (hist / new) | delta |
|---|---|---|---|---|
| max | 1 / 3 | 3, 4, 6 / 4 | 1.217 / 1.223 | 0.006 |
| max | 2 / 4 | 1, 2, 5 / 1, 2, 3 | 1.228 / 1.225 | 0.003 |
| max | unmatched levels | hist: -; new: 1, 2 | - | - |
| min | 1 / 1 | 6 / 5, 6 | 1.203 / 1.212 | 0.009 |
| min | 5 / 3 | 1, 2 / 1, 2, 3 | 1.224 / 1.225 | 0.001 |
| min | unmatched levels | hist: 2, 3, 4; new: 2 | - | - |
| sum | 1 / 1 | 1, 2, 3, 4, 5, 6 / 1, 2, 3, 4, 5, 6 | 1.227 / 1.227 | 0.000 |
