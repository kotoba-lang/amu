# crosstick-gap-1033B-w64t32-20261020 — cross-tick sign datum at a 12m52s gap (tick 20261020-1047, JUN-58): chain's shortest cross-tick gap; flip cell holds +/+/+ (17th transition, no flip); anchor adjudicates FLIP=no with both batches sign-unanimous

## The finding this tick

**At a 12m52s cross-tick gap — the chain's shortest recorded cross-tick
gap (previous shortest 16m20s at tick 1001) — both cells adjudicate
FLIP=no with both batches sign-unanimous: the w64t32 flip cell held +/+/+
in both batches (17th transition without a flip; the series is now one
flip in seventeen, and the RATE question stays UNANSWERED), and the
w64t31 anchor held −/−/− in both batches, so the anchor transition is
ADJUDICATED no-flip — no non-unanimous artifact to void this time. Every
IQR-clean anchor run on both sides reads the historic − (batch A 3/3
clean, −11,733.4 / −9,212.9 / −15,419.9; batch B 2/3 clean, −11,128.9 /
−3,725.6). Batch B ran at load1 14.07–17.82 and returned 5/6 IQR-clean:
the one dirty run is the batch's highest-load run (anchor run1, load1
17.82, IQR 0.0566) — a fourth supporting datum in the #1396
noise-attribution pattern, recorded as an OBSERVATION, NOT adjudicated.**

| cell | batch A (Oct 20 10:35:48–10:37:05, tick 1033 / PR #1402) | batch B (Oct 20 10:49:57–10:51:10, tick 1047) | cross-batch |
|------|------|------|------|
| w64t31 (anchor) | mean(3) **−12,122.1**, signs **−/−/−** (3/3 IQR-clean) | mean(3) **−9,044.6**, signs **−/−/−** (2/3 IQR-clean) | FLIP=**no — adjudicated** (both sign-unanimous) |
| w64t32 (flip cell) | mean(3) **+4,415.7**, signs **+/+/+** (3/3 IQR-clean) | mean(3) **+4,718.8**, signs **+/+/+** (3/3 IQR-clean) | FLIP=**no** (adjudicable, both sign-unanimous) |

ns/dispatch, variant-chunked minus baseline-chunked. All 12 runs `RESULT
verified=true`, runner exit 0. Batch-B IQR: anchor run1 0.0566 **dirty**
(load1 17.82, gap −12,279.3), run2 0.0295 clean (load1 14.07, gap
−11,128.9), run3 0.0264 clean (load1 16.96, gap −3,725.6); flip cell run1
0.0061 clean (load1 15.72, gap +4,779.3), run2 0.0228 clean (load1 14.42,
gap +5,321.3), run3 0.0435 clean (load1 15.43, gap +4,055.7). The chain
rule is IQR ≤ 0.05. Batch B is **5/6 IQR-clean**. Anchor probe verdicts
`vs-1.0`: `above` / `above` / `indistinguishable-at-this-noise`; flip
cell: `below` / `below` / `indistinguishable-at-this-noise`. Absolute
magnitudes are not comparable across batches.

**The flip-cell series gains its 17th no-flip entry: one flip in
seventeen transitions.** The RATE question stays UNANSWERED. This
transition sits at 12m52s — the chain's shortest cross-tick gap,
extending no-flip coverage below the previous 16m20s (tick 1001) band;
the only shorter signed gap anywhere in the chain is the 2337 tick's
within-session 6m52s datum (a different, non-cross-session protocol).
Cross-tick series now: 6m52s within-session / 12m52s / 16m20s / 24m33s /
25m36s / 27m27s / 29m21s / 30m14s / 70m26s / 124m20s / 318m29s.

**The anchor transition is ADJUDICATED, not an artifact.** Unlike
#1394/#1396/#1398/#1400 and tick 1033 (each voided a raw analyzer
FLIP=YES because one batch was non-unanimous), this transition has both
batches sign-unanimous on the anchor, so the chain's adjudication rule
returns a clean **FLIP=no**. The anchor's IQR-clean runs on both sides
read − (batch A −11,733.4 / −9,212.9 / −15,419.9; batch B −11,128.9 /
−3,725.6). The anchor's historic − sign holds on both sides of a
twelfth cross-tick transition, this one fully adjudicable.

## What this bounds, honestly

- **CROSS-TICK / CROSS-SESSION datum**: gap and session restart remain
  confounded; in-session >=30 min stays INFEASIBLE at the 1800 s budget.
  12m52s is the chain's shortest cross-tick gap to date.
- **Load natural experiment (recorded as an observation).** Within this
  datum, the higher-load batch is the noisier one: batch A (load1
  8.13–10.4, tick 1033's runs) 6/6 IQR-clean; batch B (load1 14.07–17.82)
  5/6 IQR-clean, with the single dirty run at the batch's highest load
  (17.82). Same probe bytes, same staged fixture bytes (both
  sha-attested), same base commit. This is the #1396 noise-attribution
  hypothesis's **fourth supporting datum** (after PR #1398, tick 0949,
  tick 1033) and it agrees with the pattern's direction at a new load
  band; **it does not adjudicate the hypothesis** (cross-tick batches
  differ in more than load). The load source remains UNATTRIBUTED
  (other sessions' traffic not ruled out); "probe-idle (all sessions)"
  remains UNMEASURED. The gap window itself (10:37:05–10:49:57) carried
  no documented amu-gpu GPU dispatch (the 1033 tick's post-dispatch work
  — analysis, README, commit, push, PR #1402 — and this tick's
  pre-dispatch work: git fetch, worktree creation, batch-A copies and
  sha256 checks, script writes, the fixture staging run).
- **No protocol deviations this tick.** All six batch-B runs executed on
  the first attempt (`node_modules` symlinked to the shared checkout's
  before dispatch, per the established convention). Runs are internally
  adjacent by pair (10:49:57/10:50:12, 10:50:26/10:50:40,
  10:50:57/10:51:10).
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

**Base note.** Batch A ran on `005d48fb` (tick 1033's worktree); batch B
runs on `005d48fb` — the base delta is **empty** (same commit), so the
dispatched computation is identical regardless (pinned probe bytes, staged
fixture bytes, both sha-verified).

**Analyzer carry.** `analyze-1047.py` is carried from `analyze-1033.py`
with only the output filename and the docstring changed (the `diff` shows
exactly ten changed lines in five pairs). Parsing, the noise rule and the
gap label are untouched. `run-sweep.sh` is carried from the 1033 tick's;
everything below `set -e` is byte-identical except the `EV=` dir line
(verified by `diff`), and the header is rewritten only for this tick's
series list, staging-rule status, base note and gap provenance.

## States

- implemented (code + test): nothing in src/test this tick. The diff is
  this evidence dir (PRs #1346/#1390/#1394/#1395/#1396/#1398/#1399/#1400/#1402
  shape). **Gate not run** (nothing to gate: no src/test namespace, no
  `run-tests.cljk` change). The suite's base state is the one measured on
  PR #1388's exact-base run (`cc2b2362`): 16F/15–17E, red set outside every
  amu-gpu diff, not green.
- measured (this document + logs): the 12m52s cross-tick datum above.
- UNMEASURED: the flip RATE; the #1396 anchor noise attribution (four
  supporting data, still unadjudicated); in-session >=30 min (INFEASIBLE at
  budget); a probe-idle-gap datum covering ALL sessions; the `:arm` /
  `:unknown` workgroup rows (`:measured? false` stays false).

## Files

- `run-A-*.log` — byte-identical copies of tick 1033's batch B logs (PR
  #1402), sha256: `21616df6…` `7f9ee763…` `f780e091…` (w64t31 pairs 1–3),
  `aea80536…` `5f6e0e17…` `466d5db5…` (w64t32 pairs 1–3) — matching the
  shas recorded in tick 1033's README table.
- `run-B-*.log` — this tick's six runs (exit 0, `RESULT verified=true`),
  sha256: `f68c5260…` `1fc61b9d…` `082686bb…` (w64t31 pairs 1–3),
  `019c9a1d…` `29b1ed43…` `5d1b7696…` (w64t32 pairs 1–3).
- `run-sweep.sh` — carried from the 1033 tick's (protocol section identical
  except `EV=`).
- `analyze-1047.py` / `analyze-1047.txt` — the carried analyzer and its
  output.
