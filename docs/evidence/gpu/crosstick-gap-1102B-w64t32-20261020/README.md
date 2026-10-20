# crosstick-gap-1102B-w64t32-20261020 — cross-tick sign datum at a 13m51s gap (tick 20261020-1117, JUN-58): chain's second-shortest cross-tick gap; flip cell holds +/+/+ (19th transition, no flip); anchor adjudicates FLIP=no with both batches sign-unanimous; batch B 6/6 IQR-clean at chain-heavier loads

## The finding this tick

**At a 13m51s cross-tick gap — the chain's second-shortest recorded
cross-tick gap (shortest remains 12m52s at tick 1047; this datum sits
between it and the 14m59s entry at tick 1102) — both cells adjudicate
FLIP=no with both batches sign-unanimous: the w64t32 flip cell held +/+/+
in both batches (19th transition without a flip; the series is now one flip
in nineteen, and the RATE question stays UNANSWERED), and the w64t31
anchor held −/−/− in both batches, so the anchor transition is ADJUDICATED
no-flip. Every IQR-clean anchor run on both sides reads the historic −
(batch A 3/3 clean, −11,167.0 / −8,321.3 / −12,133.8; batch B 3/3 clean,
−12,371.1 / −9,003.9 / −10,932.6). Batch B ran at load1 14.1–19.01 —
heavier than batch A's 11.75–15.1 — and still returned 6/6 IQR-clean.**

| cell | batch A (Oct 20 11:06:09–11:07:19, tick 1102 / PR #1405) | batch B (Oct 20 11:21:10–11:22:20, tick 1117) | cross-batch |
|------|------|------|------|
| w64t31 (anchor) | mean(3) **−10,540.7**, signs **−/−/−** (3/3 IQR-clean) | mean(3) **−10,769.2**, signs **−/−/−** (3/3 IQR-clean) | FLIP=**no — adjudicated** (both sign-unanimous) |
| w64t32 (flip cell) | mean(3) **+4,442.4**, signs **+/+/+** (3/3 IQR-clean) | mean(3) **+4,600.9**, signs **+/+/+** (3/3 IQR-clean) | FLIP=**no** (adjudicable, both sign-unanimous) |

ns/dispatch, variant-chunked minus baseline-chunked. All 12 runs `RESULT
verified=true`, runner exit 0. Batch-B IQR: anchor run1 0.0286 clean
(load1 14.1, gap −12,371.1), run2 0.0341 clean (load1 17.25, gap
−9,003.9), run3 0.0250 clean (load1 16.65, gap −10,932.6); flip cell run1
0.0131 clean (load1 14.67, gap +4,734.4), run2 0.0102 clean (load1 15.55,
gap +4,122.1), run3 0.0091 clean (load1 19.01, gap +4,946.3). The chain
rule is IQR ≤ 0.05. Batch B is **6/6 IQR-clean**. Anchor probe verdicts
`vs-1.0`: `above` / `indistinguishable-at-this-noise` / `above`; flip
cell: `indistinguishable-at-this-noise` / `below` / `below`. Absolute
magnitudes are not comparable across batches.

**The flip-cell series gains its 19th no-flip entry: one flip in nineteen
transitions.** The RATE question stays UNANSWERED. This transition sits at
13m51s — the chain's second-shortest cross-tick gap, between the 12m52s
(tick 1047) and 14m59s (tick 1102) entries. Cross-tick series now:
6m52s within-session / 12m52s / 13m51s / 14m59s / 16m20s / 24m33s /
25m36s / 27m27s / 29m21s / 30m14s / 70m26s / 124m20s / 318m29s.

**The anchor transition is ADJUDICATED, not an artifact.** Both batches
are sign-unanimous on the anchor, so the chain's adjudication rule returns
a clean **FLIP=no** (no non-unanimous artifact to void). The anchor's
IQR-clean runs on both sides read − (batch A −11,167.0 / −8,321.3 /
−12,133.8; batch B −12,371.1 / −9,003.9 / −10,932.6). The anchor's
historic − sign holds on both sides of a fourteenth cross-tick transition.

## What this bounds, honestly

- **CROSS-TICK / CROSS-SESSION datum**: gap and session restart remain
  confounded; in-session >=30 min stays INFEASIBLE at the 1800 s budget.
  13m51s is the chain's second-shortest cross-tick gap to date.
- **Load natural experiment (recorded as an observation).** This datum
  does **not** reproduce the #1396 noise-attribution hypothesis's pattern
  direction: batch B ran heavier (load1 14.67–19.01 vs batch A's
  11.75–15.1) yet is 6/6 IQR-clean with marginally **lower** mean IQR in
  both cells (anchor 0.0292 vs 0.0326; flip cell 0.0108 vs 0.0116), and
  the batch's heaviest run (load1 19.01) is its cleanest flip-cell run
  (IQR 0.0091). This is the chain's load-natural-experiment series' **first
  non-supporting datum** after the five supporting data recorded through
  tick 1102 (PR #1398, ticks 0949/1033/1047/1102); it neither supports the
  hypothesis nor adjudicates it (cross-tick batches differ in more than
  load; both batches here are fully clean, so there is no dirty run to
  attribute). The load source remains UNATTRIBUTED (other sessions'
  traffic not ruled out); "probe-idle (all sessions)" remains UNMEASURED.
  The gap window itself (11:07:19–11:21:10) carried no documented amu-gpu
  GPU dispatch (the 1102 tick's post-dispatch work — analysis, README,
  commit, push, PR #1405 — and this tick's pre-dispatch work: git fetch,
  worktree creation, batch-A copies and sha256 checks, script writes, the
  fixture staging run).
- **No protocol deviations this tick.** All six batch-B runs executed on
  the first attempt (`node_modules` symlinked to the shared checkout's
  before dispatch, per the established convention). Runs are internally
  adjacent by pair (11:21:10/11:21:25, 11:21:38/11:21:52,
  11:22:06/11:22:20). The carried `run-sweep.sh` body was machine-checked
  byte-identical to tick 1102's below `set -e` (only `EV=` differing)
  **before** dispatch; `analyze-1117.py`'s carry was machine-checked to
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

**Base note.** Batch A ran on `005d48fb` (tick 1102's worktree); batch B
runs on `005d48fb` — the base delta is **empty** (same commit), so the
dispatched computation is identical regardless (pinned probe bytes, staged
fixture bytes, both sha-verified).

**Analyzer carry.** `analyze-1117.py` is carried from `analyze-1102.py`
with only the carry-source line, the batch attribution pair and the
output-filename pair (docstring and code) changed — the `diff` shows
exactly five changed line-pairs (10 diff lines), machine-checked. Parsing,
the noise rule and the gap label are untouched. `run-sweep.sh` is carried
from the 1102 tick's; everything below `set -e` is byte-identical except
the `EV=` dir line (verified programmatically, see above), and the header
is rewritten only for this tick's series list, staging-rule status, base
note and gap provenance.

## States

- implemented (code + test): nothing in src/test this tick. The diff is
  this evidence dir (PRs #1346/#1390/#1394/#1395/#1396/#1398/#1399/#1400/
  #1402/#1403/#1405 shape). **Gate not run** (nothing to gate: no src/test
  namespace, no `run-tests.cljk` change). The suite's base state is the
  one carried by the chain from PR #1388's exact-base run: 16F/15–17E, red
  set outside every amu-gpu diff, not green — **not re-measured this
  tick**.
- measured (this document + logs): the 13m51s cross-tick datum above.
- UNMEASURED: the flip RATE; the #1396 anchor noise attribution (five
  supporting data through tick 1102, one non-supporting datum this tick,
  still unadjudicated); in-session >=30 min (INFEASIBLE at budget); a
  probe-idle-gap datum covering ALL sessions; the `:arm` / `:unknown`
  workgroup rows (`:measured? false` stays false).

## Files

- `run-A-*.log` — byte-identical copies of tick 1102's batch B logs (PR
  #1405), sha256: `685a937d…` `dbc13dfb…` `903198b4…` (w64t31 pairs 1–3),
  `895739c2…` `a62c6154…` `20b12157…` (w64t32 pairs 1–3) — matching the
  shas recorded in tick 1102's README table.
- `run-B-*.log` — this tick's six runs (exit 0, `RESULT verified=true`),
  sha256: `cd4561ec…` `9cd0b75d…` `1888f95e…` (w64t31 pairs 1–3),
  `7691c712…` `887f6831…` `c5cbed95…` (w64t32 pairs 1–3).
- `run-sweep.sh` — carried from the 1102 tick's (protocol section identical
  except `EV=`; byte-identity machine-verified).
- `analyze-1117.py` / `analyze-1117.txt` — the carried analyzer and its
  output.
