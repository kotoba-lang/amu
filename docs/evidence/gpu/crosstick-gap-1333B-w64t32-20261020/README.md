# crosstick-gap-1333B-w64t32-20261020 — cross-tick sign datum at a 13m50s gap (tick 20261020-1346, JUN-58): both cells ADJUDICATED FLIP=no with both batches sign-unanimous — the 25th transition, no flip; one flip in twenty-five

## The finding this tick

**Both cells adjudicate FLIP=no with both batches sign-unanimous at a
13m50s gap, and this transition therefore counts: the series becomes "the
25th transition without a flip; one flip in twenty-five"** (advancing the
tick-1333 count). The flip cell w64t32 read **+/+/+ in both batches**
(batch A mean(3) +5,404.6, batch B mean(3) +5,176.8) and the anchor w64t31
read **−/−/− in both batches** (batch A −15,391.3, batch B −11,973.0).
Batch B is 5/6 IQR-clean: anchor **2/3 IQR-clean** (run1 0.0521 **dirty**,
a hair over the chain's 0.05 rule — its floor/baseline 0.2629 also sits
above the 1.2× survivor band 0.2479 computed from the clean runs, and the
analyzer excludes it on IQR first; run2 0.0370 clean, run3 0.0300 clean;
survivors 2,3 est −13,011.7), flip cell **3/3 IQR-clean** (0.0272 / 0.0202
/ 0.0214, all three floor shares inside the rule; est +5,176.8). The sign
is unchanged on both sides: +/+/+ against the anchor's −/−/−. The anchor's
batch-B magnitudes are the more stable side this datum (its IQR-clean est
−13,011.7 against batch A's survivor est −14,648.4); signs are stable even
where magnitudes are not.

| cell | batch A (Oct 20 13:36:01–13:37:09, tick 1333 / PR #1415) | batch B (Oct 20 13:50:59–13:52:07, tick 1346) | cross-batch |
|------|------|------|------|
| w64t31 (anchor) | mean(3) **−15,391.3**, signs **−/−/−** (1/3 IQR-clean) | mean(3) **−11,973.0**, signs **−/−/−** (2/3 IQR-clean) | FLIP=**no — adjudicated** (both sign-unanimous) |
| w64t32 (flip cell) | mean(3) **+5,404.6**, signs **+/+/+** (3/3 IQR-clean) | mean(3) **+5,176.8**, signs **+/+/+** (3/3 IQR-clean) | FLIP=**no — adjudicated** (both sign-unanimous) |

ns/dispatch, variant-chunked minus baseline-chunked. All 12 runs `RESULT
verified=true`, runner exit 0. Batch-B IQR: anchor run1 0.0521 **dirty**
(load1 7.50, gap −9,895.5), run2 0.0370 clean (load1 6.37, gap −13,529.3),
run3 0.0300 clean (load1 5.83, gap −12,494.1); flip cell run1 0.0272 clean
(load1 7.17, gap +4,051.8), run2 0.0202 clean (load1 6.68, gap +5,892.6),
run3 0.0214 clean (load1 5.39, gap +5,585.9). The chain rule is IQR ≤ 0.05.
Anchor probe verdicts `vs-1.0`: `indistinguishable-at-this-noise` /
`above` / `above` (batch A read `above` / `indistinguishable-at-this-noise`
/ `indistinguishable-at-this-noise`); flip cell: `indistinguishable-at-this-noise`
on all three in both batches. The verdicts shuffled on the anchor but the
GAP sign did not move (− in every anchor run, + in every flip-cell run).

**Gap series now:** 6m52s within-session / 11m34s / 12m32s / 12m52s /
13m34s / **13m50s (this tick, 25th transition no flip)** / 13m51s /
14m51s / 14m59s / 15m21s (tick 1132, voided) / 16m20s / 24m33s / 25m36s /
27m27s (tick 1201, voided) / 27m27s (tick 0805) / 29m21s / 30m9s /
30m14s / 70m26s / 124m20s / 318m29s. This datum sits between 13m34s and
13m51s — the chain's fifth-shortest cross-tick gap, by a 1-second margin
over 13m51s (830 s vs 831 s).

## What this bounds, honestly

- **CROSS-TICK / CROSS-SESSION datum**: gap and session restart remain
  confounded; this datum is at a 13m50s gap across a tick boundary. A
  no-flip bounds nothing against a stochastic flip rate.
- **Load natural experiment (recorded as an observation).** Direction-wise
  this datum is **supporting** for the #1396 noise-attribution hypothesis
  at the anchor — the first supporting-direction datum since tick 1102,
  after seven non-supporting data (ticks 1117/1132/1201/1216/1248/1300/
  1315) and one mixed-direction datum (tick 1333): batch B ran at far
  **lighter** loads than batch A (anchor 5.83–7.50 vs 15.70–18.68, flip
  cell 5.39–7.17 vs 17.42–19.84) and the anchor got **cleaner** (1/3 →
  2/3 IQR-clean) as load fell; within batch B the anchor's single dirty
  run is its highest-load run (7.50). The flip cell stayed 3/3 IQR-clean
  at both load levels (batch-B IQRs 0.0272/0.0202/0.0214 vs batch A
  0.0181/0.0336/0.0334 — comparable). But cross-tick batches differ in
  more than load, so this datum **does not adjudicate** the hypothesis.
  The load source remains UNATTRIBUTED (other sessions' traffic not ruled
  out); "probe-idle (all sessions)" remains UNMEASURED.
- **No protocol deviations this tick.** All six batch-B runs executed on
  the first attempt (`node_modules` symlinked to the shared checkout's at
  worktree creation 13:48, before dispatch, per the established
  convention). Runs are internally adjacent by pair (13:50:59/13:51:13,
  13:51:26/13:51:40, 13:51:53/13:52:07). The carried `run-sweep.sh` body
  was machine-checked byte-identical to tick 1333's below `set -e` (only
  `EV=` differing — exactly one changed line-pair, verified
  programmatically); `analyze-1346.py`'s carry was machine-checked to
  exactly five changed line-pairs (the carry-source line, the two-line
  batch attribution pair, and the output-filename pair in docstring and
  code — 10 changed content lines, verified by diff); parsing, the noise
  rule and the gap label are untouched.
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
(full: `a25a69317b5c5a956279ccc37a5089adb489104a28ed89460b8928889b096254`,
6/6 batch-B logs, machine-checked).

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

**Base note.** Batch A ran on `005d48fb` (tick 1333's worktree); batch B
runs on `005d48fb` — the base delta is **empty** (same commit), so the
dispatched computation is identical regardless (pinned probe bytes, staged
fixture bytes, both sha-verified).

**Gap provenance.** The wall-clock window between batch A (last run
started 13:37:09 Oct 20) and batch B (first run 13:50:59) carried NO
documented amu-gpu GPU dispatch: the 1333 tick's post-dispatch work
(analysis, README, commit 13:39:26, push, PR #1415 opened 13:39:49) and
this tick's pre-dispatch work (git fetch, worktree creation 13:48, batch-A
copies and sha256 checks 13:49, script writes, the analyzer carry and its
five-line-pair check, the fixture staging run) only. Other sessions' GPU
traffic on this host is not ruled out. Recorded as a confound of this
datum.

**Analyzer carry.** `analyze-1346.py` is carried from `analyze-1331.py`
with only the carry-source line, the batch attribution pair and the
output-filename pair (docstring and code) changed — the `diff` shows
exactly five changed line-pairs (10 changed content lines),
machine-checked. Parsing, the noise rule and the gap label are untouched.
`run-sweep.sh` is carried from the 1333 tick's; everything below `set -e`
is byte-identical except the `EV=` dir line (verified programmatically),
and the header is rewritten only for this tick's series list, staging-rule
status, base note and gap provenance.

## States

- implemented (code + test): nothing in src/test this tick. The diff is
  this evidence dir (PRs #1346/#1390/#1394/#1395/#1396/#1398/#1399/#1400/
  #1402/#1403/#1405/#1406/#1408/#1409/#1410/#1412/#1413/#1414/#1415 shape).
  **Gate not run** (nothing to gate: no src/test namespace, no
  `run-tests.cljk` change). The suite's base state is the one carried by
  the chain from PR #1388's exact-base run: 16F/15–17E, red set outside
  every amu-gpu diff, not green — **not re-measured this tick**.
- measured (this document + logs): the 13m50s cross-tick datum above —
  both cells adjudicated FLIP=no with both batches sign-unanimous; the
  25th transition without a flip (one flip in twenty-five).
- UNMEASURED: the flip RATE; the #1396 anchor noise attribution (five
  supporting data through tick 1102, seven non-supporting data at ticks
  1117/1132/1201/1216/1248/1300/1315, one mixed-direction datum at tick
  1333, plus this directionally supporting datum at tick 1346 — anchor
  cleaner as load fell — still unadjudicated); in-session >=30 min
  (INFEASIBLE at budget); a probe-idle-gap datum covering ALL sessions;
  the `:arm` / `:unknown` workgroup rows (`:measured? false` stays false).

## Files

- `run-A-*.log` — byte-identical copies of tick 1333's batch B logs (PR
  #1415), sha256: `3442481d…` `b8671ac8…` `8d646327…` (w64t31 pairs 1–3),
  `561f7956…` `7c25d9c0…` `0deda030…` (w64t32 pairs 1–3) — matching the
  shas recorded in tick 1333's README table, machine-checked before copy.
- `run-B-*.log` — this tick's six runs (exit 0, `RESULT verified=true`),
  sha256: `e06da337…` `a0f4a4c5…` `e5defc0c…` (w64t31 pairs 1–3),
  `16d5dad5…` `12f16021…` `8330dfe1…` (w64t32 pairs 1–3).
- `run-sweep.sh` — carried from the 1333 tick's (body below `set -e`
  identical except `EV=`; byte-identity machine-verified).
- `analyze-1346.py` / `analyze-1346.txt` — the carried analyzer and its
  output.
