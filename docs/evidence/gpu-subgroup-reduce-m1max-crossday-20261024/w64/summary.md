# JUN-58: :baseline vs :subgroup-reduce on Apple M1 Max at W = 64 -- the MSL arms on the native Metal route

- device: Apple M1 Max
- reported subgroup size ([[threads_per_simdgroup]]): 32
- n = 1000003 elements, workgroup W = 64 (a W-sweep cell, NOT the ADR-0358 row), 6 fresh-process runs
- shape: the historical shape (not a multiple of W: the padded-lane tail is exercised)
- emitted at W = 64 by the emitters' own bytes (shaders/; the variant arm's threadgroup partials array is sized from this W)
- protocol: 20 interleaved pairs per operator per run, alternating AB/BA order, 2 warmup submits per arm discarded (ADR-0358's sweep protocol)
- operator dispatch order: sum,max,min (the default fixed order every earlier cell used)
- timer: Metal GPU timestamps (command buffer GPUStartTime->GPUEndTime) around one reduce dispatch; host submit->completion ns recorded as secondary

| operator | arm | samples | median gpu ns | per-run medians | median host ns |
|---|---|---|---|---|---|
| sum | baseline | 120 | 92000 | 91979, 91938, 92042, 92021, 92083, 92166 | 317458 |
| sum | variant | 120 | 112271 | 112270, 112250, 112146, 112375, 112375, 112354 | 331542 |
| max | baseline | 120 | 92021 | 91854, 92083, 92000, 91938, 92021, 92188 | 289230 |
| max | variant | 120 | 111896 | 111916, 112125, 111771, 112000, 111792, 112000 | 312188 |
| min | baseline | 120 | 92000 | 91979, 91833, 92062, 91938, 92000, 92166 | 291250 |
| min | variant | 120 | 111958 | 111958, 112146, 111750, 112188, 111916, 112083 | 312084 |

Paired within-run comparison (the statistic of ADR-0358: per fresh process, median over its pairs of variant/baseline gpu-ns ratio, then the median of those):

| operator | per-run ratios | median ratio |
|---|---|---|
| sum | 1.221, 1.221, 1.218, 1.221, 1.220, 1.219 | 1.220 |
| max | 1.218, 1.218, 1.215, 1.218, 1.215, 1.215 | 1.216 |
| min | 1.217, 1.221, 1.214, 1.220, 1.216, 1.216 | 1.217 |

## Regime classification (claim protocol rule 1)

Published by scripts/gpu_regime_classify.py (GAP-1.15). The harness reads no GPU clock: a regime here is a cluster of the observed baseline per-run median gpu-ns levels, named by its gpu-ns range, per operator. Cross-operator level identity is tested mechanically and published in its own section below when the record has at least two operators. Rule 2's sign classification is published in its own section below when the record's per-run ratios are provided.

Clustering rule GAP-1.15: per operator, the per-run baseline medians sorted ascending, single-linkage -- the next median joins the current level at <= 1.15x the previous, else it starts a new level. 1.15 is the geometric midpoint of the committed records' decided separation window [1.075, 1.234] (within-level drift vs between-level step; see docs/evidence/gpu/regime-classification-20261023.txt).

| operator | level | gpu-ns range | runs (baseline per-run median) |
|---|---|---|---|
| max | 1 (the only observed level) | 91854..92188 | 1 (91854), 2 (92083), 3 (92000), 4 (91938), 5 (92021), 6 (92188) |
| min | 1 (the only observed level) | 91833..92166 | 1 (91979), 2 (91833), 3 (92062), 4 (91938), 5 (92000), 6 (92166) |
| sum | 1 (the only observed level) | 91938..92166 | 1 (91979), 2 (91938), 3 (92042), 4 (92021), 5 (92083), 6 (92166) |

## Cross-operator level identity (the rule-1 partition across operators)

Published by scripts/gpu_regime_classify.py: rule 1 classifies per operator; this section tests mechanically whether those classifications describe ONE regime structure. The test is partition agreement -- for every run pair, every operator must agree on whether the two runs sit in the same rule-1 level (GAP-1.15, applied per operator). The harness reads no GPU clock and asserts no clock identity: identity here is agreement of the run partitions, nothing more.

Verdict: **identity holds** -- the rule-1 run partition is identical across max, min, sum (all 15 run pairs agree). Where it holds, a record's prose may name one level across these operators.

Partition relations (the disagreement's shape where the partitions disagree): max and min: equal partitions; max and sum: equal partitions; min and sum: equal partitions.

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
run 1: verify op=sum arm=baseline max_abs_vs_ref=3.4570694e-06 max_abs_vs_other=3.81469727e-06 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 1: verify op=sum arm=variant max_abs_vs_ref=4.529953e-06 max_abs_vs_other=3.81469727e-06 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 1: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 1: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 1: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 1: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 2: verify op=sum arm=baseline max_abs_vs_ref=3.4570694e-06 max_abs_vs_other=3.81469727e-06 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 2: verify op=sum arm=variant max_abs_vs_ref=4.529953e-06 max_abs_vs_other=3.81469727e-06 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 2: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 2: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 2: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 2: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 3: verify op=sum arm=baseline max_abs_vs_ref=3.4570694e-06 max_abs_vs_other=3.81469727e-06 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 3: verify op=sum arm=variant max_abs_vs_ref=4.529953e-06 max_abs_vs_other=3.81469727e-06 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 3: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 3: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 3: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 3: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 4: verify op=sum arm=baseline max_abs_vs_ref=3.4570694e-06 max_abs_vs_other=3.81469727e-06 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 4: verify op=sum arm=variant max_abs_vs_ref=4.529953e-06 max_abs_vs_other=3.81469727e-06 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 4: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 4: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 4: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 4: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 5: verify op=sum arm=baseline max_abs_vs_ref=3.4570694e-06 max_abs_vs_other=3.81469727e-06 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 5: verify op=sum arm=variant max_abs_vs_ref=4.529953e-06 max_abs_vs_other=3.81469727e-06 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 5: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 5: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 5: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 5: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 6: verify op=sum arm=baseline max_abs_vs_ref=3.4570694e-06 max_abs_vs_other=3.81469727e-06 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 6: verify op=sum arm=variant max_abs_vs_ref=4.529953e-06 max_abs_vs_other=3.81469727e-06 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 6: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 6: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 6: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 6: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
```

## What this is, and what it is not

This is a REAL hardware measurement: the emitter's own bytes for the two arms ran on the Apple M1 Max GPU, interleaved, with verified read-back. ADR-0360 question (1)'s 2026-10-23 decision admits this native-Metal channel as contract-satisfying FOR THE MSL ARM: wire 42 executes SPIR-V through Vulkan and can never run MSL, so a wire-42-only contract could never measure this arm at all (the GLSL arm is a different story and keeps its LABELED BOOTSTRAP status). No `:measured?` flag moves in THIS run: the honesty-lock flip set is code (accelerator_variants' :measured-cell W set) and extends in its own slice, and no workgroup row (ADR-0355/0358) is touched.

## Regime-matched comparison (claim protocol rule 3)

Published by the measurement driver's --compare-historical auto-wiring (scripts/gpu-subgroup-reduce-metal-measure.py; rule-3 machinery: scripts/gpu_regime_classify.py): **docs/evidence/gpu-subgroup-reduce-m1max-wsweep-low-20261023/w64/summary.md** (historical) against **docs/evidence/gpu-subgroup-reduce-m1max-crossday-20261024/w64/summary.md**. Rule 3: a magnitude comparison across sessions or cells is drawn within matched regime strata; when the regime mixes differ the claim names the split ("magnitude splits by clock regime") and attributes the deviation to session mixing -- never "failed to reproduce". The reproduction vocabulary is exactly three phrases. Strata match across cells under rule 1's own single-linkage test at GAP-1.15 (the harness reads no clock: matched = gpu-ns-compatible, not verified clock identity). The magnitude phrase's delta is the observed deviation of the published paired medians.

| operator | sign phrase | magnitude phrase | median draw (historical / new) |
|---|---|---|---|
| max | reproduces in sign strictly (all 6 per-run ratios hold the historical sign: slower) | magnitude reproduces within 0.000 | pure (level 3, runs 1, 5) / pure (level 1, runs 1, 2, 3, 4, 5, 6) |
| min | reproduces in sign strictly (all 6 per-run ratios hold the historical sign: slower) | magnitude splits by clock regime | pure (level 1, runs 3, 4, 5, 6) / pure (level 1, runs 1, 5, 6) |
| sum | reproduces in sign strictly (all 6 per-run ratios hold the historical sign: slower) | magnitude reproduces within 0.001 | pure (level 1, runs 3, 4, 5) / pure (level 1, runs 1, 2, 4, 5) |

Cell: sign -- reproduces in sign strictly (every operator); magnitude -- magnitude splits by clock regime (mixed: min).

Within-stratum comparison (the regime-matched datum; per matched stratum pair, the per-run ratio medians of the member runs):

| operator | strata (hist / new) | runs (hist / new) | median ratio (hist / new) | delta |
|---|---|---|---|---|
| max | 3 / 1 | 1, 5, 6 / 1, 2, 3, 4, 5, 6 | 1.216 / 1.216 | 0.000 |
| max | unmatched levels | hist: 1, 2; new: - | - | - |
| min | 3 / 1 | 1 / 1, 2, 3, 4, 5, 6 | 1.217 / 1.216 | 0.001 |
| min | unmatched levels | hist: 1, 2; new: - | - | - |
| sum | 1 / 1 | 1, 2, 3, 4, 5, 6 / 1, 2, 3, 4, 5, 6 | 1.220 / 1.220 | 0.000 |
