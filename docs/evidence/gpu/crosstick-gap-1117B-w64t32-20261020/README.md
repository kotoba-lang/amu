# crosstick-gap-1117B-w64t32-20261020 — cross-tick sign datum at a 15m21s gap (tick 20261020-1132, JUN-58): the flip-cell transition is INCONCLUSIVE — analyzer FLIP=YES is NON-ADJUDICATED (batch B non-unanimous +/−/+; the discordant −88.9 ns run is the batch's only non-IQR-clean flip-cell run and sits within noise of zero); the anchor adjudicates FLIP=no with both batches sign-unanimous

## The finding this tick

**The flip cell does not read +/+/+ in batch B: its signs are +/−/+, so the
analyzer's raw FLIP=YES is voided by the chain's adjudication rule (a
transition counts only when both batches are sign-unanimous on that cell)
— the transition is INCONCLUSIVE, NOT a flip and NOT a no-flip entry.**
This is the cross-tick series' first non-adjudication on the flip cell;
every prior voided artifact in the series (#1396, #1398, #1400, #1402) was
anchor-side. The discordant run (run2, gap **−88.9 ns/dispatch**) is the
batch's only non-IQR-clean flip-cell run (IQR 0.0654 > 0.05) and its
magnitude is two orders below the cell's clean-run gaps (+4,557.6 /
+1,287.1) — within noise of zero, not a sign reversal at the historic
magnitude. Both IQR-clean flip-cell runs read +. The w64t31 anchor held
−/−/− in both batches, so the anchor transition is **ADJUDICATED FLIP=no**.

| cell | batch A (Oct 20 11:21:10–11:22:20, tick 1117 / PR #1406) | batch B (Oct 20 11:37:41–11:38:53, tick 1132) | cross-batch |
|------|------|------|------|
| w64t31 (anchor) | mean(3) **−10,769.2**, signs **−/−/−** (3/3 IQR-clean) | mean(3) **−13,893.9**, signs **−/−/−** (1/3 IQR-clean) | FLIP=**no — adjudicated** (both sign-unanimous) |
| w64t32 (flip cell) | mean(3) **+4,600.9**, signs **+/+/+** (3/3 IQR-clean) | mean(3) **+1,918.6**, signs **+/−/+** (2/3 IQR-clean) | analyzer FLIP=**YES — NON-ADJUDICATED** (batch B non-unanimous) → transition **INCONCLUSIVE** |

ns/dispatch, variant-chunked minus baseline-chunked. All 12 runs `RESULT
verified=true`, runner exit 0. Batch-B IQR: anchor run1 0.0658 **dirty**
(load1 10.15, gap −12,853.5), run2 0.0868 **dirty** (load1 13.87, gap
−14,431.6), run3 0.0426 clean (load1 15.52, gap −14,396.5); flip cell run1
0.0178 clean (load1 11.36, gap +4,557.6), run2 0.0654 **dirty** (load1
12.23, gap −88.9), run3 0.0317 clean (load1 15.35, gap +1,287.1). The
chain rule is IQR ≤ 0.05. Batch B is **3/6 IQR-clean** — the chain's
dirtiest batch since tick 1001's batch A (2/6). Anchor probe verdicts
`vs-1.0`: `above` / `indistinguishable-at-this-noise` / `above`; flip
cell: `indistinguishable-at-this-noise` on all three. Absolute magnitudes
are not comparable across batches.

**The flip-cell series gains NO entry this tick.** A voided transition
cannot advance the count, so the series stands exactly as recorded at tick
1117 ("the 19th transition without a flip; one flip in nineteen", PR
#1406) and the RATE question stays UNANSWERED. This would-be transition
sits at a 15m21s gap — slotting between the 14m59s (tick 1102) and 16m20s
(tick 1001) entries; the gap series is now: 6m52s within-session / 12m52s
/ 13m51s / 14m59s / **15m21s (this tick, voided transition)** / 16m20s /
24m33s / 25m36s / 27m27s / 29m21s / 30m14s / 70m26s / 124m20s / 318m29s.

**The anchor transition is ADJUDICATED, not an artifact.** Both batches
are sign-unanimous on the anchor (−/−/− and −/−/−), so the rule returns a
clean **FLIP=no**. The anchor's historic − sign holds on both sides of
another cross-tick transition. Caveat on precision, not on sign: batch
B's anchor runs are only 1/3 IQR-clean (runs 1–2 at IQR 0.0658/0.0868),
so the batch-B anchor mean(3) −13,893.9 is a noisy estimate; the sign
itself is unanimous in all six anchor runs across both batches (the
dirtiest runs still read −).

## What this bounds, honestly

- **CROSS-TICK / CROSS-SESSION datum**: gap and session restart remain
  confounded; in-session >=30 min stays INFEASIBLE at the 1800 s budget.
- **Load natural experiment (recorded as an observation).** This datum is
  the series' **second consecutive non-supporting datum** for the #1396
  noise-attribution hypothesis (after tick 1117's): batch B ran *lighter*
  than batch A (load1 10.15–15.52 vs 14.1–19.01) yet returned the dirtier
  batch (3/6 IQR-clean vs 6/6), and the batch's heaviest run (load1 15.52)
  is its cleanest anchor run. The direction is opposite to "heavier load →
  dirtier runs"; the datum neither supports the hypothesis nor adjudicates
  it (cross-tick batches differ in more than load). The load source remains
  UNATTRIBUTED (other sessions' traffic not ruled out); "probe-idle (all
  sessions)" remains UNMEASURED.
- **No protocol deviations this tick.** All six batch-B runs executed on
  the first attempt (`node_modules` symlinked to the shared checkout's at
  worktree creation, before dispatch, per the established convention).
  Runs are internally adjacent by pair (11:37:41/11:37:58,
  11:38:12/11:38:26, 11:38:40/11:38:53). The carried `run-sweep.sh` body
  was machine-checked byte-identical to tick 1117's below `set -e` (only
  `EV=` differing); `analyze-1132.py`'s carry was machine-checked to
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

**Base note.** Batch A ran on `005d48fb` (tick 1117's worktree); batch B
runs on `005d48fb` — the base delta is **empty** (same commit), so the
dispatched computation is identical regardless (pinned probe bytes, staged
fixture bytes, both sha-verified).

**Analyzer carry.** `analyze-1132.py` is carried from `analyze-1117.py`
with only the carry-source line, the batch attribution pair and the
output-filename pair (docstring and code) changed — the `diff` shows
exactly five changed line-pairs (10 diff lines), machine-checked. Parsing,
the noise rule and the gap label are untouched. `run-sweep.sh` is carried
from the 1117 tick's; everything below `set -e` is byte-identical except
the `EV=` dir line (verified programmatically), and the header is
rewritten only for this tick's series list, staging-rule status, base note
and gap provenance.

## States

- implemented (code + test): nothing in src/test this tick. The diff is
  this evidence dir (PRs #1346/#1390/#1394/#1395/#1396/#1398/#1399/#1400/
  #1402/#1403/#1405/#1406 shape). **Gate not run** (nothing to gate: no
  src/test namespace, no `run-tests.cljk` change). The suite's base state
  is the one carried by the chain from PR #1388's exact-base run: 16F/15–17E,
  red set outside every amu-gpu diff, not green — **not re-measured this
  tick**.
- measured (this document + logs): the 15m21s cross-tick datum above —
  anchor adjudicated FLIP=no, flip-cell transition INCONCLUSIVE.
- UNMEASURED: the flip RATE; the #1396 anchor noise attribution (five
  supporting data through tick 1102, two non-supporting data at ticks
  1117/1132, still unadjudicated); in-session >=30 min (INFEASIBLE at
  budget); a probe-idle-gap datum covering ALL sessions; the `:arm` /
  `:unknown` workgroup rows (`:measured? false` stays false).

## Files

- `run-A-*.log` — byte-identical copies of tick 1117's batch B logs (PR
  #1406), sha256: `cd4561ec…` `9cd0b75d…` `1888f95e…` (w64t31 pairs 1–3),
  `7691c712…` `887f6831…` `c5cbed95…` (w64t32 pairs 1–3) — matching the
  shas recorded in tick 1117's README table.
- `run-B-*.log` — this tick's six runs (exit 0, `RESULT verified=true`),
  sha256: `1eecc031…` `805d6ba4…` `1fb49e14…` (w64t31 pairs 1–3),
  `92764ff2…` `695530ed…` `22573968…` (w64t32 pairs 1–3).
- `run-sweep.sh` — carried from the 1117 tick's (body below `set -e`
  identical except `EV=`; byte-identity machine-verified).
- `analyze-1132.py` / `analyze-1132.txt` — the carried analyzer and its
  output.
