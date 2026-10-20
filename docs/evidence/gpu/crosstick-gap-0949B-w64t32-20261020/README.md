# crosstick-gap-0949B-w64t32-20261020 — cross-tick sign datum at a 16m20s gap (tick 20261020-1001, JUN-58): flip cell holds +/+/+ (15th transition, no flip); analyzer FLIP=YES on the anchor is NON-ADJUDICATED (batch B non-unanimous under the chain's heaviest loads) — INCONCLUSIVE, not a flip

## The finding this tick

**At a 16m20s cross-tick gap (the chain's shortest to date), the w64t32
flip cell held +/+/+ in both batches (FLIP=no) — the series' 15th
transition without a flip (one flip in fifteen) — while the w64t31 anchor's
batch B came out non-unanimous (+/−/−, only 1/3 IQR-clean) at the chain's
heaviest load window yet (load1 22.84–43.19), so the analyzer's raw
FLIP=YES on the anchor is voided by the chain's adjudication rule and the
anchor transition is INCONCLUSIVE, not a flip. The lone + run is also the
noisiest run the chain has recorded (IQR 0.5245, speedup range 0.4301–2.9397);
the anchor's single IQR-clean run (−11,965.8) re-reads the historic − sign.**

| cell | batch A (Oct 20 09:48:51–09:50:02, tick 0949 / PR #1399) | batch B (Oct 20 10:06:22–10:10:12, tick 1001) | cross-batch |
|------|------|------|------|
| w64t31 (anchor) | mean(3) **−14,604.5**, signs **−/−/−** (2/3 IQR-clean) | mean(3) **+7,506.2**, signs **+/−/−** (1/3 IQR-clean) | analyzer FLIP=**YES — NOT adjudicable** (batch B non-unanimous) |
| w64t32 (flip cell) | mean(3) **+4,435.9**, signs **+/+/+** (3/3 IQR-clean) | mean(3) **+8,996.8**, signs **+/+/+** (1/3 IQR-clean) | FLIP=**no** (adjudicable, both sign-unanimous; noise-labeled on batch B) |

ns/dispatch, variant-chunked minus baseline-chunked. All 12 runs `RESULT
verified=true`, runner exit 0. Batch-B IQR: anchor run1 0.5245 fails
(load1 22.84, gap +47,564.5 — the + run, and the noisiest run in the
chain's series), run2 0.0432 clean (load1 40.11, gap −11,965.8 — the
historic anchor sign), run3 0.1005 fails (load1 43.19, gap −13,080.1,
sign also −); flip cell run1 0.0976 fails (load1 27.59, gap +19,388.7),
run2 0.1230 fails (load1 27.57, gap +2,258.8), run3 0.0353 clean (load1
40.69, gap +5,342.8). Batch B is 2/6 IQR-clean — the chain's least-clean
batch since #1396's 2/6 — and all six probe-internal verdicts read
`vs-1.0=indistinguishable-at-this-noise`. The chain rule is IQR ≤ 0.05.
Absolute magnitudes are not comparable across batches.

**The flip-cell series gains its 15th no-flip entry: one flip in fifteen
transitions.** The RATE question stays UNANSWERED. This transition is the
chain's shortest gap (16m20s vs the previous shortest 24m33s at the 0949
tick), extending the flip cell's no-flip coverage further downward in gap
length.

**The anchor FLIP=YES is NOT a measured flip.** The analyzer's raw set
comparison prints FLIP=YES (batch A's {−} vs batch B's {+,−}); the chain's
adjudication rule voids it because batch B's anchor is non-unanimous (the
same rule as #1394's refusal of #1390's artifact and #1398's refusal of
#1396's). Reported as INCONCLUSIVE. Recorded from the logs without
upgrading any state: the only + run is the batch's noisiest by a wide
margin (IQR 0.5245 vs the 0.05 rule; the run's own verdict is
"indistinguishable-at-this-noise"), and the two − runs include the only
clean run; this is an OBSERVATION in the #1396 noise-attribution
hypothesis's pattern (load noise moving the anchor's sign), not a datum
that adjudicates it — this batch is itself non-unanimous and cannot serve
as a clean anchor side, and the hypothesis remains at its previous two
supporting data (PR #1398 and tick 0949), NOT adjudicated.

## What this bounds, honestly

- **CROSS-TICK / CROSS-SESSION datum**: gap and session restart remain
  confounded; in-session >=30 min stays INFEASIBLE at the 1800 s budget.
  16m20s is the chain's SHORTEST cross-tick gap so far (previous shortest
  24m33s at tick 0949).
- **Load confound (the heaviest in the chain).** Batch B ran at load1
  22.84–43.19 — the chain's heaviest batch window — and returned only 2/6
  IQR-clean runs, all six probe verdicts "indistinguishable-at-this-noise";
  contrast tick 0949's lowest-load batch (11.12–17.40) with its tightest
  flip-cell IQRs (0.0065–0.0102). The chain has now recorded both extremes
  and the noise tracks the load in both directions. The load source is
  UNATTRIBUTED (other sessions' traffic on this host is not ruled out).
  "Probe-idle (all sessions)" remains UNMEASURED. The gap window itself
  (09:50:02–10:06:22) carried no documented amu-gpu GPU dispatch (the 0949
  tick's post-dispatch work — analysis, commit, push, PR — the platform's
  auto-merge of PR #1388 into origin/main, and this tick's pre-dispatch
  work: git fetch, worktree creation, the fixture staging run, file copies,
  sha256 checks).
- **No protocol deviations this tick.** All six batch-B runs executed on
  the first attempt (the `node_modules` symlink to the shared checkout's
  was created before dispatch, per the established convention). Runs are
  internally adjacent by pair (10:06:22/10:07:36, 10:08:26/10:09:18,
  10:09:49/10:10:12).
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

**Base note.** Batch A ran on `2f04a37e` (tick 0949's worktree); batch B
runs on `005d48fb`. The delta (2f04a37e..005d48fb) is PR #1388 only —
evidence additions (a gate log + README; no src/test) — so the dispatched
computation is byte-identical regardless (pinned probe bytes, staged
fixture bytes, both sha-verified). The base delta is recorded as a chain
note, not analyzed as an executed-path change.

**Analyzer carry.** `analyze-1001.py` is carried from `analyze-0949.py`
with only the output filename and the docstring changed (the `diff` shows
exactly ten changed lines in five pairs). Parsing, the noise rule and the
gap label are untouched. `run-sweep.sh` is carried from the 0949 tick's;
everything below `set -e` is byte-identical except the `EV=` dir line
(verified by `diff`), and the header is rewritten only for this tick's
series list, staging-rule status, base note and gap provenance.

## States

- implemented (code + test): nothing in src/test this tick. The diff is
  this evidence dir (PRs #1346/#1390/#1394/#1395/#1396/#1398/#1399 shape).
  **Gate not run** (nothing to gate: no src/test namespace, no
  `run-tests.cljk` change). The suite's base state is the one measured on
  PR #1388's exact-base run (`cc2b2362`): 16F/15–17E, red set outside every
  amu-gpu diff, not green.
- measured (this document + logs): the 16m20s cross-tick datum above.
- UNMEASURED: the flip RATE; the anchor transition at this gap
  (INCONCLUSIVE — batch B non-unanimous); the #1396 anchor +/−/+ noise
  attribution (two supporting data, still unadjudicated); in-session >=30
  min (INFEASIBLE at budget); a probe-idle-gap datum covering ALL sessions;
  the `:arm` / `:unknown` workgroup rows (`:measured? false` stays false).

## Files

- `run-A-*.log` — byte-identical copies of tick 0949's batch B logs (PR
  #1399), sha256: `6873f010…` `cf302d96…` `0ef0ec36…` (w64t31 pairs 1–3),
  `e0250a62…` `bf60e57a…` `5f94ea6b…` (w64t32 pairs 1–3).
- `run-B-*.log` — this tick's six runs (exit 0, `RESULT verified=true`),
  sha256: `4025fdb1…` `1f2a69f9…` `b1949f7b…` (w64t31 pairs 1–3),
  `2d566457…` `27c2fb1d…` `6de7b5e0…` (w64t32 pairs 1–3).
- `run-sweep.sh` — carried from the 0949 tick's (protocol section identical
  except `EV=`).
- `analyze-1001.py` / `analyze-1001.txt` — the carried analyzer and its
  output.
