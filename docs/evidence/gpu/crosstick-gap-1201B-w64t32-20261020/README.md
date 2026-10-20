# crosstick-gap-1201B-w64t32-20261020 — cross-tick sign datum at a 11m34s gap (tick 20261020-1216, JUN-58): the chain's shortest cross-tick gap yet; both cells ADJUDICATED FLIP=no with both batches sign-unanimous — the 20th transition, no flip

## The finding this tick

**Both cells adjudicate FLIP=no with both batches sign-unanimous at the
chain's shortest cross-tick gap to date (11m34s), and this transition
therefore counts: the series becomes "the 20th transition without a flip;
one flip in twenty"** (advancing exactly the tick-1117 count that the two
voided transitions at ticks 1132/1201 could not advance). The flip cell
w64t32 read **+/+/+ in both batches** (batch A mean(3) +5,144.2, batch B
mean(3) +5,015.9) and the anchor w64t31 read **−/−/− in both batches**
(batch A −13,305.3, batch B −12,660.8). Batch B is a clean datum in both
cells: flip cell **3/3 IQR-clean** (0.0055 / 0.0064 / 0.0072 — the chain's
lowest flip-cell IQRs again, just below tick 1201's previous low), all
three runs `vs-1.0=below`; anchor 2/3 IQR-clean. The flip cell is now
all-`below` and 3/3 IQR-clean in **both** batches — two consecutive
all-below flip-cell batches for the first time in the series.

| cell | batch A (Oct 20 12:06:20–12:08:15, tick 1201 / PR #1409) | batch B (Oct 20 12:19:49–12:21:18, tick 1216) | cross-batch |
|------|------|------|------|
| w64t31 (anchor) | mean(3) **−13,305.3**, signs **−/−/−** (2/3 IQR-clean) | mean(3) **−12,660.8**, signs **−/−/−** (2/3 IQR-clean) | FLIP=**no — adjudicated** (both sign-unanimous) |
| w64t32 (flip cell) | mean(3) **+5,144.2**, signs **+/+/+** (3/3 IQR-clean) | mean(3) **+5,015.9**, signs **+/+/+** (3/3 IQR-clean) | FLIP=**no — adjudicated** (both sign-unanimous) |

ns/dispatch, variant-chunked minus baseline-chunked. All 12 runs `RESULT
verified=true`, runner exit 0. Batch-B IQR: anchor run1 0.0558 **dirty**
(load1 13.11, gap −12,176.8), run2 0.0286 clean (load1 15.85, gap
−12,007.8), run3 0.0276 clean (load1 14.11, gap −13,797.9); flip cell
run1 0.0055 clean (load1 18.09, gap +4,787.1), run2 0.0064 clean (load1
18.98, gap +5,183.6), run3 0.0072 clean (load1 12.56, gap +5,077.1). The
chain rule is IQR ≤ 0.05. Batch B is **5/6 IQR-clean** (the same shape as
tick 1201's batch B). Anchor probe verdicts `vs-1.0`:
`indistinguishable-at-this-noise` / `above` / `above`; flip cell: `below`
on all three (second consecutive all-`below` flip-cell batch). Absolute
magnitudes are not comparable across batches; note both batches here ran
the same base (below), so their magnitudes are directly close.

**Gap series now:** 6m52s within-session / **11m34s (this tick, chain's
shortest cross-tick, 20th transition no flip)** / 12m52s / 13m51s /
14m59s / 15m21s (tick 1132, voided) / 16m20s / 24m33s / 25m36s / 27m27s
(tick 1201, voided) / 27m27s (tick 0805) / 29m21s / 30m14s / 70m26s /
124m20s / 318m29s.

## What this bounds, honestly

- **CROSS-TICK / CROSS-SESSION datum**: gap and session restart remain
  confounded; in-session >=30 min stays INFEASIBLE at the 1800 s budget.
  A no-flip bounds nothing against a stochastic flip rate.
- **Load natural experiment (recorded as an observation).** This datum is
  the series' **fourth consecutive non-supporting datum** for the #1396
  noise-attribution hypothesis (after ticks 1117's, 1132's and 1201's):
  batch B ran *heavier* than batch A (load1 max 18.98 vs 17.48) yet again
  returned 5/6 IQR-clean with the chain's lowest flip-cell IQRs (0.0055
  floor), and the batch's heaviest run (load1 18.98) is its second-cleanest
  flip-cell run (IQR 0.0064). The direction is again opposite to "heavier
  load → dirtier runs"; the datum neither supports the hypothesis nor
  adjudicates it (cross-tick batches differ in more than load). The load
  source remains UNATTRIBUTED (other sessions' traffic not ruled out);
  "probe-idle (all sessions)" remains UNMEASURED.
- **No protocol deviations this tick.** All six batch-B runs executed on
  the first attempt (`node_modules` symlinked to the shared checkout's at
  worktree creation, before dispatch, per the established convention).
  Runs are internally adjacent by pair (12:19:49/12:20:16,
  12:20:37/12:20:50, 12:21:04/12:21:18). The carried `run-sweep.sh` body
  was machine-checked byte-identical to tick 1201's below `set -e` (only
  `EV=` differing); `analyze-1216.py`'s carry was machine-checked to
  exactly five changed line-pairs (the carry-source line, the two-line
  batch attribution pair, and the output-filename pair in docstring and
  code); parsing, the noise rule and the gap label are untouched.
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

**Base note.** Batch A ran on `005d48fb` (tick 1201's worktree); batch B
runs on `005d48fb` — the base delta is **empty** (same commit), so the
dispatched computation is identical regardless (pinned probe bytes, staged
fixture bytes, both sha-verified).

**Gap provenance.** The wall-clock window between batch A (ended 12:08:15
Oct 20) and batch B (first run 12:19:49) carried NO documented amu-gpu GPU
dispatch: the 1201 tick's post-dispatch work (analysis, README, commit,
push, PR #1409) and this tick's pre-dispatch work (git fetch, worktree
creation, batch-A copies and sha256 checks, script writes, the fixture
staging run) only. Other sessions' GPU traffic on this host is not ruled
out. Recorded as a confound of this datum.

**Analyzer carry.** `analyze-1216.py` is carried from `analyze-1201.py`
with only the carry-source line, the batch attribution pair and the
output-filename pair (docstring and code) changed — the `diff` shows
exactly five changed line-pairs (10 changed content lines),
machine-checked. Parsing, the noise rule and the gap label are untouched.
`run-sweep.sh` is carried from the 1201 tick's; everything below `set -e`
is byte-identical except the `EV=` dir line (verified programmatically),
and the header is rewritten only for this tick's series list, staging-rule
status, base note and gap provenance.

## States

- implemented (code + test): nothing in src/test this tick. The diff is
  this evidence dir (PRs #1346/#1390/#1394/#1395/#1396/#1398/#1399/#1400/
  #1402/#1403/#1405/#1406/#1408/#1409 shape). **Gate not run** (nothing to
  gate: no src/test namespace, no `run-tests.cljk` change). The suite's
  base state is the one carried by the chain from PR #1388's exact-base
  run: 16F/15–17E, red set outside every amu-gpu diff, not green — **not
  re-measured this tick**.
- measured (this document + logs): the 11m34s cross-tick datum above —
  both cells adjudicated FLIP=no with both batches sign-unanimous; the
  20th transition without a flip (one flip in twenty).
- UNMEASURED: the flip RATE; the #1396 anchor noise attribution (five
  supporting data through tick 1102, four non-supporting data at ticks
  1117/1132/1201/1216, still unadjudicated); in-session >=30 min
  (INFEASIBLE at budget); a probe-idle-gap datum covering ALL sessions; the
  `:arm` / `:unknown` workgroup rows (`:measured? false` stays false).

## Files

- `run-A-*.log` — byte-identical copies of tick 1201's batch B logs (PR
  #1409), sha256: `cb61ea62…` `c00aacc2…` `fa0eeaa1…` (w64t31 pairs 1–3),
  `ede4c92e…` `625c58fa…` `21eb1fb5…` (w64t32 pairs 1–3) — matching the
  shas recorded in tick 1201's README table, machine-checked before copy.
- `run-B-*.log` — this tick's six runs (exit 0, `RESULT verified=true`),
  sha256: `8fa482b2…` `c58c2df1…` `6486f5e6…` (w64t31 pairs 1–3),
  `94ae7291…` `09bfd439…` `47e0a942…` (w64t32 pairs 1–3).
- `run-sweep.sh` — carried from the 1201 tick's (body below `set -e`
  identical except `EV=`; byte-identity machine-verified).
- `analyze-1216.py` / `analyze-1216.txt` — the carried analyzer and its
  output.
