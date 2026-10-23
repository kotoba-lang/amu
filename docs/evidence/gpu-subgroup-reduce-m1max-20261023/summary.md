# JUN-58: :baseline vs :subgroup-reduce on Apple M1 Max -- the MSL arm's first hardware run

- device: Apple M1 Max
- reported subgroup size ([[threads_per_simdgroup]]): 32
- n = 1000003 elements, workgroup W = 256 (the measured Apple row, ADR-0358), 6 fresh-process runs
- protocol: 20 interleaved pairs per operator per run, alternating AB/BA order, 2 warmup submits per arm discarded (ADR-0358's sweep protocol)
- timer: Metal GPU timestamps (command buffer GPUStartTime->GPUEndTime) around one reduce dispatch; host submit->completion ns recorded as secondary

| operator | arm | samples | median gpu ns | per-run medians | median host ns |
|---|---|---|---|---|---|
| sum | baseline | 120 | 103000 | 103062, 103458, 102792, 102625, 54229, 102916 | 298980 |
| sum | variant | 120 | 126084 | 125770, 126312, 125979, 125584, 66396, 125730 | 323750 |
| max | baseline | 120 | 102396 | 103667, 83584, 103062, 103396, 52521, 32792 | 298000 |
| max | variant | 120 | 125188 | 126334, 101688, 125875, 126062, 63916, 39250 | 309979 |
| min | baseline | 120 | 89666 | 103438, 102834, 103542, 83625, 42833, 32708 | 289562 |
| min | variant | 120 | 101625 | 126208, 125812, 126125, 101562, 51750, 39125 | 303604 |

Paired within-run comparison (the statistic of ADR-0358: per fresh process, median over its pairs of variant/baseline gpu-ns ratio, then the median of those):

| operator | per-run ratios | median ratio |
|---|---|---|
| sum | 1.220, 1.221, 1.226, 1.224, 1.224, 1.222 | 1.223 |
| max | 1.219, 1.217, 1.221, 1.219, 1.217, 1.197 | 1.218 |
| min | 1.220, 1.223, 1.218, 1.214, 1.208, 1.196 | 1.216 |

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

## Prior art (corrected 2026-10-23, same tick): this is NOT the first comparison

The first hardware comparison of the two reduce arms ran 2026-10-19 through
wire-42 / MoltenVK on the GLSL arm: PR #1347 (ba1fcced -- W=256 :sum, the
variant costs ~20-27% more time per dispatch) and PR #1348 (677fa1cf --
W-sweep 32..256, variant never faster, penalty grows with W). S = 32 was
measured the same day through the Vulkan side (PR #1343, eef57e63 --
gl_SubgroupSize at W=64). All three are merged ancestors of this chain.
What is NEW in this run, and only this:

1. the MSL arm's first hardware EXECUTION (it was COMPILED-only before --
   the chain's MSL evidence of the same date says so);
2. a CROSS-ROUTE REPLICATION: the MSL arm on the native Metal route
   reproduces the GLSL arm's MoltenVK finding at W=256 (paired ratio
   1.216-1.223 here vs 1.29-1.32x there -- different load shape and timer,
   so the numbers are not comparable cell-by-cell; the sign and magnitude
   class agree);
3. the :max/:min operators (the prior campaign ran :sum only), with the
   bit-exact rule-2 read-back verification;
4. the Metal-native [[threads_per_simdgroup]] = 32 reading -- a DIFFERENT
   channel from eef57e63's Vulkan-side probe; it confirms S = 32 on the
   native binding, it is not the first S = 32 fact.

This evidence's commit (009c86ef) claimed "first" twice in its message and
once in this file's title; those claims are superseded by this correction.
Named, not hidden: the chain's ADR-0356 row prose ("no Apple device has run
the variant") conflicts with ba1fcced/677fa1cf having run and timed the
GLSL arm on 2026-10-19 -- the row prose predates this correction and is out
of scope for this measurement tick; it needs its own reconciliation.
(CLOSED later 2026-10-23: ADR-0356's "row prose reconciled to the
execution record" amendment -- this file's record stands as written.)

## What this is, and what it is not

This is a REAL hardware measurement: the emitter's own bytes for the two arms ran on the Apple M1 Max GPU, interleaved, with verified read-back. It is NOT the measurement ADR-0360's contract names: that contract requires the wire-42 route, which does not exist since the C loader removal (ADR 0371 -- the provider is the replacement track and is not implemented). This run dispatches the MSL arms through the Metal API directly instead. No `:measured?` flag moves and no workgroup row is touched: the row's flip stays blocked on the contract's route clause (and on the per-tested-device scoping the flip would need). Whether a native Metal harness satisfies the measurement contract is a design decision, PROPOSED by this evidence and decided nowhere.
