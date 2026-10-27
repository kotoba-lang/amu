# JUN-58: :baseline vs :subgroup-reduce on Apple M1 Max at W = 32 -- the MSL arms on the native Metal route

- device: Apple M1 Max
- reported subgroup size ([[threads_per_simdgroup]]): 32
- n = 1000003 elements, workgroup W = 32 (a W-sweep cell, NOT the ADR-0358 row), 6 fresh-process runs
- shape: the historical shape (not a multiple of W: the padded-lane tail is exercised)
- emitted at W = 32 by the emitters' own bytes (shaders/; the subgroup arm's threadgroup partials array is sized from this W)
- protocol: 20 interleaved pairs per operator per run, alternating AB/BA order, 2 warmup submits per arm discarded (ADR-0358's sweep protocol)
- operator dispatch order: max,min,sum (OP-ORDER VARIANT, named: under the fixed sum,max,min order the fresh-process clock ramp left :sum with no fast-regime sample on any cell -- the shape-2 record's structural blocker on the W = 32 regime question; this order puts :sum's block after the ramp on purpose)
- timer: Metal GPU timestamps (command buffer GPUStartTime->GPUEndTime) around one reduce dispatch; host submit->completion ns recorded as secondary

| operator | arm | samples | median gpu ns | per-run medians | median host ns |
|---|---|---|---|---|---|
| sum | baseline | 120 | 88458 | 109312, 109229, 109229, 56104, 45833, 36021 | 282666 |
| sum | variant | 120 | 70500 | 100625, 100292, 100125, 51312, 42375, 36584 | 269167 |
| max | baseline | 120 | 109354 | 108854, 109604, 109417, 109500, 108916, 109250 | 335270 |
| max | variant | 120 | 100229 | 100354, 100416, 100084, 100271, 100292, 99625 | 320854 |
| min | baseline | 120 | 108938 | 109375, 109229, 109104, 107708, 109125, 36000 | 290688 |
| min | variant | 120 | 100208 | 100458, 100500, 100271, 99750, 100208, 36625 | 284375 |

Paired within-run comparison (the statistic of ADR-0358: per fresh process, median over its pairs of variant/baseline gpu-ns ratio, then the median of those):

| operator | per-run ratios | median ratio |
|---|---|---|
| sum | 0.921, 0.918, 0.917, 0.915, 0.925, 1.016 | 0.919 |
| max | 0.922, 0.916, 0.915, 0.916, 0.921, 0.912 | 0.916 |
| min | 0.918, 0.920, 0.919, 0.926, 0.918, 1.017 | 0.920 |

Verified read-back (every fresh process):

```
run 1: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 1: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 1: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 1: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 1: verify op=sum arm=baseline max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=0 bit_exact_vs_ref=0 bit_exact_vs_other=1 ok=1
run 1: verify op=sum arm=variant max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=0 bit_exact_vs_ref=0 bit_exact_vs_other=1 ok=1
run 2: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 2: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 2: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 2: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 2: verify op=sum arm=baseline max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=0 bit_exact_vs_ref=0 bit_exact_vs_other=1 ok=1
run 2: verify op=sum arm=variant max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=0 bit_exact_vs_ref=0 bit_exact_vs_other=1 ok=1
run 3: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 3: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 3: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 3: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 3: verify op=sum arm=baseline max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=0 bit_exact_vs_ref=0 bit_exact_vs_other=1 ok=1
run 3: verify op=sum arm=variant max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=0 bit_exact_vs_ref=0 bit_exact_vs_other=1 ok=1
run 4: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 4: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 4: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 4: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 4: verify op=sum arm=baseline max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=0 bit_exact_vs_ref=0 bit_exact_vs_other=1 ok=1
run 4: verify op=sum arm=variant max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=0 bit_exact_vs_ref=0 bit_exact_vs_other=1 ok=1
run 5: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 5: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 5: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 5: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 5: verify op=sum arm=baseline max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=0 bit_exact_vs_ref=0 bit_exact_vs_other=1 ok=1
run 5: verify op=sum arm=variant max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=0 bit_exact_vs_ref=0 bit_exact_vs_other=1 ok=1
run 6: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 6: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 6: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 6: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 6: verify op=sum arm=baseline max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=0 bit_exact_vs_ref=0 bit_exact_vs_other=1 ok=1
run 6: verify op=sum arm=variant max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=0 bit_exact_vs_ref=0 bit_exact_vs_other=1 ok=1
```

## What this is, and what it is not

This is a REAL hardware measurement: the emitter's own bytes for the two arms ran on the Apple M1 Max GPU, interleaved, with verified read-back. ADR-0360 question (1)'s 2026-10-23 decision admits this native-Metal channel as contract-satisfying FOR THE MSL ARM: wire 42 executes SPIR-V through Vulkan and can never run MSL, so a wire-42-only contract could never measure this arm at all (the GLSL arm is a different story and keeps its LABELED BOOTSTRAP status). No `:measured?` flag moves in THIS run: the honesty-lock flip set is code (accelerator_variants' :measured-cell W set) and extends in its own slice, and no workgroup row (ADR-0355/0358) is touched.
