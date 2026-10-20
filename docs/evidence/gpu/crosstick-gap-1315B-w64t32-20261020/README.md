# crosstick-gap-1315B-w64t32-20261020 — cross-tick sign datum at a 14m51s gap (tick 20261020-1333, JUN-58): both cells ADJUDICATED FLIP=no with both batches sign-unanimous — the 24th transition, no flip; one flip in twenty-four

## The finding this tick

**Both cells adjudicate FLIP=no with both batches sign-unanimous at a
14m51s gap, and this transition therefore counts: the series becomes "the
24th transition without a flip; one flip in twenty-four"** (advancing the
tick-1315 count). The flip cell w64t32 read **+/+/+ in both batches**
(batch A mean(3) +4,465.2, batch B mean(3) +5,404.6) and the anchor w64t31
read **−/−/− in both batches** (batch A −7,936.2, batch B −15,391.3).
Batch B is 4/6 IQR-clean: anchor **1/3 IQR-clean** (run1 0.0355 clean —
**run2 0.1063 dirty**, run3 0.0733 dirty, both over the chain's 0.05 rule;
their floor/baseline 0.2566 / 0.2780 pass the floor-share rule, so they are
dirty on IQR alone; survivor 1 est −14,648.4), flip cell **3/3 IQR-clean**
(0.0181 / 0.0336 / 0.0334, all three floor shares inside the rule; est
+5,404.6). The sign is unchanged on both sides:
+/+/+ against the anchor's −/−/−. The anchor's batch-B magnitudes are the
less stable side this datum (its only clean run reads −14,648.4 against
batch A's clean-run est −9,132.4); signs are stable even where magnitudes
are not.

| cell | batch A (Oct 20 13:20:00–13:21:10, tick 1315 / PR #1414) | batch B (Oct 20 13:36:01–13:37:09, tick 1333) | cross-batch |
|------|------|------|------|
| w64t31 (anchor) | mean(3) **−7,936.2**, signs **−/−/−** (2/3 IQR-clean) | mean(3) **−15,391.3**, signs **−/−/−** (1/3 IQR-clean) | FLIP=**no — adjudicated** (both sign-unanimous) |
| w64t32 (flip cell) | mean(3) **+4,465.2**, signs **+/+/+** (3/3 IQR-clean) | mean(3) **+5,404.6**, signs **+/+/+** (3/3 IQR-clean) | FLIP=**no — adjudicated** (both sign-unanimous) |

ns/dispatch, variant-chunked minus baseline-chunked. All 12 runs `RESULT
verified=true`, runner exit 0. Batch-B IQR: anchor run1 0.0355 clean
(load1 18.68, gap −14,648.4), run2 0.1063 **dirty** (load1 15.76, gap
−14,184.6), run3 0.0733 **dirty** (load1 15.70, gap −17,340.8); flip cell
run1 0.0181 clean (load1 19.84, gap +5,026.4), run2 0.0336 clean (load1
17.42, gap +5,750.0), run3 0.0334 clean (load1 17.87, gap +5,437.5). The
chain rule is IQR ≤ 0.05. Anchor probe verdicts `vs-1.0`: `above` /
`indistinguishable-at-this-noise` / `indistinguishable-at-this-noise`;
flip cell: `indistinguishable-at-this-noise` on all three (batch A read
`below` on all three; the verdicts moved because batch B's flip-cell IQRs
are wider, not because the GAP sign moved — the gap is + in every run).
Both batches ran the same base (below), so their magnitudes are directly
comparable: the anchor reads more negative (−7,936.2 → −15,391.3) and the
flip cell slightly more positive (+4,465.2 → +5,404.6). Signs unchanged on
both sides.

**Gap series now:** 6m52s within-session / 11m34s / 12m32s / 12m52s /
13m34s / 13m51s / **14m51s (this tick, 24th transition no flip)** / 14m59s
/ 15m21s (tick 1132, voided) / 16m20s / 24m33s / 25m36s / 27m27s (tick
1201, voided) / 27m27s (tick 0805) / 29m21s / 30m9s / 30m14s / 70m26s /
124m20s / 318m29s. This datum sits mid-pack (between 13m51s and 14m59s) —
no gap record.

## What this bounds, honestly

- **CROSS-TICK / CROSS-SESSION datum**: gap and session restart remain
  confounded; this datum is at a 14m51s gap across a tick boundary. A
  no-flip bounds nothing against a stochastic flip rate.
- **Load natural experiment (recorded as an observation).** Direction-wise
  this datum is again **non-supporting** for the #1396 noise-attribution
  hypothesis, but less cleanly so than the previous seven: the flip cell
  ran **heavier** than batch A at every run (load1 17.42–19.84 vs
  12.94–17.91) and stayed 3/3 IQR-clean — same direction as before — while
  the anchor at **near-identical loads** (15.70–18.68 vs 14.75–18.73) went
  **dirtier** (2/3 → 1/3 IQR-clean, run2 iqr 0.1063 with a single-sample
  max 1.9420 spike). Dirtiness appeared at the anchor **without a load
  increase**, which is not the direction "heavier load → dirtier runs"
  predicts; the datum neither supports the hypothesis nor adjudicates it
  (cross-tick batches differ in more than load). The load source remains
  UNATTRIBUTED (other sessions' traffic not ruled out); "probe-idle (all
  sessions)" remains UNMEASURED.
- **No protocol deviations this tick.** All six batch-B runs executed on
  the first attempt (`node_modules` symlinked to the shared checkout's at
  worktree creation, before dispatch, per the established convention).
  Runs are internally adjacent by pair (13:36:01/13:36:15,
  13:36:28/13:36:41, 13:36:55/13:37:09). The carried `run-sweep.sh` body
  was machine-checked byte-identical to tick 1315's below `set -e` (only
  `EV=` differing — exactly one changed line-pair, verified by diff);
  `analyze-1331.py`'s carry was machine-checked to exactly five changed
  line-pairs (the carry-source line, the two-line batch attribution pair,
  and the output-filename pair in docstring and code — 10 changed content
  lines, verified by diff); parsing, the noise rule and the gap label are
  untouched.
- No value here is a workgroup-default value; every number is measured on
  this host (Apple M1 Max / MoltenVK 1.3.357; `INFO
  Apple M1 Max|1.3.357|1024|1 aarch64-macos` self-printed by every run)
  at lanes 2,095,104. Nothing flips `:measured?` in
  `kotoba.compiler.accelerator-targets` — `:arm` and `:unknown` rows stay
  provisional (`:measured? false`); this diff does not touch that file.

## Protocol and base note

**Probe identity: the chain's pinned bytes, sha256 `3696ca0d…`** (full:
`3696ca0db0e28c5b41fa5c8551df2ae1302deb190e91722408117a06077ef652`), run as
`scripts/gpu-subgroup-reduce-chunksweep-pinned-3696ca0d.cljk`, re-verified
by `run-sweep.sh`'s shasum guard before any run. Every SHAPE line
self-printed `fixture=subgroup-reduce-w64-sum.emitted.glsl sha256=a25a6931…`
(full: `a25a69317b5c5a956279ccc37a5089adb489104a28ed89460b8928889b096254`).

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

**Base note.** Batch A ran on `005d48fb` (tick 1315's worktree); batch B
runs on `005d48fb` — the base delta is **empty** (same commit), so the
dispatched computation is identical regardless (pinned probe bytes, staged
fixture bytes, both sha-verified).

**Gap provenance.** The wall-clock window between batch A (last run
started 13:21:10 Oct 20) and batch B (first run 13:36:01) carried NO
documented amu-gpu GPU dispatch: the 1315 tick's post-dispatch work
(analysis, README, commit 13:23:50, push, PR #1414 opened 13:24:19) and
this tick's pre-dispatch work (git fetch, worktree creation 13:33,
batch-A copies and sha256 checks, script writes, the analyzer carry and
its five-line-pair check, the fixture staging run) only. Other sessions'
GPU traffic on this host is not ruled out. Recorded as a confound of this
datum.

**Analyzer carry.** `analyze-1331.py` is carried from `analyze-1315.py`
with only the carry-source line, the batch attribution pair and the
output-filename pair (docstring and code) changed — the `diff` shows
exactly five changed line-pairs (10 changed content lines),
machine-checked. Parsing, the noise rule and the gap label are untouched.
`run-sweep.sh` is carried from the 1315 tick's; everything below `set -e`
is byte-identical except the `EV=` dir line (verified programmatically),
and the header is rewritten only for this tick's series list, staging-rule
status, base note and gap provenance.

## States

- implemented (code + test): nothing in src/test this tick. The diff is
  this evidence dir (PRs #1346/#1390/#1394/#1395/#1396/#1398/#1399/#1400/
  #1402/#1403/#1405/#1406/#1408/#1409/#1410/#1412/#1413/#1414 shape).
  **Gate not run** (nothing to gate: no src/test namespace, no
  `run-tests.cljk` change). The suite's base state is the one carried by
  the chain from PR #1388's exact-base run: 16F/15–17E, red set outside
  every amu-gpu diff, not green — **not re-measured this tick**.
- measured (this document + logs): the 14m51s cross-tick datum above —
  both cells adjudicated FLIP=no with both batches sign-unanimous; the
  24th transition without a flip (one flip in twenty-four).
- UNMEASURED: the flip RATE; the #1396 anchor noise attribution (five
  supporting data through tick 1102, seven non-supporting data at ticks
  1117/1132/1201/1216/1248/1300/1315 plus this mixed-direction eighth
  datum at tick 1333, still unadjudicated); in-session >=30 min (INFEASIBLE
  at budget); a probe-idle-gap datum covering ALL sessions; the `:arm` /
  `:unknown` workgroup rows (`:measured? false` stays false).

## Files

- `run-A-*.log` — byte-identical copies of tick 1315's batch B logs (PR
  #1414), sha256: `a1be6ca4…` `87ca22c8…` `9be3e427…` (w64t31 pairs 1–3),
  `445fc3cf…` `fe28fcc5…` `a6174666…` (w64t32 pairs 1–3) — matching the
  shas recorded in tick 1315's README table, machine-checked before copy.
- `run-B-*.log` — this tick's six runs (exit 0, `RESULT verified=true`),
  sha256: `3442481d…` `b8671ac8…` `8d646327…` (w64t31 pairs 1–3),
  `561f7956…` `7c25d9c0…` `0deda030…` (w64t32 pairs 1–3).
- `run-sweep.sh` — carried from the 1315 tick's (body below `set -e`
  identical except `EV=`; byte-identity machine-verified).
- `analyze-1331.py` / `analyze-1331.txt` — the carried analyzer and its
  output.
