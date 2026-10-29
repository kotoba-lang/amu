# JUN-58: :baseline vs :simdgroup-reduce on Apple M1 Max at W = 128 -- the MSL arms on the native Metal route

- device: Apple M1 Max
- reported subgroup size ([[threads_per_simdgroup]]): 32
- n = 1000003 elements, workgroup W = 128 (a W-sweep cell, NOT the ADR-0358 row), 6 fresh-process runs
- shape: the historical shape (not a multiple of W: the padded-lane tail is exercised)
- emitted at W = 128 by the emitters' own bytes (shaders/; the variant arm's threadgroup partials array is sized from this W)
- protocol: 20 interleaved pairs per operator per run, alternating AB/BA order, 2 warmup submits per arm discarded (ADR-0358's sweep protocol)
- operator dispatch order: sum,max,min (the default fixed order every earlier cell used)
- timer: Metal GPU timestamps (command buffer GPUStartTime->GPUEndTime) around one reduce dispatch; host submit->completion ns recorded as secondary

| operator | arm | samples | median gpu ns | per-run medians | median host ns |
|---|---|---|---|---|---|
| sum | baseline | 120 | 95500 | 95396, 95500, 95562, 95500, 95417, 95500 | 308000 |
| sum | variant | 120 | 74042 | 73896, 73979, 73896, 74250, 74125, 74042 | 285312 |
| max | baseline | 120 | 85938 | 95500, 95000, 95271, 30521, 30479, 30604 | 279104 |
| max | variant | 120 | 74396 | 74979, 74750, 74875, 24334, 24125, 24250 | 251312 |
| min | baseline | 120 | 32875 | 95500, 58938, 39500, 30500, 30542, 30562 | 241334 |
| min | variant | 120 | 25812 | 74875, 46229, 31125, 24229, 24250, 24146 | 221708 |

Paired within-run comparison (the statistic of ADR-0358: per fresh process, median over its pairs of variant/baseline gpu-ns ratio, then the median of those):

| operator | per-run ratios | median ratio |
|---|---|---|
| sum | 0.775, 0.775, 0.773, 0.777, 0.777, 0.775 | 0.775 |
| max | 0.785, 0.787, 0.786, 0.797, 0.792, 0.792 | 0.789 |
| min | 0.784, 0.784, 0.788, 0.794, 0.794, 0.790 | 0.789 |

## Regime classification (claim protocol rule 1)

Published by scripts/gpu_regime_classify.py (GAP-1.15). The harness reads no GPU clock: a regime here is a cluster of the observed baseline per-run median gpu-ns levels, named by its gpu-ns range, per operator. Cross-operator level identity is tested mechanically and published in its own section below when the record has at least two operators. Rule 2's sign classification is published in its own section below when the record's per-run ratios are provided.

Clustering rule GAP-1.15: per operator, the per-run baseline medians sorted ascending, single-linkage -- the next median joins the current level at <= 1.15x the previous, else it starts a new level. 1.15 is the geometric midpoint of the committed records' decided separation window [1.075, 1.234] (within-level drift vs between-level step; see docs/evidence/gpu/regime-classification-20261023.txt).

| operator | level | gpu-ns range | runs (baseline per-run median) |
|---|---|---|---|
| max | 1 (fastest observed) | 30479..30604 | 4 (30521), 5 (30479), 6 (30604) |
| max | 2 (slowest observed) | 95000..95500 | 1 (95500), 2 (95000), 3 (95271) |
| min | 1 (fastest observed) | 30500..30562 | 4 (30500), 5 (30542), 6 (30562) |
| min | 2 | 39500 | 3 (39500) |
| min | 3 | 58938 | 2 (58938) |
| min | 4 (slowest observed) | 95500 | 1 (95500) |
| sum | 1 (the only observed level) | 95396..95562 | 1 (95396), 2 (95500), 3 (95562), 4 (95500), 5 (95417), 6 (95500) |

## Cross-operator level identity (the rule-1 partition across operators)

Published by scripts/gpu_regime_classify.py: rule 1 classifies per operator; this section tests mechanically whether those classifications describe ONE regime structure. The test is partition agreement -- for every run pair, every operator must agree on whether the two runs sit in the same rule-1 level (GAP-1.15, applied per operator). The harness reads no GPU clock and asserts no clock identity: identity here is agreement of the run partitions, nothing more.

Verdict: **identity refuted** -- 12 of 15 run pairs diverge across max, min, sum (named below). Per-operator level names stay operator-scoped: one operator's fastest level is not another's.

Partition relations (the disagreement's shape where the partitions disagree): min's partition refines max's (max pools what min splits); max's partition refines sum's (sum pools what max splits); min's partition refines sum's (sum pools what min splits).

Divergent run pairs (12 of 15):

| run pair | max | min | sum |
|---|---|---|---|
| 1 vs 2 | same-level | split-level | same-level |
| 1 vs 3 | same-level | split-level | same-level |
| 1 vs 4 | split-level | split-level | same-level |
| 1 vs 5 | split-level | split-level | same-level |
| 1 vs 6 | split-level | split-level | same-level |
| 2 vs 3 | same-level | split-level | same-level |
| 2 vs 4 | split-level | split-level | same-level |
| 2 vs 5 | split-level | split-level | same-level |
| 2 vs 6 | split-level | split-level | same-level |
| 3 vs 4 | split-level | split-level | same-level |
| 3 vs 5 | split-level | split-level | same-level |
| 3 vs 6 | split-level | split-level | same-level |

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
run 1: verify op=sum arm=baseline max_abs_vs_ref=9.23871994e-06 max_abs_vs_other=1.52587891e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 1: verify op=sum arm=variant max_abs_vs_ref=6.02006912e-06 max_abs_vs_other=1.52587891e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 1: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 1: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 1: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 1: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 2: verify op=sum arm=baseline max_abs_vs_ref=9.23871994e-06 max_abs_vs_other=1.52587891e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 2: verify op=sum arm=variant max_abs_vs_ref=6.02006912e-06 max_abs_vs_other=1.52587891e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 2: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 2: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 2: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 2: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 3: verify op=sum arm=baseline max_abs_vs_ref=9.23871994e-06 max_abs_vs_other=1.52587891e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 3: verify op=sum arm=variant max_abs_vs_ref=6.02006912e-06 max_abs_vs_other=1.52587891e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 3: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 3: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 3: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 3: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 4: verify op=sum arm=baseline max_abs_vs_ref=9.23871994e-06 max_abs_vs_other=1.52587891e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 4: verify op=sum arm=variant max_abs_vs_ref=6.02006912e-06 max_abs_vs_other=1.52587891e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 4: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 4: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 4: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 4: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 5: verify op=sum arm=baseline max_abs_vs_ref=9.23871994e-06 max_abs_vs_other=1.52587891e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 5: verify op=sum arm=variant max_abs_vs_ref=6.02006912e-06 max_abs_vs_other=1.52587891e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 5: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 5: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 5: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 5: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 6: verify op=sum arm=baseline max_abs_vs_ref=9.23871994e-06 max_abs_vs_other=1.52587891e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 6: verify op=sum arm=variant max_abs_vs_ref=6.02006912e-06 max_abs_vs_other=1.52587891e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 6: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 6: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 6: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 6: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
```

## What this is, and what it is not

This is a REAL hardware measurement: the emitter's own bytes for the two arms ran on the Apple M1 Max GPU, interleaved, with verified read-back. ADR-0360 question (1)'s 2026-10-23 decision admits this native-Metal channel as contract-satisfying FOR THE MSL ARM: wire 42 executes SPIR-V through Vulkan and can never run MSL, so a wire-42-only contract could never measure this arm at all (the GLSL arm is a different story and keeps its LABELED BOOTSTRAP status). No `:measured?` flag moves in THIS run: the honesty-lock flip set is code (accelerator_variants' :measured-cell W set) and extends in its own slice, and no workgroup row (ADR-0355/0358) is touched.
