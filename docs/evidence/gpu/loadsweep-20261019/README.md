# gpu/loadsweep-20261019 -- W=64 baseline cascade vs :subgroup-reduce at 4x load (JUN-58)

Raw logs from `scripts/test-gpu-subgroup-reduce-loadsweep.cljk`, 3 verified
runs at 4,194,240 lanes/dispatch plus 1 control run at the sweep's 2^20
load, on Apple M1 Max / MoltenVK (Vulkan 1.3.357), glslang 11:16.6.0,
aarch64-macos, 2026-10-19 08:26-08:31 JST. Every run verified x[i]=i+1 and
the first four workgroup partials of BOTH reduce arms bit-exact (f32, sum
W^2*g + W(W-1)/2 + W, g = 0..3) before printing any timing line; all 4 runs
printed `RESULT verified=true`.

## Why this probe exists

PR #1348's W-sweep (constant 2^20 lanes/dispatch) reported the W=32 and
W=64 rows as explicitly NOT algorithm verdicts: at those shapes all three
arms sat on the launch floor (floor/baseline 0.82 at W=64), so the
baseline/variant difference was below the noise floor. This probe re-runs
the W=64 comparison with ~4x the work per dispatch (4194240 lanes =
64 * 65535 workgroups, the last grid count within Vulkan's guaranteed
65535 limit). The protocol is byte-for-byte the same as PR #1348's probe
(three interleaved wire-42 arms, BEGINK/REPLAY kept buffers, 32 rounds x
512-dispatch batches, 96 samples, parity-alternating arm order, bit-exact
verification first); the ONE change is that lanes per dispatch is an argv
parameter. The variant is the same pinned emit-glsl W=64 fixture
(sha256 a25a69317b5c5a956279ccc37a5089adb489104a28ed89460b8928889b096254)
at PR #1346's `:categories+id` rung. The control run at 2^20 reproduces PR
#1348's W=64 row (median 1.0129 here vs 1.0149 / 1.0401 there), which ties
the two probes' chains together.

## baseline/variant ratio (median of 32 within-round ratios; BELOW 1.0 = variant slower)

| run | lanes/dispatch | ratio med | iqr    | min    | max    | vs-1.0 (range)              | floor/baseline | ns/dispatch b / v / f        |
|-----|----------------|-----------|--------|--------|--------|-----------------------------|----------------|------------------------------|
| 1   | 4194240        | 0.9390    | 0.0220 | 0.6689 | 1.6315 | crosses (host spikes)       | 0.9102         | 99282 / 105320 / 90253       |
| 2   | 4194240        | 0.9387    | 0.0091 | 0.9260 | 0.9551 | below (all 32 rounds)       | 0.9051         | 98077 / 104656 / 89022       |
| 3   | 4194240        | 0.9346    | 0.0124 | 0.8880 | 1.0971 | crosses (1 round of 32)     | 0.9102         | 98138 / 104883 / 89629       |
| 4 (control) | 1048576 | 1.0129    | 0.0317 | 0.9245 | 1.0726 | indistinguishable           | 0.8505         | 42249 / 41808 / 35539        |

Host was contended throughout (load averages 15-21, `uptime` before each
run); runs 1 and 3 show single-round spikes in the min/max range. The
three 4x-load medians agree to within 0.5%; run 2 (quiet, arm IQRs ~1% of
median) has every one of its 32 rounds below 1.0.

## Finding (PROVISIONAL: bootstrap compiler, contended host)

Repository policy permits publishing compiler codegen performance verdicts
only from a selfhost-built compiler on a quiet host. These runs used the
Node bootstrap compiler and ran with the host contended (load averages
15-21), and the harness's replay order was the forward/reverse scheme
(012,210), whose adjacent positions are unbalanced (two of the three arms
get back-to-back replays; the variant's predecessor is always another arm)
-- a predecessor cache/power/frequency confound that biases the
baseline/variant ratio beyond drift. The recorded logs carry
`order=alternating(012,210)` and are retained as LABELED BOOTSTRAP runs;
the harness now emits the balanced order (012021), and a selfhost-built
compiler run on a quiet host is required before any verdict is published.
What follows is that labeled-bootstrap finding, not a published verdict.

At W=64 with 4x the load the difference RESOLVES: the :subgroup-reduce
variant is slower than the shared-memory cascade by ~6.5-7.0% per dispatch
(1/0.9387 = 1.065; per-run 1.065-1.070), where at 2^20 lanes the same
comparison was indistinguishable from 1.0 in both PR #1348 runs and in
this probe's control run. At 2^20 the median wobbled to either side of
1.0 (1.015 / 1.040 / 1.013) with no resolvable sign, so nothing "flipped" --
the only resolvable facts are "no difference above noise at 2^20" and
"variant ~6.5% slower at 4x". Together with PR #1348's W=128 (0.84-0.86)
and W=256 (0.76-0.77) rows, every resolvable point on this host is on the
same side: the subgroup-shuffle variant is never faster than the cascade
on Apple M1 Max.

## Two things this run measured that the script's motivation got wrong

The header's motivating model said the fixed per-dispatch floor would stay
put under load and the ratio would amplify off it. Measured instead:

- The floor is NOT fixed per dispatch. Floor ns/dispatch grew from
  30901-37877 at 16,384 workgroups (2^20 runs: PR #1348's two plus this
  probe's control) to 89022-90253 at 65,535 workgroups -- 2.5-2.9x time
  for 4x workgroups, sub-linear in groups but nowhere near constant.
  Floor/baseline SHARE went UP (0.82-0.85 -> 0.90-0.91), not down, at the
  higher load.
- The resolution still happened, but through the arms' absolute gap
  growing: baseline-variant per dispatch is ~0.4-2.7 us at 2^20 (within
  noise) and 6.3-6.7 us at 4x (three consistent medians). Why the gap
  grows super-proportionally to the load is UNRESOLVED; the variant's
  shared-memory/shuffle traffic interacting with the larger x[] stream
  (16.8 MB per dispatch at 4x) is a hypothesis, not a measurement. A load
  sweep at W=64 between the two points would test it.

## What this is not

One device (Apple M1 Max), one W. No :measured? flag is flipped anywhere
in kotoba.compiler.accelerator-targets. The cross-W penalty comparison
carries a caveat: W=128/256 rows were measured at 2^20 lanes (floor share
0.68-0.78) and this W=64 row at 4x (floor share 0.91); the percentage
penalties across W are not normalized to the same floor share. W=32
remains floor-bound and unverdicted (its 4x grid would need 131072
workgroups, over the 65535 limit in 1D). The Intel (JUN-59) and Mali
(JUN-60) baseline-vs-variant comparisons need hardware this bot does not
have.
