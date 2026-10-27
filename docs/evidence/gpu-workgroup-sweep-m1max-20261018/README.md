# gpu-workgroup-sweep-m1max-20261018 — workgroup-size sweep, Apple M1 Max

Verbatim stdout of `kbb --backend sci scripts/test-gpu-workgroup-sweep.cljk`
(three consecutive runs, each a fresh process), 2026-10-18 JST, on the amu-gpu
bot host. `EXIT=0` lines are the script's own process exit.

## Provenance

- Command: `kbb --backend sci scripts/test-gpu-workgroup-sweep.cljk`
- Code: branch `bot/amu-gpu-20261018-2102`, base `origin/main` =
  `bea7b9b24a44ebd3d5108e8e356a39c6bed5912d`, plus
  `scripts/test-gpu-workgroup-sweep.cljk` and this directory only
  (`git diff origin/main --stat` shows exactly these).
- Host: Apple M1 Max, macOS 26.4, aarch64-macos. GPU stack: MoltenVK
  (Vulkan device apiVersion 1.3.357), reported by the wire-42 INFO probe as
  `Apple M1 Max|1.3.357|1024|1` (device name | apiVersion |
  maxComputeWorkGroupSize[0] | unified memory).
- Workload (fixed by the script): one GLSL compute kernel per local size
  W ∈ {32, 64, 128, 256, 512, 1024}, 2^25 u32 elements per size (2D dispatch
  32768 × 1024/W), 2 rounds of xorshift mixing per element. Timings are the
  loader's submit->fence host clock (REPLAY nanoseconds,
  `tools/kexe_gpu_vulkan.c`); the warm-up SUBMIT is discarded and 8 REPLAY
  samples are kept per size. Medians are of those 8 samples.
- Verification (in every run, by the script itself): read-back words 0..3 of
  each size are checked against the same mixing computed on the host
  (`expected-hex`); `verify=ok` means that check passed. A run that 'measured'
  a kernel that never wrote exits 1, not 0. All three runs exited 0.

## What this evidence is

Per-size wall time of THIS kernel on THIS device. It is not a universal
optimum, and it is not dispatch-row evidence on its own.

## What it is NOT: repeatability at per-size resolution

The three runs disagree materially: medians drift up to ~2x between runs
(e.g. W=64: 1225000 / 1211000 / 596500 ns) and the FASTEST row flips
(512, 512, 1024). W=512/1024 are at or near the fastest in every run and
W=32 is the slowest or most erratic in every run, but the ordering among
64/128/256/512/1024 is not stable.

Therefore NO dispatch row is replaced by this evidence and the apple
workgroup row in `kotoba.compiler.accelerator-targets` stays provisional
(`:measured? false`). Before any row flips, the protocol needs interleaved
repeats (sizes interleaved within one run instead of 8 consecutive replays
per size) so a run-to-run baseline shift cannot masquerade as a size effect.
That is the next slice, not a conclusion of this one.

## Suite state at this commit

`kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)" run-tests.cljk`
→ 304 tests / 4939 assertions, 16 failures + 15 errors (process exit 1 for
the suite's summary path). The 31 red entries are the same base-red set PR
#1324 named at its merge base: policy-grant-count-test (15),
row-tuple-element-argument-test (9), ios-aot-test (3), typed-wasm-min-max-test
(1), rebound-row-argument-test (1), native-allocation-budget-test (1),
namespace-reachability-test (1). This diff touches only
`scripts/test-gpu-workgroup-sweep.cljk`, which the suite does not load.

CORRECTION NOTE (2026-10-24, later tick): true when written
(2026-10-18, before ADR-0358); the state moved the next day -- ADR-0358
(2026-10-19) measured four of the six rows (:nvidia, :apple, :intel,
:amd, each scoped to its one :measured-device name fragment), and only
:arm/:unknown stay :measured? false. Census:
docs/evidence/gpu/workgroup-prose-rootcause-20261024.txt.
