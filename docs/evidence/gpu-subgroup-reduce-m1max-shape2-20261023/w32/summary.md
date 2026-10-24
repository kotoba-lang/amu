# JUN-58: :baseline vs :subgroup-reduce on Apple M1 Max at W = 32 -- the MSL arms on the native Metal route

- device: Apple M1 Max
- reported subgroup size ([[threads_per_simdgroup]]): 32
- n = 1048576 elements, workgroup W = 32 (a W-sweep cell, NOT the ADR-0358 row), 6 fresh-process runs
- shape: SHAPE 2: n = 2^20, a clean multiple of every W in [32, 1024] -- no padded-lane tail; the only variable changed from the historical cells (same LCG input prefix, byte-identical emitted arms)
- emitted at W = 32 by the emitters' own bytes (shaders/; the subgroup arm's threadgroup partials array is sized from this W)
- protocol: 20 interleaved pairs per operator per run, alternating AB/BA order, 2 warmup submits per arm discarded (ADR-0358's sweep protocol)
- timer: Metal GPU timestamps (command buffer GPUStartTime->GPUEndTime) around one reduce dispatch; host submit->completion ns recorded as secondary

| operator | arm | samples | median gpu ns | per-run medians | median host ns |
|---|---|---|---|---|---|
| sum | baseline | 120 | 113750 | 113666, 113667, 113750, 114104, 113312, 113792 | 325792 |
| sum | variant | 120 | 104438 | 104562, 104271, 104396, 104896, 104458, 104375 | 318188 |
| max | baseline | 120 | 113250 | 114084, 113875, 48042, 37812, 112916, 113834 | 302500 |
| max | variant | 120 | 104250 | 104458, 104500, 44562, 38792, 104396, 104416 | 291250 |
| min | baseline | 120 | 69688 | 113812, 113312, 47958, 37521, 37583, 114000 | 273896 |
| min | variant | 120 | 65104 | 104375, 104062, 43625, 38312, 38562, 104500 | 260146 |

Paired within-run comparison (the statistic of ADR-0358: per fresh process, median over its pairs of variant/baseline gpu-ns ratio, then the median of those):

| operator | per-run ratios | median ratio |
|---|---|---|
| sum | 0.920, 0.917, 0.918, 0.919, 0.922, 0.917 | 0.919 |
| max | 0.916, 0.918, 0.928, 1.026, 0.925, 0.917 | 0.921 |
| min | 0.917, 0.918, 0.910, 1.021, 1.026, 0.917 | 0.918 |

Verified read-back (every fresh process):

```
run 1: verify op=sum arm=baseline max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=0 bit_exact_vs_ref=0 bit_exact_vs_other=1 ok=1
run 1: verify op=sum arm=variant max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=0 bit_exact_vs_ref=0 bit_exact_vs_other=1 ok=1
run 1: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 1: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 1: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 1: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 2: verify op=sum arm=baseline max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=0 bit_exact_vs_ref=0 bit_exact_vs_other=1 ok=1
run 2: verify op=sum arm=variant max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=0 bit_exact_vs_ref=0 bit_exact_vs_other=1 ok=1
run 2: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 2: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 2: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 2: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 3: verify op=sum arm=baseline max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=0 bit_exact_vs_ref=0 bit_exact_vs_other=1 ok=1
run 3: verify op=sum arm=variant max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=0 bit_exact_vs_ref=0 bit_exact_vs_other=1 ok=1
run 3: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 3: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 3: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 3: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 4: verify op=sum arm=baseline max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=0 bit_exact_vs_ref=0 bit_exact_vs_other=1 ok=1
run 4: verify op=sum arm=variant max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=0 bit_exact_vs_ref=0 bit_exact_vs_other=1 ok=1
run 4: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 4: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 4: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 4: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 5: verify op=sum arm=baseline max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=0 bit_exact_vs_ref=0 bit_exact_vs_other=1 ok=1
run 5: verify op=sum arm=variant max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=0 bit_exact_vs_ref=0 bit_exact_vs_other=1 ok=1
run 5: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 5: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 5: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 5: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 6: verify op=sum arm=baseline max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=0 bit_exact_vs_ref=0 bit_exact_vs_other=1 ok=1
run 6: verify op=sum arm=variant max_abs_vs_ref=2.14576721e-06 max_abs_vs_other=0 bit_exact_vs_ref=0 bit_exact_vs_other=1 ok=1
run 6: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 6: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 6: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 6: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
```

## What this is, and what it is not

This is a REAL hardware measurement: the emitter's own bytes for the two arms ran on the Apple M1 Max GPU, interleaved, with verified read-back. ADR-0360 question (1)'s 2026-10-23 decision admits this native-Metal channel as contract-satisfying FOR THE MSL ARM: wire 42 executes SPIR-V through Vulkan and can never run MSL, so a wire-42-only contract could never measure this arm at all (the GLSL arm is a different story and keeps its LABELED BOOTSTRAP status). No `:measured?` flag moves in THIS run: the honesty-lock flip set is code (accelerator_variants' :measured-cell W set) and extends in its own slice, and no workgroup row (ADR-0355/0358) is touched.
