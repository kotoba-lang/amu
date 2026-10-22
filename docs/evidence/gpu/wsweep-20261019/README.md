# gpu/wsweep-20261019 -- baseline cascade vs :subgroup-reduce over W (JUN-58)

Raw logs from `scripts/test-gpu-subgroup-reduce-wsweep.cljk`, 8 verified runs
(2 per workgroup size) on Apple M1 Max / MoltenVK (Vulkan 1.3.357),
glslang 11:16.6.0, aarch64-macos, 2026-10-19. Every run verified the first
four input words x[0..3] = 1.0..4.0 (the only x values the harness reads
back -- `READ hx 0 16`) and the first four workgroup partials of BOTH
reduce arms bit-exact (f32, sum W^2*g + W(W-1)/2 + W, g = 0..3) before
printing any timing line; all 8 runs printed `RESULT verified=true`.

Method (the script header is the full text): three interleaved wire-42 arms
per W -- baseline (the emit-wgsl :reduce :sum stride cascade, ported WGSL ->
GLSL structurally unchanged), variant (the exact emit-glsl bytes for the
(W, :sum) shape, sha256-pinned fixtures in test/fixtures/gpu/, with PR
#1346's :categories+id rung patches), floor (same dispatch shape,
near-empty body). 32 rounds x 3 REPLAYs with parity-alternating arm order,
512-dispatch kept buffers, 96 samples; constant work per sample at every W
(2^20 lanes per dispatch). Per-round ratio is t(baseline)/t(variant): BELOW
1.0 means the variant is SLOWER.

## baseline/variant ratio (median of 32 within-round ratios)

| W   | run 1              | run 2              | floor/baseline | read |
|-----|--------------------|--------------------|----------------|------|
| 32  | 0.9620 (iqr .031)  | 0.9700 (iqr .017)  | 1.06 / 1.04    | launch-floor-bound: floor share ~1.0, no algorithm effect resolvable |
| 64  | 1.0149 (iqr .023)  | 1.0401 (iqr .173)  | 0.82 / 0.82    | indistinguishable from 1.0 (run 2 noisy) |
| 128 | 0.8412 (iqr .036)  | 0.8595 (iqr .175)  | 0.78 / 0.77    | run 1 resolvably below 1.0 (range .80-.93); run 2 median agrees, noisy host |
| 256 | 0.7735 (iqr .020)  | 0.7567 (iqr .013)  | 0.68 / 0.69    | resolvably below 1.0 in both runs (ranges .74-.81, .73-.82) |

The W=256 medians replicate PR #1347's single-shape result (0.786 / 0.803
at 4x the load) at 2^20 lanes/dispatch: the variant's W=256 penalty is not
a load-shape artifact.

## What this is not

One device (Apple M1 Max). No :measured? flag is flipped anywhere in
kotoba.compiler.accelerator-targets. The Intel (JUN-59) and Mali (JUN-60)
baseline-vs-variant comparisons need hardware this bot does not have. The
W=32 and W=64 rows are explicitly NOT algorithm verdicts, for different
reasons: at W=32 a 2^20-lane dispatch is launch-bound on this device and
all three arms sit on the floor (floor share ~1.0), while at W=64 the
reduction arms do NOT sit on the floor (floor/baseline 0.8227 / 0.8237,
floor/variant 0.8307 / 0.8627 -- the reduction arms take ~16-22% longer
than the near-empty arm) but baseline and variant remain indistinguishable
from each other, so no algorithm effect is resolvable there either.
