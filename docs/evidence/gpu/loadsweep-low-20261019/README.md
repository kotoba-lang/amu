# gpu/loadsweep-low-20261019 -- W=64 low-load onset sweep (JUN-58)

Raw logs from `scripts/test-gpu-subgroup-reduce-loadsweep.cljk` (sha256
871bfde4a14e4168fba9808581acd7b2a704f47054cac49eee54e1f35f1da462,
byte-identical to PRs #1349/#1350), 9 verified runs in three interleaved
cycles of 1.25x / 1.5x / 1.75x the sweep's 2^20 load plus one 2^20 control
run, on Apple M1 Max / MoltenVK (Vulkan 1.3.357), glslang 11:16.6.0,
aarch64-macos, 2026-10-19 09:55-09:57 JST. Every run verified x[i]=i+1 and
the first four workgroup partials of BOTH reduce arms bit-exact (f32,
sum W^2*g + W(W-1)/2 + W, g = 0..3) before printing any timing line; all 10
runs printed `RESULT verified=true` and exited 0. `uptime` is printed inside
each log; host load averages 19.3-25.9 throughout (higher than PRs
#1349/#1350's 6.5-13.2 -- other tenants of the machine; two runs below show
visible host spikes and are called out). Run ORDER is interleaved across
loads (cycle 1a/1b/1c, 2a/2b/2c, 3a/3b/3c, then control) rather than the
blocked order of PR #1350, so slow host drift biases the three loads
symmetrically; everything else (probe bytes, fixtures, protocol) is the
PR #1350 chain's.

## Why this probe exists

PR #1350 (loadsweep-mid-20261019) left two things open: (a) the resolution
point of the W=64 row "sits between 16,384 and 32,768 workgroups", and (b)
the affine fit through its 2x/4x gap means (slope 0.128 ns/wg, intercept
-1.9 us) predicted a gap of only ~+190 ns at the 2^20 control, which the
control's noise band could not confirm or refute -- a threshold onset
somewhere below 32,768 wg was still consistent with the data. This run
fills the low end: 3 runs each at 20,480 wg (1,310,720 lanes = 1.25x),
24,576 wg (1,572,864 = 1.5x), 28,672 wg (1,835,008 = 1.75x), plus one
same-protocol 2^20 control at 16,384 wg.

## baseline/variant ratio (median of 32 within-round ratios; BELOW 1.0 = variant slower)

| run | wg     | ratio med | iqr    | min    | max    | vs-1.0 (script verdict)   | floor/base | ns/dispatch b / v / f        | gap v-b (ns) |
|-----|--------|-----------|--------|--------|--------|---------------------------|------------|------------------------------|--------------|
| 1a  | 20,480 | 0.9819    | 0.0250 | 0.9229 | 1.1078 | indistinguishable         | 0.7991     | 46936 / 47672 / 37150        | +736         |
| 2a  | 20,480 | 0.9889    | 0.0122 | 0.9565 | 1.0350 | indistinguishable         | 0.7835     | 46558 / 47066 / 36416        | +509         |
| 3a  | 20,480 | 0.9583    | 0.1528 | 0.2644 | 1.7966 | indistinguishable (SPIKE) | 0.8261     | 51199 / 52161 / 43376        | +962         |
| 1b  | 24,576 | 0.9932    | 0.0973 | 0.4432 | 2.0780 | indistinguishable (SPIKE) | 0.8116     | 56255 / 56240 / 45624        | -15          |
| 2b  | 24,576 | 0.9740    | 0.0193 | 0.9475 | 1.0539 | indistinguishable         | 0.8100     | 52469 / 53700 / 42489        | +1231        |
| 3b  | 24,576 | 0.9820    | 0.0152 | 0.9309 | 1.0616 | indistinguishable         | 0.8211     | 52425 / 53516 / 42917        | +1091        |
| 1c  | 28,672 | 0.9776    | 0.0154 | 0.9597 | 1.0144 | indistinguishable         | 0.8586     | 56652 / 57961 / 48638        | +1309        |
| 2c  | 28,672 | 0.9747    | 0.0152 | 0.9428 | 0.9876 | below (all 32 rounds)     | 0.8552     | 57415 / 58945 / 48972        | +1530        |
| 3c  | 28,672 | 0.9769    | 0.0106 | 0.9491 | 0.9911 | below (all 32 rounds)     | 0.8601     | 57799 / 59383 / 49766        | +1584        |
| 10 (control) | 16,384 | 1.0145 | 0.0172 | 0.9812 | 1.0466 | indistinguishable | 0.8291 | 39692 / 39225 / 33146 | -468 |

SPIKE = runs 3a and 1b: baseline arm round IQR 5.1 ms / 6.8 ms against
0.2-0.5 ms in the other runs, single rounds up to 107/130 ms -- host noise,
visible in all three arms of those runs. Their gap values are kept in every
mean below but the "clean" column (runs with baseline IQR < 2 ms) is given
alongside.

Chain points quoted (NOT re-measured here): 2x = 32,768 wg gap +2284 ns
(PR #1350, three runs 2203/2368/2280), 3x = 49,152 wg +4436 ns (PR #1350),
4x = 65,535 wg +6454 ns (PR #1349). Prior 2^20 controls: -788 (PR #1350),
-441 (PR #1349).

## Finding

1. **The 20,480-workgroup onset is UNRESOLVED.** The 1.25x runs' gap
   values (+736 / +509 / +962 ns per dispatch) sit above the 2^20
   controls (-468 / -788 / -441), but at 20,480 wg every run's paired
   ratio range spans 1.0 and the median effects (1.81% / 1.11% / 4.17%)
   are each smaller than their reported IQRs (2.50% / 1.22% / 15.28%);
   by this probe's own protocol such an effect is not a result. The gap
   values are also differences of separately computed arm medians rather
   than paired round differences (the harness's paired GAP statistic
   landed later, PR #1373's thread). The threshold question therefore
   stays open at 20,480 wg: neither "onset established" nor "onset at
   >= 32,768 refuted" follows from these rows. The PR #1350 statement
   "the resolution point sits between 16,384 and 32,768 workgroups"
   holds only for the STRICT within-round ratio verdict (see 2).

2. **Strict ratio verdict: the lowest load that resolves "below" is 28,672
   workgroups, and only 2 of 3 runs.** At 28,672 wg runs 2c/3c have all 32
   rounds below 1.0 (max 0.9876 / 0.9911) and run 1c crosses marginally
   (max 1.0144). At 24,576 and 20,480 no run resolves: every range crosses
   1.0. At 32,768 wg (PR #1350) all three runs resolve with all rounds
   below. So the verdict-resolution point sits in (24,576, 32,768] wg and
   the 28,672 row is the boundary evidence.

3. **The gap stays consistent with the affine-in-workgroups law of the
   mid-sweep, and the low-end data no longer need a threshold.** Gap means
   (ns/dispatch): -468 (16,384) / +736 (20,480) / +769 (24,576, clean
   +1161) / +1474 (28,672) / +2284 (32,768) / +4436 (49,152) / +6454
   (65,535). The PR #1350 affine fit (0.1273 ns/wg, -1.89 us intercept)
   predicts +720 / +1242 / +1763 at 20,480 / 24,576 / 28,672: measured
   means land +16 / -472 / -288 ns from prediction (clean-run view:
   -98 / -81 / -288). A least-squares line through all seven chain points
   gives 0.1373 ns/wg, -2.42 us, max residual 343 ns (at 20,480). The
   per-segment marginal slopes at the low end are noisy (clean: 0.27 ns/wg
   for 16,384->20,480, 0.13 for 20,480->24,576, 0.08 for
   24,576->28,672) against the chain average 0.13 ns/wg; with one control
   run today the data cannot resolve curvature at the bottom, so "affine,
   slope ~0.13 ns/wg, intercept ~-2 us" remains a description, not a
   mechanism.

4. **Mechanism still UNRESOLVED, no :measured? flag flipped anywhere.**
   This sweep varies only lanes-per-dispatch; it still does not separate
   the x[] stream size from the workgroup count (PR #1350's caveat), and
   nothing here is a hardware measurement of
   kotoba.compiler.accelerator-targets workgroup defaults -- those rows
   stay provisional (:measured? false).

## What this is not

One device (Apple M1 Max), one W (64). The host carried load averages
19.3-25.9 (PRs #1349/#1350 ran at 6.5-13.2); the cross-chain anchor is that
the same-protocol control's floor ns/dispatch reproduces the PR #1350
control to within 1 ns (33,145.5 vs 33,145) and its gap (-468) lands inside
the chain's control cluster (-788..-441). The 2x/3x/4x rows are quoted from
PRs #1349/#1350, not re-measured here. Spike runs 3a/1b are kept, not
dropped; the clean column shows they do not move the conclusions. The
Intel (JUN-59) and Mali (JUN-60) comparisons need hardware this bot does
not have.

## Provenance correction to PR #1350

PR #1350's README pins the probe script as sha256
`d6273519db58a1b5fc022c24b81e8c6493d6fe02`. That value matches no file: the
script's true sha256 on both PR #1349 and PR #1350 (committed blob and
working tree, verified here with `shasum -a 256` on both worktrees and on
`git show 47a4eacf:scripts/test-gpu-subgroup-reduce-loadsweep.cljk`) is
`871bfde4a14e4168fba9808581acd7b2a704f47054cac49eee54e1f35f1da462`.
The byte-identical claim between #1349 and #1350 remains TRUE -- only the
printed pin was wrong. This README uses the verified pin. The W=64 fixture
pin (a25a69317b5c5a956279ccc37a5089adb489104a28ed89460b8928889b096254)
in PR #1350 was correct and is reproduced by the fixture carried here.

## Gate (completed)

The canonical suite command (run at the worktree root:
`kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)" run-tests.cljk`,
wrapper run-gate-0949.sh) ran to COMPLETION on this tree; `gate.log` in
this directory is the full run output (ends `GATE-EXIT=1`, finished
2026-10-19 ~10:20 JST). Result: **304 tests / 4939 assertions / 4908
passed / 16 failures / 15 errors (exit 1) -- not a green suite.**

The red set is identical to the base red set the chain recorded first-hand
(PR #1350's gate.log on its tree and gate-base.log on clean bea7b9b2):
16 FAILs in name and count -- numbered-grants-at-any-count 9,
malformed-policy-still-refused-by-name 3, same-policy-read-twice-is-equal 1,
packages-macos-with-a-macos-profile-and-platform-load-command 1,
native-constructors-charge-fuel-test 1,
every-source-namespace-is-reachable-from-the-tests 1; and 15 ERRORs --
row-tuple-element-argument-test 9, named-grants-at-any-count 1,
same-policy-read-twice-is-equal 1, refuses-macos-static-host-typed-list-
operations 1, refuses-macos-static-host-capability-calls-without-providers
1, text-edit-rebound-state-is-a-row-test 1, min-max-qualified-on-typed-
wasm-test 1 -- all present in base's 17 (base's 2 extra are the
native-oracle flakiness pair, see PR #1350). Nothing red here is absent at
base. The committed diff is scripts + 4 golden GLSL fixtures +
docs/evidence only -- it adds no tested namespace (the worktree's
uncommitted package-lock.json churn is npm tooling side-effect and is NOT
part of the diff).
