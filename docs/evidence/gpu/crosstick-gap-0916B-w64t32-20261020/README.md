# crosstick-gap-0916B-w64t32-20261020 — cross-tick sign datum at a 24m33s gap (tick 20261020-0949, JUN-58): both cells sign-unanimous on both sides, both cross-batch comparisons adjudicate FLIP=no (14th transition, no flip); flip cell 3/3 IQR-clean at the chain's lowest loads; anchor re-reads historic − a second batch running

## The finding this tick

**At a 24m33s cross-tick gap (the chain's shortest to date), both cells are
sign-unanimous in both batches and both cross-batch comparisons adjudicate
FLIP=no with no NON-ADJUDICATED artifact: the w64t32 flip cell held +/+/+
vs +/+/+ (batch B 3/3 IQR-clean — the chain's tightest flip-cell IQRs yet,
0.0065–0.0102, at the chain's lowest load window, load1 11.12–17.40) and
the w64t31 anchor held −/−/− vs −/−/− (both clean runs in batch B re-read
the historic anchor sign). This is the series' 14th transition without a
flip — one flip in fourteen — and the first datum since #1395 where the
anchor comparison is adjudicable and reads no-flip.**

| cell | batch A (Oct 20 09:20:39–09:24:18, tick 0916 / PR #1398) | batch B (Oct 20 09:48:51–09:50:02, tick 0949) | cross-batch |
|------|------|------|------|
| w64t31 (anchor) | mean(3) **−13,534.5**, signs **−/−/−** (2/3 IQR-clean) | mean(3) **−14,604.5**, signs **−/−/−** (2/3 IQR-clean; run3 marginal fail, IQR 0.0540 vs the 0.05 rule) | FLIP=**no** — adjudicable (both sign-unanimous); noise-labeled on both sides |
| w64t32 (flip cell) | mean(3) **+6,491.8**, signs **+/+/+** (2/3 IQR-clean, 1/3 surviving the floor-share rule) | mean(3) **+4,435.9**, signs **+/+/+** (**3/3 IQR-clean, 3/3 surviving**) | FLIP=**no** — adjudicable (both sign-unanimous); noise-labeled on batch A |

ns/dispatch, variant-chunked minus baseline-chunked. All 12 runs `RESULT
verified=true`, runner exit 0. Batch-B IQR: anchor 0.0540 fails (run3,
load1 11.48, gap −16,628.9 — a marginal fail 0.004 over the rule), runs 1–2
clean (0.0276 / 0.0335, load1 17.40 / 12.65, gap −12,225.6 / −14,959.0 —
the historic anchor sign, re-read cleanly a second batch running); flip
cell all three clean (0.0065 / 0.0102 / 0.0068, load1 17.24 / 14.84 /
11.12, gap +4,980.5 / +4,767.6 / +3,559.6). The chain rule is IQR ≤ 0.05.
Absolute magnitudes are not comparable across batches.

**The flip-cell series gains its 14th no-flip entry: one flip in fourteen
transitions.** The RATE question stays UNANSWERED. Unlike #1396 and #1398,
this transition needs no NON-ADJUDICATED refusal: every analyzer raw
verdict this tick is also the chain-rule verdict. The noise labels are
bookkeeping (batch A carries #1398's documented load-noisy run pair; batch
B's only fail is the anchor's marginal run3), not voids.

**The anchor's − holds a second consecutive sign-unanimous batch** (batch B
clean runs −12,225.6 / −14,959.0, matching the historic anchors −14,958.0 /
−15,172.9 at #1398, −2,951.2 at #1395, −4,042.9 at #1394). The
#1396-anchor noise-attribution hypothesis gains a SECOND supporting datum;
it remains NOT adjudicated — the chain's rule voids the comparisons that
touch the #1396 window (the adjacent datum #1398's batch A is the
non-unanimous +/−/+ batch itself). Note, recorded from the logs without
upgrading the state: sign-unanimous anchor batches now exist on both sides
of the #1396 window (#1396's batch A = #1395's batch B is −/−/− 3/3
IQR-clean, PR #1396's own table; #1398's batch B and this batch B are
−/−/− after it), but the chain's within-datum rule compares only each
datum's own A/B pair, and no single datum's pair spans the window.

## What this bounds, honestly

- **CROSS-TICK / CROSS-SESSION datum**: gap and session restart remain
  confounded; in-session >=30 min stays INFEASIBLE at the 1800 s budget.
  24m33s is the chain's SHORTEST cross-tick gap so far (previous shortest
  27m27s at #1395), extending the no-flip coverage downward in gap length.
- **No analyzer artifact this tick.** Both raw FLIP verdicts equal the
  chain-rule verdicts (FLIP=no / FLIP=no). This is the chain's first
  all-adjudicable transition since #1395 (12/12 IQR-clean); this one is
  9/12 IQR-clean and fully sign-unanimous.
- **Load confound (weakest in the chain).** Batch B ran at load1
  11.12–17.40 — the lowest-load batch the chain has recorded — and returned
  the tightest flip-cell IQRs (0.0065–0.0102). "Probe-idle (all sessions)"
  remains UNMEASURED. The gap window itself (09:24:18–09:48:51) carried no
  amu-gpu GPU dispatch (this tick's pre-dispatch work: git reads/fetch,
  worktree creation, the fixture staging run, file copies, sha256 checks).
- **No protocol deviations this tick.** All six batch-B runs executed on
  the first attempt (the #1398 node_modules failure was pre-empted by
  symlinking node_modules to the shared checkout's before dispatch, per
  that tick's recorded convention). Runs are internally adjacent by pair
  (09:48:51/09:49:08, 09:49:21/09:49:34, 09:49:48/09:50:02).
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
no-op).** This worktree's base is origin/main `2f04a37e` — the chain's
FIRST base on #1393's merge. The checkout's `test/fixtures/gpu/` held the
regenerated post-fix bytes, so `sh
scripts/gpu-sign-chain-stage-fixtures.sh.txt` was run from this worktree
root before dispatch, restoring the chain's pinned pre-fix fixture bytes
(all four sha256 verified: w32 `0cf6c406…`, w64 `a25a6931…`, w128
`c7931718…`, w256 `087107f9…`). The rule's invariant — the probe sees the
bytes every prior datum ran — held by that staging step. After dispatch the
tracked fixtures were restored (`git checkout -- test/fixtures/gpu/`) so
this diff stays evidence-only; the executed bytes are attested by the
SHAPE-line sha256 in every log.

**Base note: the chain's first cross-tick pair with a non-empty base
delta.** Batch A ran on `9b084efe` (tick 0916's worktree); batch B runs on
`2f04a37e` (delta = PRs #1391/#1393: exec-postfix partial-matrix fail +
INFO recording, the fixed subgroup-reduce emitter + test, fixture
regeneration + `.sh` driver renames). The dispatched computation is
byte-identical regardless — the probe bytes are the chain's pinned copy and
the fixture bytes were staged to the chain's pre-fix pins (both
sha-verified) — so the delta is recorded as a chain note, not analyzed as
an executed-path change.

**Analyzer carry.** `analyze-0949.py` is carried from `analyze-0916.py`
with only the output filename and the docstring changed (the `diff` shows
exactly ten changed lines in five pairs). Parsing, the noise rule and the
gap label are untouched. `run-sweep.sh` is carried from the 0916 tick's;
everything below `set -e` is byte-identical except the `EV=` dir line
(verified by `diff`), and the header is rewritten only for this tick's
series list, staging-rule status, base note and gap provenance.

## States

- implemented (code + test): nothing in src/test this tick. The diff is
  this evidence dir (PRs #1346/#1390/#1394/#1395/#1396/#1398 shape).
  **Gate not run** (nothing to gate: no src/test namespace, no
  `run-tests.cljk` change). The suite's base state is the one measured on
  PR #1388's exact-base run (`cc2b2362`): 16F/15–17E, red set outside every
  amu-gpu diff, not green.
- measured (this document + logs): the 24m33s cross-tick datum above.
- UNMEASURED: the flip RATE; the #1396 anchor +/−/+ noise attribution (two
  supporting data now, still unadjudicated); in-session >=30 min
  (INFEASIBLE at budget); a probe-idle-gap datum covering ALL sessions; the
  `:arm` / `:unknown` workgroup rows (`:measured? false` stays false).

## Files

- `run-A-*.log` — byte-identical copies of tick 0916's batch B logs (PR
  #1398), sha256: `9631aa5b…` `80aa3eab…` `e1b4611a…` (w64t31 pairs 1–3),
  `b273c795…` `736edc90…` `52f2c37f…` (w64t32 pairs 1–3).
- `run-B-*.log` — this tick's six runs (exit 0, `RESULT verified=true`),
  sha256: `6873f010…` `cf302d96…` `0ef0ec36…` (w64t31 pairs 1–3),
  `e0250a62…` `bf60e57a…` `5f94ea6b…` (w64t32 pairs 1–3).
- `run-sweep.sh` — carried from the 0916 tick's (protocol section identical
  except `EV=`).
- `analyze-0949.py` / `analyze-0949.txt` — the carried analyzer and its
  output.
