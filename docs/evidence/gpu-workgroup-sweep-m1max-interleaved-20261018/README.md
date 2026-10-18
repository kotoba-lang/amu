# gpu-workgroup-sweep-m1max-interleaved-20261018 — interleaved protocol, Apple M1 Max

Verbatim stdout of `kbb --backend sci scripts/test-gpu-workgroup-sweep-interleaved.cljk`
(three consecutive runs, each a fresh process), 2026-10-18 JST, on the amu-gpu
bot host. `EXIT=0` lines are the script's own process exit.

## Provenance

- Command: `kbb --backend sci scripts/test-gpu-workgroup-sweep-interleaved.cljk`
- Code: branch `bot/amu-gpu-20261018-2307`, base `origin/main` =
  `bea7b9b24a44ebd3d5108e8e356a39c6bed5912d`, plus exactly
  `scripts/test-gpu-workgroup-sweep-interleaved.cljk`,
  `tools/kexe_gpu_vulkan.c` (one constant: KGPU_MAX_KEPT 4 -> 8, needed for
  6 simultaneously kept command buffers), and this directory.
- Host: Apple M1 Max, macOS 26.4, aarch64-macos. MoltenVK, Vulkan device
  apiVersion 1.3.357, INFO `Apple M1 Max|1.3.357|1024|1`.
- Workload: identical to the consecutive protocol
  (docs/evidence/gpu-workgroup-sweep-m1max-20261018/): one kernel per local
  size W in {32,64,128,256,512,1024}, 2^25 u32 elements per size, 2 rounds
  of xorshift mixing; timings are the loader's submit->fence host clock
  (REPLAY nanoseconds). Read-back words 0..3 verified against the host's
  own mixing (`verify=ok` in all runs).
- Protocol difference: instead of 8 consecutive REPLAYs of one size, each
  round REPLAYs all six sizes once (8 rounds, order 32..1024), so all six
  sample sets share every point in time of the run. Sample j belongs to
  size (j mod 6); the script's self-test pins that mapping.

## What the three runs say (measured)

- Interleaving removed the confound it was built for: within one run the
  six medians now sit within ~5-15% of each other and the per-size
  min-max ranges overlap heavily (consecutive protocol: medians drifted
  ~2x between runs and the fastest row flipped 512/512/1024).
- The run-to-run baseline shift remains (~1.0-1.23 ms for the same
  kernel), and because per-size differences within a run (0.1-5%) are
  SMALLER than that shift's residue in the medians, the fastest row still
  flips across the three interleaved runs: 256 / 128 / 64.

## What this evidence is NOT

It is not a tuning result. At this workload (memory-bound mixing) there is
NO stable workgroup-size effect on M1 Max above the measurement noise, in
either protocol. Therefore NO dispatch row is replaced and the apple
workgroup row in `kotoba.compiler.accelerator-targets` stays provisional
(`:measured? false`) -- neither confirmed nor overturned. Flipping
`:measured?` on "we measured no difference" also needs more than 3 runs of
one kernel shape.

Residual bias not removed by this protocol: within-round order is fixed
(32,64,128,256,512,1024), so a monotonic drift within one round (~3.6 ms)
would still favor one end; second-order against what interleaving fixed.

Next slices (pick one, next tick): within-run ratios with more rounds
(ratios cancel the baseline, CIs tighten); a compute-bound kernel variant
where local size can matter; or a "size-insensitive for this kernel shape"
measured row scoped to THIS kernel, never to the vendor row.

## Suite state at this commit

`kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)" run-tests.cljk`
→ 304 tests / 4939 assertions, 16 failures + 15 errors. Identical to the
base-red set PR #1324 named at its merge base (policy-grant-count-test (15),
row-tuple-element-argument-test (9), ios-aot-test (3), typed-wasm-min-max-test
(1), rebound-row-argument-test (1), native-allocation-budget-test (1),
namespace-reachability-test (1)). This diff touches no suite namespace
(script + C constant + evidence only) and introduces no new red.
