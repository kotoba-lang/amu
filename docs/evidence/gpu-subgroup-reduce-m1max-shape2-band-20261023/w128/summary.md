# JUN-58: :baseline vs :subgroup-reduce on Apple M1 Max at W = 128 -- the MSL arms on the native Metal route

- device: Apple M1 Max
- reported subgroup size ([[threads_per_simdgroup]]): 32
- n = 1048576 elements, workgroup W = 128 (a W-sweep cell, NOT the ADR-0358 row), 6 fresh-process runs
- shape: SHAPE 2: n = 2^20, a clean multiple of every W in [32, 1024] -- no padded-lane tail; the only variable changed from the historical cells (same LCG input prefix, byte-identical emitted arms)
- emitted at W = 128 by the emitters' own bytes (shaders/; the subgroup arm's threadgroup partials array is sized from this W)
- protocol: 20 interleaved pairs per operator per run, alternating AB/BA order, 2 warmup submits per arm discarded (ADR-0358's sweep protocol)
- operator dispatch order: sum,max,min (the default fixed order every earlier cell used)
- timer: Metal GPU timestamps (command buffer GPUStartTime->GPUEndTime) around one reduce dispatch; host submit->completion ns recorded as secondary

| operator | arm | samples | median gpu ns | per-run medians | median host ns |
|---|---|---|---|---|---|
| sum | baseline | 120 | 100208 | 100083, 100125, 100292, 100208, 100354, 100104 | 301729 |
| sum | variant | 120 | 124125 | 124000, 123979, 124125, 124146, 124250, 124167 | 332312 |
| max | baseline | 120 | 99958 | 100104, 81104, 52458, 100271, 41521, 100021 | 283666 |
| max | variant | 120 | 123625 | 123750, 99666, 93834, 123729, 50812, 123750 | 312333 |
| min | baseline | 120 | 79834 | 100104, 61750, 41458, 100125, 32125, 100062 | 278208 |
| min | variant | 120 | 87938 | 123666, 75604, 50792, 123708, 39000, 123896 | 291938 |

Paired within-run comparison (the statistic of ADR-0358: per fresh process, median over its pairs of variant/baseline gpu-ns ratio, then the median of those):

| operator | per-run ratios | median ratio |
|---|---|---|
| sum | 1.239, 1.238, 1.238, 1.239, 1.238, 1.240 | 1.239 |
| max | 1.236, 1.229, 1.789, 1.234, 1.224, 1.237 | 1.235 |
| min | 1.235, 1.224, 1.225, 1.236, 1.214, 1.238 | 1.230 |

Verified read-back (every fresh process):

```
run 1: verify op=sum arm=baseline max_abs_vs_ref=9.23871994e-06 max_abs_vs_other=1.52587891e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 1: verify op=sum arm=variant max_abs_vs_ref=9.77516174e-06 max_abs_vs_other=1.52587891e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 1: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 1: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 1: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 1: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 2: verify op=sum arm=baseline max_abs_vs_ref=9.23871994e-06 max_abs_vs_other=1.52587891e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 2: verify op=sum arm=variant max_abs_vs_ref=9.77516174e-06 max_abs_vs_other=1.52587891e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 2: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 2: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 2: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 2: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 3: verify op=sum arm=baseline max_abs_vs_ref=9.23871994e-06 max_abs_vs_other=1.52587891e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 3: verify op=sum arm=variant max_abs_vs_ref=9.77516174e-06 max_abs_vs_other=1.52587891e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 3: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 3: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 3: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 3: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 4: verify op=sum arm=baseline max_abs_vs_ref=9.23871994e-06 max_abs_vs_other=1.52587891e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 4: verify op=sum arm=variant max_abs_vs_ref=9.77516174e-06 max_abs_vs_other=1.52587891e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 4: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 4: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 4: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 4: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 5: verify op=sum arm=baseline max_abs_vs_ref=9.23871994e-06 max_abs_vs_other=1.52587891e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 5: verify op=sum arm=variant max_abs_vs_ref=9.77516174e-06 max_abs_vs_other=1.52587891e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 5: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 5: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 5: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 5: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 6: verify op=sum arm=baseline max_abs_vs_ref=9.23871994e-06 max_abs_vs_other=1.52587891e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 6: verify op=sum arm=variant max_abs_vs_ref=9.77516174e-06 max_abs_vs_other=1.52587891e-05 bit_exact_vs_ref=0 bit_exact_vs_other=0 ok=1
run 6: verify op=max arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 6: verify op=max arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 6: verify op=min arm=baseline max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
run 6: verify op=min arm=variant max_abs_vs_ref=0 max_abs_vs_other=0 bit_exact_vs_ref=1 bit_exact_vs_other=1 ok=1
```

## What this is, and what it is not

This is a REAL hardware measurement: the emitter's own bytes for the two arms ran on the Apple M1 Max GPU, interleaved, with verified read-back. ADR-0360 question (1)'s 2026-10-23 decision admits this native-Metal channel as contract-satisfying FOR THE MSL ARM: wire 42 executes SPIR-V through Vulkan and can never run MSL, so a wire-42-only contract could never measure this arm at all (the GLSL arm is a different story and keeps its LABELED BOOTSTRAP status). No `:measured?` flag moves in THIS run: the honesty-lock flip set is code (accelerator_variants' :measured-cell W set) and extends in its own slice, and no workgroup row (ADR-0355/0358) is touched.
