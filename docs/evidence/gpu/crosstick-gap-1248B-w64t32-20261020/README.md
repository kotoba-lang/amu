# crosstick-gap-1248B-w64t32-20261020 — cross-tick sign datum at a 12m32s gap (tick 20261020-1300, JUN-58): both cells ADJUDICATED FLIP=no with both batches sign-unanimous — the 22nd transition, no flip; one flip in twenty-two; chain's second-shortest cross-tick gap

## The finding this tick

**Both cells adjudicate FLIP=no with both batches sign-unanimous at a
12m32s gap, and this transition therefore counts: the series becomes "the
22nd transition without a flip; one flip in twenty-two"** (advancing the
tick-1248 count). The flip cell w64t32 read **+/+/+ in both batches**
(batch A mean(3) +4,330.7, batch B mean(3) +3,864.9) and the anchor w64t31
read **−/−/− in both batches** (batch A −10,444.3, batch B −14,874.7).
Batch B is 5/6 IQR-clean (the same shape as the previous two batches):
anchor **2/3 IQR-clean** (0.0426 / **0.0905 dirty** / 0.0423 — run2 over
the chain's 0.05 rule; its floor/baseline 0.2052 passes the floor-share
rule, so it is dirty on IQR alone; survivors 1 and 3 est −14,093.2), flip
cell **3/3 IQR-clean** (0.0236 / 0.0156 / 0.0192, all three floor shares
inside the rule; est +3,864.9). The sign is unchanged on both sides:
+/+/+ against the anchor's −/−/−.

| cell | batch A (Oct 20 12:51:27–12:52:41, tick 1248 / PR #1412) | batch B (Oct 20 13:05:13–13:06:26, tick 1300) | cross-batch |
|------|------|------|------|
| w64t31 (anchor) | mean(3) **−10,444.3**, signs **−/−/−** (3/3 IQR-clean) | mean(3) **−14,874.7**, signs **−/−/−** (2/3 IQR-clean) | FLIP=**no — adjudicated** (both sign-unanimous) |
| w64t32 (flip cell) | mean(3) **+4,330.7**, signs **+/+/+** (2/3 IQR-clean) | mean(3) **+3,864.9**, signs **+/+/+** (3/3 IQR-clean) | FLIP=**no — adjudicated** (both sign-unanimous) |

ns/dispatch, variant-chunked minus baseline-chunked. All 12 runs `RESULT
verified=true`, runner exit 0. Batch-B IQR: anchor run1 0.0426 clean
(load1 12.26, gap −12,330.1), run2 0.0905 **dirty** (load1 9.91, gap
−16,437.5), run3 0.0423 clean (load1 9.57, gap −15,856.4); flip cell run1
0.0236 clean (load1 12.38, gap +4,437.5), run2 0.0156 clean (load1 11.03,
gap +2,635.7), run3 0.0192 clean (load1 9.02, gap +4,521.5). The chain
rule is IQR ≤ 0.05. Anchor probe verdicts `vs-1.0`:
`indistinguishable-at-this-noise` / `indistinguishable-at-this-noise` /
`above`; flip cell: `indistinguishable-at-this-noise` on all three. Both
batches ran the same base (below), so their magnitudes are directly
comparable: at the heavier batch-B loads the anchor reads further negative
(−10,444.3 → −14,874.7) while the flip cell's survivor estimate moves
toward zero (+5,163.6 → +3,864.9). Signs unchanged on both sides.

**Gap series now:** 6m52s within-session / 11m34s / **12m32s (this tick,
22nd transition no flip)** / 12m52s / 13m51s / 14m59s / 15m21s (tick 1132,
voided) / 16m20s / 24m33s / 25m36s / 27m27s (tick 1201, voided) / 27m27s
(tick 0805) / 29m21s / 30m9s / 30m14s / 70m26s / 124m20s / 318m29s. This
datum is the chain's **second-shortest cross-tick gap** (11m34s remains
shortest; 12m52s drops to third).

## What this bounds, honestly

- **CROSS-TICK / CROSS-SESSION datum**: gap and session restart remain
  confounded; this datum is at a 12m32s gap across a tick boundary. A
  no-flip bounds nothing against a stochastic flip rate.
- **Load natural experiment (recorded as an observation).** This datum is
  the series' **sixth consecutive non-supporting datum** for the #1396
  noise-attribution hypothesis (after ticks 1117's, 1132's, 1201's, 1216's
  and 1248's): batch B ran **heavier** than batch A at every run (load1
  9.02–12.38 vs 6.96–9.69 — reversing tick 1248's series-lowest-load
  direction) yet was **not dirtier** (5/6 IQR-clean in both batches; the
  batch-B dirty run sits at load1 9.91, the batch's middle loads). The
  direction is again opposite to "heavier load → dirtier runs"; the datum
  neither supports the hypothesis nor adjudicates it (cross-tick batches
  differ in more than load). The load source remains UNATTRIBUTED (other
  sessions' traffic not ruled out); "probe-idle (all sessions)" remains
  UNMEASURED.
- **No protocol deviations this tick.** All six batch-B runs executed on
  the first attempt (`node_modules` symlinked to the shared checkout's at
  worktree creation, before dispatch, per the established convention).
  Runs are internally adjacent by pair (13:05:13/13:05:30,
  13:05:43/13:05:57, 13:06:12/13:06:26). The carried `run-sweep.sh` body
  was machine-checked byte-identical to tick 1248's below `set -e` (only
  `EV=` differing); `analyze-1300.py`'s carry was machine-checked to
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

**Base note.** Batch A ran on `005d48fb` (tick 1248's worktree); batch B
runs on `005d48fb` — the base delta is **empty** (same commit), so the
dispatched computation is identical regardless (pinned probe bytes, staged
fixture bytes, both sha-verified).

**Gap provenance.** The wall-clock window between batch A (ended 12:52:41
Oct 20) and batch B (first run 13:05:13) carried NO documented amu-gpu GPU
dispatch: the 1248 tick's post-dispatch work (analysis, README, commit,
push, PR #1412) and this tick's pre-dispatch work (git fetch, worktree
creation, batch-A copies and sha256 checks, script writes, the fixture
staging run) only. Other sessions' GPU traffic on this host is not ruled
out. Recorded as a confound of this datum.

**Analyzer carry.** `analyze-1300.py` is carried from `analyze-1248.py`
with only the carry-source line, the batch attribution pair and the
output-filename pair (docstring and code) changed — the `diff` shows
exactly five changed line-pairs (10 changed content lines),
machine-checked. Parsing, the noise rule and the gap label are untouched.
`run-sweep.sh` is carried from the 1248 tick's; everything below `set -e`
is byte-identical except the `EV=` dir line (verified programmatically),
and the header is rewritten only for this tick's series list, staging-rule
status, base note and gap provenance.

## States

- implemented (code + test): nothing in src/test this tick. The diff is
  this evidence dir (PRs #1346/#1390/#1394/#1395/#1396/#1398/#1399/#1400/
  #1402/#1403/#1405/#1406/#1408/#1409/#1410/#1412 shape). **Gate not run**
  (nothing to gate: no src/test namespace, no `run-tests.cljk` change).
  The suite's base state is the one carried by the chain from PR #1388's
  exact-base run: 16F/15–17E, red set outside every amu-gpu diff, not
  green — **not re-measured this tick**.
- measured (this document + logs): the 12m32s cross-tick datum above —
  both cells adjudicated FLIP=no with both batches sign-unanimous; the
  22nd transition without a flip (one flip in twenty-two).
- UNMEASURED: the flip RATE; the #1396 anchor noise attribution (five
  supporting data through tick 1102, six non-supporting data at ticks
  1117/1132/1201/1216/1248/1300, still unadjudicated); in-session >=30 min
  (INFEASIBLE at budget); a probe-idle-gap datum covering ALL sessions;
  the `:arm` / `:unknown` workgroup rows (`:measured? false` stays false).

## Files

- `run-A-*.log` — byte-identical copies of tick 1248's batch B logs (PR
  #1412), sha256: `6db5c19a…` `35eb69de…` `4a754d5f…` (w64t31 pairs 1–3),
  `3f2ba029…` `c1684617…` `a1ffb2e6…` (w64t32 pairs 1–3) — matching the
  shas recorded in tick 1248's README table, machine-checked before copy.
- `run-B-*.log` — this tick's six runs (exit 0, `RESULT verified=true`),
  sha256: `1c084743…` `7ec922b5…` `ffc49f71…` (w64t31 pairs 1–3),
  `25f80eef…` `c11f51c1…` `06bd0de4…` (w64t32 pairs 1–3).
- `run-sweep.sh` — carried from the 1248 tick's (body below `set -e`
  identical except `EV=`; byte-identity machine-verified).
- `analyze-1300.py` / `analyze-1300.txt` — the carried analyzer and its
  output.
