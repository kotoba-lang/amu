# crosstick-gap-1001B-w64t32-20261020 — cross-tick sign datum at a 25m36s gap (tick 20261020-1033, JUN-58): flip cell holds +/+/+ (16th transition, no flip); anchor analyzer FLIP=YES is NON-ADJUDICATED (batch A non-unanimous) — clean-vs-clean both sides read the historic −, at the chain's lowest load window

## The finding this tick

**At a 25m36s cross-tick gap, the w64t32 flip cell held +/+/+ in both
batches (FLIP=no, adjudicable — both sign-unanimous): the series' 16th
transition without a flip (one flip in sixteen), and the RATE question
stays UNANSWERED. The w64t31 anchor's analyzer output reads raw FLIP=YES
(batch A's signs {+,−} vs batch B's {−}), but batch A is non-unanimous, so
the chain's adjudication rule voids it exactly as it voided #1390's and
#1396's artifacts — the anchor transition is INCONCLUSIVE, not a flip. On
IQR-clean runs only, both sides read the historic − sign: batch A's sole
clean run −11,965.8, batch B 3/3 clean mean(3) −12,122.1. Batch B ran at
the chain's lowest recorded load window (load1 8.13–10.4) and is 6/6
IQR-clean with all three anchor probe verdicts decisive (`vs-1.0=above`) —
the chain-heaviest batch (batch A, load1 22.84–43.19) had produced the
chain's noisiest run and a non-unanimous anchor. This is a third supporting
datum in the #1396 noise-attribution pattern (the anchor's + tracks high
load), recorded as an OBSERVATION — the hypothesis remains NOT
adjudicated.**

| cell | batch A (Oct 20 10:06:22–10:10:12, tick 1001 / PR #1400) | batch B (Oct 20 10:35:48–10:37:05, tick 1033) | cross-batch |
|------|------|------|------|
| w64t31 (anchor) | mean(3) **+7,506.2**, signs **+/−/−** (1/3 IQR-clean) | mean(3) **−12,122.1**, signs **−/−/−** (3/3 IQR-clean) | analyzer FLIP=**YES — NOT adjudicable** (batch A non-unanimous) |
| w64t32 (flip cell) | mean(3) **+8,996.8**, signs **+/+/+** (1/3 IQR-clean) | mean(3) **+4,415.7**, signs **+/+/+** (3/3 IQR-clean) | FLIP=**no** (adjudicable, both sign-unanimous) |

ns/dispatch, variant-chunked minus baseline-chunked. All 12 runs `RESULT
verified=true`, runner exit 0. Batch-B IQR: anchor run1 0.0365 clean (load1
9.31, gap −11,733.4), run2 0.0330 clean (load1 8.13, gap −9,212.9), run3
0.0339 clean (load1 9.08, gap −15,419.9); flip cell run1 0.0084 clean
(load1 9.12, gap +4,293.0), run2 0.0137 clean (load1 8.86, gap +3,502.9),
run3 0.0135 clean (load1 10.4, gap +5,451.2). Batch B is **6/6 IQR-clean**
— the chain rule is IQR ≤ 0.05. All three anchor probe verdicts read
`vs-1.0=above` (the chain has recorded `above` verdicts before; this is
not claimed as a first — it is the anchor's cleanest batch in the
cross-tick series). Absolute magnitudes are not comparable across batches.

**The flip-cell series gains its 16th no-flip entry: one flip in sixteen
transitions.** The RATE question stays UNANSWERED. This transition sits at
25m36s — between the chain's previous shortest (16m20s at tick 1001) and
the 27m27s (tick 0805) / 29–31m entries, extending no-flip coverage
through the mid-20-minute band.

**The anchor FLIP=YES is NOT a measured flip.** The analyzer's raw set
comparison prints FLIP=YES; the chain's adjudication rule voids it because
batch A's anchor is non-unanimous (+/−/− — the same rule as #1394's
refusal of #1390's artifact, #1398's refusal of #1396's, and tick 1001's
refusal of its own batch-B artifact). Reported as INCONCLUSIVE. What the
clean evidence says, recorded without upgrading any state: every IQR-clean
anchor run on both sides of this transition reads − (batch A's single
clean run −11,965.8; batch B's three clean runs −11,733.4 / −9,212.9 /
−15,419.9). This is the #1396 noise-attribution hypothesis's pattern — the
anchor's lone + was the chain's noisiest run (IQR 0.5245) under the
chain-heaviest loads — and it is the hypothesis's **third supporting
datum** (after PR #1398 and tick 0949), **NOT an adjudication**; the
hypothesis remains "supporting data, unadjudicated".

## What this bounds, honestly

- **CROSS-TICK / CROSS-SESSION datum**: gap and session restart remain
  confounded; in-session >=30 min stays INFEASIBLE at the 1800 s budget.
  25m36s is mid-band for the chain (previous: 16m20s shortest at tick
  1001, then 24m33s / 27m27s / 29m21s / 30m14s / 70m26s / 124m20s /
  318m29s in the recorded series).
- **Load natural experiment (recorded as an observation).** Batch A ran at
  load1 22.84–43.19 (chain-heaviest, directly attested by the copied
  run-A logs) and returned 2/6 IQR-clean with the chain's noisiest run and
  a non-unanimous anchor; batch B ran at load1 8.13–10.4 (below the
  previously recorded chain-lowest window, 11.12–17.40 at tick 0949 per
  the chain's records) and returned 6/6 IQR-clean with a unanimous anchor
  on the historic sign. Same probe bytes, same staged fixture bytes (both
  sha-attested), consecutive ticks. The noise tracks the load in both
  directions across the chain's extremes; **this is consistent with the
  #1396 noise-attribution hypothesis and is its third supporting datum,
  but it does not adjudicate it** (cross-tick batches differ in more than
  load). The load source remains UNATTRIBUTED (other sessions' traffic not
  ruled out); "probe-idle (all sessions)" remains UNMEASURED. The gap
  window itself (10:10:12–10:35:48) carried no documented amu-gpu GPU
  dispatch (the 1001 tick's post-dispatch work — analysis, commit, push,
  PR #1400 — and this tick's pre-dispatch work: git fetch, worktree
  creation, batch-A copies, script writes, the fixture staging run, sha256
  checks).
- **No protocol deviations this tick.** All six batch-B runs executed on
  the first attempt (the `node_modules` symlink to the shared checkout's
  was created before dispatch, per the established convention). Runs are
  internally adjacent by pair (10:35:48/10:36:06, 10:36:20/10:36:36,
  10:36:50/10:37:05).
- No value here is a workgroup-default value; every number is measured on
  this host (Apple M1 Max / MoltenVK 1.3.357 / glslang 11:16.6.0, `INFO
  Apple M1 Max|1.3.357|1024|1 aarch64-macos` self-printed by every run) at
  lanes 2,095,104. Nothing flips `:measured?` in
  `kotoba.compiler.accelerator-targets` — `:arm` and `:unknown` rows stay
  provisional (`:measured? false`); this diff does not touch that file.

## Protocol and base note

**Probe identity: the chain's pinned bytes, sha256 `3696ca0d…`** (full:
`3696ca0db0e28c5b41fa5c8551df2ae1302deb190e91722408117a06077ef652`), run as
`scripts/gpu-subgroup-reduce-chunksweep-pinned-3696ca0d.cljk`, re-verified
by `run-sweep.sh`'s shasum guard before any run. Every SHAPE line
self-printed `fixture=subgroup-reduce-w64-sum.emitted.glsl sha256=a25a6931…`.

**Chain inputs at this base (the PR #1393 staging rule — executed, not a
no-op).** This worktree's base is origin/main `005d48fb` — on/after #1393's
merge, so `test/fixtures/gpu/` held the regenerated post-fix bytes and `sh
scripts/gpu-sign-chain-stage-fixtures.sh.txt` was run from this worktree
root before dispatch, restoring the chain's pinned pre-fix fixture bytes
(all four sha256 verified by the script's fail-closed check: w32
`0cf6c406…`, w64 `a25a6931…`, w128 `c7931718…`, w256 `087107f9…`). The
rule's invariant — the probe sees the bytes every prior datum ran — held
by that staging step. After dispatch the tracked fixtures were restored
(`git checkout -- test/fixtures/gpu/`) so this diff stays evidence-only;
the executed bytes are attested by the SHAPE-line sha256 in every log.

**Base note.** Batch A ran on `005d48fb` (tick 1001's worktree); batch B
runs on `005d48fb` — the base delta is **empty** (same commit), so the
dispatched computation is identical regardless (pinned probe bytes, staged
fixture bytes, both sha-verified).

**Analyzer carry.** `analyze-1033.py` is carried from `analyze-1001.py`
with only the output filename and the docstring changed (the `diff` shows
exactly ten changed lines in five pairs). Parsing, the noise rule and the
gap label are untouched. `run-sweep.sh` is carried from the 1001 tick's;
everything below `set -e` is byte-identical except the `EV=` dir line
(verified by `diff`), and the header is rewritten only for this tick's
series list, staging-rule status, base note and gap provenance.

## States

- implemented (code + test): nothing in src/test this tick. The diff is
  this evidence dir (PRs #1346/#1390/#1394/#1395/#1396/#1398/#1399/#1400
  shape). **Gate not run** (nothing to gate: no src/test namespace, no
  `run-tests.cljk` change). The suite's base state is the one measured on
  PR #1388's exact-base run (`cc2b2362`): 16F/15–17E, red set outside every
  amu-gpu diff, not green.
- measured (this document + logs): the 25m36s cross-tick datum above.
- UNMEASURED: the flip RATE; the anchor transition at this gap
  (INCONCLUSIVE — batch A non-unanimous; the clean-vs-clean − read is an
  observation, not a state upgrade); the #1396 anchor noise attribution
  (three supporting data, still unadjudicated); in-session >=30 min
  (INFEASIBLE at budget); a probe-idle-gap datum covering ALL sessions;
  the `:arm` / `:unknown` workgroup rows (`:measured? false` stays false).

## Files

- `run-A-*.log` — byte-identical copies of tick 1001's batch B logs (PR
  #1400), sha256: `4025fdb1…` `1f2a69f9…` `b1949f7b…` (w64t31 pairs 1–3),
  `2d566457…` `27c2fb1d…` `6de7b5e0…` (w64t32 pairs 1–3) — matching the
  shas recorded in tick 1001's README table.
- `run-B-*.log` — this tick's six runs (exit 0, `RESULT verified=true`),
  sha256: `21616df6…` `7f9ee763…` `f780e091…` (w64t31 pairs 1–3),
  `aea80536…` `5f6e0e17…` `466d5db5…` (w64t32 pairs 1–3).
- `run-sweep.sh` — carried from the 1001 tick's (protocol section identical
  except `EV=`).
- `analyze-1033.py` / `analyze-1033.txt` — the carried analyzer and its
  output.
