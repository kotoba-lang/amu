# gpu/loadsweep-mid-20261019 -- W=64 intermediate-load sweep (JUN-58)

Raw logs from `scripts/test-gpu-subgroup-reduce-loadsweep.cljk`, 3 verified
runs at 2x the sweep's 2^20 load (2,097,152 lanes = 32,768 workgroups), 3 at
3x (3,145,728 lanes = 49,152 workgroups), plus 1 control run at 2^20
(1,048,576 lanes = 16,384 workgroups), on Apple M1 Max / MoltenVK (Vulkan
1.3.357), glslang 11:16.6.0, aarch64-macos, 2026-10-19 08:52-08:56 JST.
These are NODE BOOTSTRAP results: the measured guest is built and extracted
through `node bin/amu`, so the numbers characterize the bootstrap compiler's
generated code and are NOT selfhost evidence.
Every run verified the SAMPLED words x[0..3] (the harness READs 16 bytes at
offset zero of x) and the first four workgroup partials of BOTH
reduce arms bit-exact (f32, sum W^2*g + W(W-1)/2 + W, g = 0..3) before
printing any timing line; all 7 runs printed `RESULT verified=true`. The
x=ok claim is scoped to those four sampled words: x[i]=i+1 across the
million-plus lanes is the INPUT GENERATOR's claim, not a verified read-back.
Host load averages 6.5-13.2 were observed on `uptime` before each run; the
committed logs do NOT contain that output (each starts at the toolchain
line), so the load figures rest on contemporaneous observation and are not
re-checkable from this evidence.

## Why this probe exists

PR #1349 (loadsweep-20261019) measured W=64 at 4x load and reported that the
arms' absolute gap grows super-proportionally to the load ("~0.4-2.7 us at
2^20 ... 6.3-6.7 us at 4x"), with the mechanism UNRESOLVED, and left "a load
sweep at W=64 between the two points" as the test. This run is that sweep.
The probe script, fixtures and protocol are byte-identical to PR #1349's
(script sha256 871bfde4a14e4168fba9808581acd7b2a704f47054cac49eee54e1f35f1da462,
verified against the committed script; an earlier revision of this line
recorded d6273519db58a1b5fc022c24b81e8c6493d6fe02, which does not hash to
any committed script -- the run logs do not identify the executing script's
hash, so provenance rests on this recorded value; W=64 fixture
sha256 a25a69317b5c5a956279ccc37a5089adb489104a28ed89460b8928889b096254);
the only difference is the lanes argv. The control run at 2^20 answers
1.0196 here vs 1.0129 (PR #1349), 1.0149 / 1.0401 (PR #1348), tying the
chains together.

## baseline/variant ratio (median of 32 within-round ratios; BELOW 1.0 = variant slower)

| run | lanes/dispatch | wg   | ratio med | iqr    | min    | max    | vs-1.0                | floor/base | ns/dispatch b / v / f        | gap v-b (ns) |
|-----|----------------|------|-----------|--------|--------|--------|-----------------------|------------|------------------------------|--------------|
| 1   | 2097152        | 32768| 0.9647    | 0.0083 | 0.9499 | 0.9801 | below (all 32 rounds) | 0.8812     | 62016 / 64219 / 54560        | 2203         |
| 2   | 2097152        | 32768| 0.9626    | 0.0193 | 0.9394 | 0.9932 | below (all 32 rounds) | 0.8863     | 62297 / 64665 / 55219        | 2368         |
| 3   | 2097152        | 32768| 0.9652    | 0.0092 | 0.9462 | 0.9802 | below (all 32 rounds) | 0.8807     | 61967 / 64247 / 54694        | 2280         |
| 4   | 3145728        | 49152| 0.9485    | 0.0276 | 0.7077 | 1.2175 | crosses (host spike)  | 0.8940     | 81524 / 86120 / 73188        | 4596         |
| 5   | 3145728        | 49152| 0.9488    | 0.0178 | 0.9265 | 0.9821 | below (all 32 rounds) | 0.8890     | 81172 / 85298 / 72075        | 4126         |
| 6   | 3145728        | 49152| 0.9456    | 0.0093 | 0.9332 | 0.9610 | below (all 32 rounds) | 0.8936     | 80302 / 84888 / 71689        | 4586         |
| 7 (control) | 1048576 | 16384| 1.0196    | 0.0123 | 0.9059 | 1.6837 | indistinguishable     | 0.8372     | 39520 / 38731 / 33145        | -788         |

4x rows for the same probe, quoted from PR #1349 (same host, same day,
08:26-08:31 JST): ratio medians 0.9390 / 0.9387 / 0.9346, gap v-b
6038 / 6579 / 6745 ns per dispatch, floor ns/dispatch 90253 / 89022 / 89629
at 4,194,240 lanes = 65,535 workgroups.

## Finding

1. **The W=64 row resolves to variant-slower by 2x load.** At 32,768
   workgroups all three runs have all 32 rounds below 1.0 (max 0.9801 /
   0.9932 / 0.9802); ratio medians 0.9626-0.9652 (spread 0.0026). The
   2^20 control is again indistinguishable. So the resolution point sits
   between 16,384 and 32,768 workgroups on this host -- nothing flipped;
   the 2^20 rows are noise-straddled in both directions.

2. **The gap grows at an essentially constant marginal cost per workgroup
   between 2x and 4x -- the data no longer require "super-proportional to
   load".** Gap means (variant - baseline ns/dispatch): 2284 (2x) -> 4436
   (3x) -> 6454 (4x). These are UNPAIRED differences of per-arm means, not
   paired round gaps: the recorded logs persist per-arm aggregates only
   (no per-round timings), so a paired gap or paired slope cannot be
   computed from this evidence. The paired, drift-cancelled quantity is
   the within-round ratio above (median of 32 within-round ratios); the
   per-arm subtraction does not cancel drift and the 3x arm additionally
   carries run 4's documented host spike. The slopes below are descriptive
   unpaired differences accordingly. Marginal cost per +16k workgroups: +2152 ns
   (2x->3x, 0.131 ns/wg) and +2018 ns (3x->4x, 0.123 ns/wg) -- the two
   segment slopes agree to within 6%. An affine fit through the 2x and 4x
   means (slope 0.128 ns/wg, intercept -1.9 us) predicts +190 ns at
   16,384 workgroups, inside the 2^20 noise band (the three 2^20 rows
   straddle zero: -788 ns here, -441 ns in PR #1349's control, and the
   0.4-2.7 us band PR #1349 quoted). PR #1349's "super-proportional"
   reading came from treating the 2^20 gap as ~0; with the intermediate
   points on the table, a constant marginal per-workgroup cost explains
   all four load points. The per-run gaps at each load agree to within
   0.4 us (2x: 2203/2368/2280; 3x: 4596/4126/4586).

3. **The floor is affine in workgroups, not fixed and not proportional.**
   Floor ns/dispatch means: 33145 (2^20, this control) -> 54824 (2x) ->
   72317 (3x) -> 89635 (4x, PR #1349). Deltas per +16k workgroups:
   +21680 / +17493 / +17318 -- a near-constant marginal floor cost of
   ~1.1-1.3 ns per workgroup on top of a fixed per-dispatch base
   (descriptive fit through 2x/4x: ~20 us fixed + 1.06 ns/wg). This
   refines PR #1349's "sub-linear in groups" with its shape: 4.0x the
   workgroups costs 2.7x the floor time because the fixed base stays put.

4. **Mechanism still UNRESOLVED.** That the variant pays ~0.12-0.13 ns per
   workgroup over the cascade (and why that marginal cost is constant
   across 32k-65k workgroups while floor/baseline sits 0.88-0.91 and
   floor/variant 0.84-0.85) is
   not measured by this probe. The PR #1349 hypothesis (shared-memory /
   shuffle traffic against a larger x[] stream) is not tested here: x[]
   bytes per dispatch grow with lanes, and workgroups grow too, so this
   sweep does not separate them.

## What this is not

One device (Apple M1 Max), one W (64). No :measured? flag is flipped
anywhere in kotoba.compiler.accelerator-targets. Cross-load percentage
comparisons carry PR #1349's floor-share caveat (floor/baseline 0.84 at
2^20, 0.88 at 2x, 0.89 at 3x, 0.91 at 4x -- the % penalty at each load is
measured against a different floor share; only the within-load ratios and
the absolute ns/dispatch gaps are compared across loads here). The 4x rows
are quoted from PR #1349, not re-measured in this run; the 3x run 4 range
crosses 1.0 on a host spike (min 0.71 / max 1.22) and is not by itself a
verdict -- its median agrees with runs 5-6 to within 0.3%. The Intel
(JUN-59) and Mali (JUN-60) comparisons need hardware this bot does not
have. W=32 stays floor-bound/unverdicted (its grids would need more than
the 65535 1D limit at any load that lifts it off the floor).

## Gate (completed and landed by follow-up tick 20261019)

The canonical suite command (run at the worktree root:
`kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)" run-tests.cljk`,
wrapper `run-gate-0849.sh`) ran to COMPLETION on this tree; `gate.log` is the
full run output (488 lines, ends `GATE-EXIT=1`, finished 2026-10-19 09:12 JST
-- the run was still executing when the PR opened, which is why the PR body
originally called this log partial; the completed log is what this commit
lands).

Result: 304 tests / 4939 assertions / 4908 passed / 16 failures / 15 errors
(exit 1).

Base comparison, first-hand: `gate-base.log` is the same canonical command
run on a CLEAN bea7b9b2 tree (worktree base-check-20261019-0204, `git status`
clean; output kept out of that tree), 2026-10-19 09:31-09:50 JST:
304 tests / 4939 assertions / 4906 passed / 16 failures / 17 errors (exit 1).

- The 16 FAILs are identical in name and count in both runs
  (policy-grant-count-test 13, ios-aot-test 1, namespace-reachability-test 1,
  native-allocation-budget-test 1).
- All 15 ERRORs of this tree's run are present in the base run's 17. The base
  run has 2 extra ERRORs this tree does not:
  `kotoba.compiler.native-rebound-row-update-test` /
  `native-rebound-row-update-test` and `kotoba.compiler.options-map-argument-test`
  / `options-map-destructures-as-a-row-test`. Both sit in the native-oracle
  family whose failures carry `:trap :host/stack-exhausted` "oracle
  inconclusive" errors; run-to-run flakiness is the working hypothesis,
  UNVERIFIED (base was run once).
- Nothing red in this tree's run is absent from the base run. The committed
  diff adds no test namespace (scripts + 4 golden GLSL fixtures under
  test/fixtures/gpu/ + docs/evidence only; the worktree's uncommitted
  package-lock.json churn is tooling side-effect and is NOT part of the
  diff).

Red set detail (this tree's run): policy-grant-count-test
(numbered-grants-at-any-count 9 FAIL, malformed-policy-still-refused-by-name
3 FAIL, same-policy-read-twice-is-equal 1 FAIL + 1 ERROR,
named-grants-at-any-count 1 ERROR); row-tuple-element-argument-test (9 ERROR);
ios-aot-test (packages-macos-with-a-macos-profile-and-platform-load-command
1 FAIL, refuses-macos-static-host-typed-list-operations +
refuses-macos-static-host-capability-calls-without-providers 2 ERROR, both
`todo:`); namespace-reachability-test
(every-source-namespace-is-reachable-from-the-tests: kotoba.compiler.execution-targets
+ kotoba.compiler.nbb.kototama-cli unreachable);
native-allocation-budget-test (native-constructors-charge-fuel-test 1 FAIL);
rebound-row-argument-test (text-edit-rebound-state-is-a-row-test 1 ERROR);
typed-wasm-min-max-test (min-max-qualified-on-typed-wasm-test 1 ERROR).
