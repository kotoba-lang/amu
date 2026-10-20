# crosstick-gap-1132B-w64t32-20261020 — cross-tick sign datum at a 27m27s gap (tick 20261020-1201, JUN-58): the flip-cell transition is INCONCLUSIVE — analyzer FLIP=YES is NON-ADJUDICATED (batch A non-unanimous +/−/+, carried from tick 1132's discordant run); the anchor adjudicates FLIP=no with both batches sign-unanimous

## The finding this tick

**The flip cell's analyzer FLIP=YES is voided by the chain's adjudication
rule on the batch-A side: batch A (tick 1132's batch B) reads +/−/+ and is
not sign-unanimous, so this would-be 20th transition is INCONCLUSIVE —
NOT a flip and NOT a no-flip entry.** Batch B itself is the chain's
cleanest flip-cell batch yet: signs **+/+/+**, 3/3 IQR-clean (0.0057 /
0.0087 / 0.0088 — the lowest flip-cell IQRs in the series), all three runs
`vs-1.0=below`, mean(3) **+5,144.2 ns/dispatch** at the historic positive
magnitude (clean-run range +4,538.1 … +5,948.2, matching tick 1117's
batch-B range +4,122.1 … +4,946.3). The void is entirely inherited from
the +/−/+ batch on the other side (the −88.9 ns discordant run, within
noise of zero, that tick 1132 already recorded). This is the second
consecutive flip-cell non-adjudication (#1408 voided on the batch-B side,
this one on the batch-A side — the same three-run artifact, seen from
both sides of one gap). The w64t31 anchor held **−/−/− in both batches**,
so the anchor transition is **ADJUDICATED FLIP=no**.

| cell | batch A (Oct 20 11:37:41–11:38:53, tick 1132 / PR #1408) | batch B (Oct 20 12:06:20–12:08:15, tick 1201) | cross-batch |
|------|------|------|------|
| w64t31 (anchor) | mean(3) **−13,893.9**, signs **−/−/−** (1/3 IQR-clean) | mean(3) **−13,305.3**, signs **−/−/−** (2/3 IQR-clean) | FLIP=**no — adjudicated** (both sign-unanimous) |
| w64t32 (flip cell) | mean(3) **+1,918.6**, signs **+/−/+** (2/3 IQR-clean) | mean(3) **+5,144.2**, signs **+/+/+** (3/3 IQR-clean) | analyzer FLIP=**YES — NON-ADJUDICATED** (batch A non-unanimous) → transition **INCONCLUSIVE** |

ns/dispatch, variant-chunked minus baseline-chunked. All 12 runs `RESULT
verified=true`, runner exit 0. Batch-B IQR: anchor run1 0.0784 **dirty**
(load1 14.97, gap −14,355.5), run2 0.0235 clean (load1 15.00, gap
−11,812.5), run3 0.0438 clean (load1 13.16, gap −13,748.0); flip cell
run1 0.0057 clean (load1 15.99, gap +5,948.2), run2 0.0087 clean (load1
17.48, gap +4,946.3), run3 0.0088 clean (load1 12.43, gap +4,538.1). The
chain rule is IQR ≤ 0.05. Batch B is **5/6 IQR-clean** — a third
consecutive non-supporting datum for the #1396 noise-attribution
hypothesis (below). Anchor probe verdicts `vs-1.0`: `indistinguishable-at-
this-noise` / `above` / `above`; flip cell: `below` on all three (the
first all-`below` flip-cell batch in the series). Absolute magnitudes are
not comparable across batches.

**The flip-cell series gains NO entry this tick.** A voided transition
cannot advance the count, so the series stands exactly as recorded at tick
1117 ("the 19th transition without a flip; one flip in nineteen", PR
#1406). This would-be transition sits at a 27m27s gap — the same rounded
gap as tick 0805's clean 12/12-IQR datum, the series' first repeated gap
value; the gap series is now: 6m52s within-session / 12m52s / 13m51s /
14m59s / 15m21s (tick 1132, voided) / 16m20s / 24m33s / 25m36s /
**27m27s (this tick, voided transition)** / 27m27s (tick 0805) / 29m21s /
30m14s / 70m26s / 124m20s / 318m29s.

**The anchor transition is ADJUDICATED, not an artifact.** Both batches
are sign-unanimous on the anchor (−/−/− and −/−/−), so the rule returns a
clean **FLIP=no**. The anchor's historic − sign holds on both sides of
another cross-tick transition. Caveat on precision, not on sign: batch
A's anchor runs are 1/3 IQR-clean (tick 1132's runs 1–2 at IQR
0.0658/0.0868) and batch B's are 2/3 (run 1 at 0.0784), so both batch
anchor means are partly noisy estimates; the sign itself is unanimous in
all six anchor runs across both batches (the dirtiest runs still read −).

## What this bounds, honestly

- **CROSS-TICK / CROSS-SESSION datum**: gap and session restart remain
  confounded; in-session >=30 min stays INFEASIBLE at the 1800 s budget.
- **Load natural experiment (recorded as an observation).** This datum is
  the series' **third consecutive non-supporting datum** for the #1396
  noise-attribution hypothesis (after ticks 1117's and 1132's): batch B
  ran *heavier* than batch A (load1 12.43–17.48 vs 10.15–15.52) yet
  returned the cleaner batch (5/6 IQR-clean vs 3/6) with the chain's
  lowest flip-cell IQRs, and the batch's heaviest run (load1 17.48) is
  essentially tied for its cleanest flip-cell run (IQR 0.0087 vs 0.0088).
  The direction is again opposite to "heavier load → dirtier runs"; the
  datum neither supports the hypothesis nor adjudicates it (cross-tick
  batches differ in more than load). The load source remains UNATTRIBUTED
  (other sessions' traffic not ruled out); "probe-idle (all sessions)"
  remains UNMEASURED.
- **No protocol deviations this tick.** All six batch-B runs executed on
  the first attempt (`node_modules` symlinked to the shared checkout's at
  worktree creation, before dispatch, per the established convention).
  Runs are internally adjacent by pair (12:06:20/12:06:43,
  12:07:29/12:07:45, 12:07:59/12:08:15). The carried `run-sweep.sh` body
  was machine-checked byte-identical to tick 1132's below `set -e` (only
  `EV=` differing); `analyze-1201.py`'s carry was machine-checked to
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

**Base note.** Batch A ran on `005d48fb` (tick 1132's worktree); batch B
runs on `005d48fb` — the base delta is **empty** (same commit), so the
dispatched computation is identical regardless (pinned probe bytes, staged
fixture bytes, both sha-verified).

**Analyzer carry.** `analyze-1201.py` is carried from `analyze-1132.py`
with only the carry-source line, the batch attribution pair and the
output-filename pair (docstring and code) changed — the `diff` shows
exactly five changed line-pairs (10 changed content lines),
machine-checked. Parsing, the noise rule and the gap label are untouched.
`run-sweep.sh` is carried from the 1132 tick's; everything below `set -e`
is byte-identical except the `EV=` dir line (verified programmatically),
and the header is rewritten only for this tick's series list, staging-rule
status, base note and gap provenance.

## States

- implemented (code + test): nothing in src/test this tick. The diff is
  this evidence dir (PRs #1346/#1390/#1394/#1395/#1396/#1398/#1399/#1400/
  #1402/#1403/#1405/#1406/#1408 shape). **Gate not run** (nothing to gate:
  no src/test namespace, no `run-tests.cljk` change). The suite's base
  state is the one carried by the chain from PR #1388's exact-base run:
  16F/15–17E, red set outside every amu-gpu diff, not green — **not
  re-measured this tick**.
- measured (this document + logs): the 27m27s cross-tick datum above —
  anchor adjudicated FLIP=no, flip-cell transition INCONCLUSIVE (batch-A
  side non-unanimous).
- UNMEASURED: the flip RATE; the #1396 anchor noise attribution (five
  supporting data through tick 1102, three non-supporting data at ticks
  1117/1132/1201, still unadjudicated); in-session >=30 min (INFEASIBLE at
  budget); a probe-idle-gap datum covering ALL sessions; the `:arm` /
  `:unknown` workgroup rows (`:measured? false` stays false).

## Files

- `run-A-*.log` — byte-identical copies of tick 1132's batch B logs (PR
  #1408), sha256: `1eecc031…` `805d6ba4…` `1fb49e14…` (w64t31 pairs 1–3),
  `92764ff2…` `695530ed…` `22573968…` (w64t32 pairs 1–3) — matching the
  shas recorded in tick 1132's README table.
- `run-B-*.log` — this tick's six runs (exit 0, `RESULT verified=true`),
  sha256: `cb61ea62…` `c00aacc2…` `fa0eeaa1…` (w64t31 pairs 1–3),
  `ede4c92e…` `625c58fa…` `21eb1fb5…` (w64t32 pairs 1–3).
- `run-sweep.sh` — carried from the 1132 tick's (body below `set -e`
  identical except `EV=`; byte-identity machine-verified).
- `analyze-1201.py` / `analyze-1201.txt` — the carried analyzer and its
  output.
