# crosstick-gap-1047B-w64t32-20261020 — cross-tick sign datum at a 14m59s gap (tick 20261020-1102, JUN-58): chain's second-shortest cross-tick gap; flip cell holds +/+/+ (18th transition, no flip); anchor adjudicates FLIP=no with both batches sign-unanimous; batch B 6/6 IQR-clean

## The finding this tick

**At a 14m59s cross-tick gap — the chain's second-shortest recorded
cross-tick gap (shortest remains 12m52s at tick 1047, next 16m20s at tick
1001) — both cells adjudicate FLIP=no with both batches sign-unanimous:
the w64t32 flip cell held +/+/+ in both batches (18th transition without
a flip; the series is now one flip in eighteen, and the RATE question
stays UNANSWERED), and the w64t31 anchor held −/−/− in both batches, so
the anchor transition is ADJUDICATED no-flip. Every IQR-clean anchor run
on both sides reads the historic − (batch A 2/3 clean, −11,128.9 /
−3,725.6; batch B 3/3 clean, −11,167.0 / −8,321.3 / −12,133.8). Batch B
ran at load1 11.75–15.1 and returned 6/6 IQR-clean.**

| cell | batch A (Oct 20 10:49:57–10:51:10, tick 1047 / PR #1403) | batch B (Oct 20 11:06:09–11:07:19, tick 1102) | cross-batch |
|------|------|------|------|
| w64t31 (anchor) | mean(3) **−9,044.6**, signs **−/−/−** (2/3 IQR-clean) | mean(3) **−10,540.7**, signs **−/−/−** (3/3 IQR-clean) | FLIP=**no — adjudicated** (both sign-unanimous) |
| w64t32 (flip cell) | mean(3) **+4,718.8**, signs **+/+/+** (3/3 IQR-clean) | mean(3) **+4,442.4**, signs **+/+/+** (3/3 IQR-clean) | FLIP=**no** (adjudicable, both sign-unanimous) |

ns/dispatch, variant-chunked minus baseline-chunked. All 12 runs `RESULT
verified=true`, runner exit 0. Batch-B IQR: anchor run1 0.0295 clean
(load1 15.1, gap −11,167.0), run2 0.0402 clean (load1 13.7, gap
−8,321.3), run3 0.0282 clean (load1 12.81, gap −12,133.8); flip cell run1
0.0158 clean (load1 14.9, gap +4,670.9), run2 0.0095 clean (load1 14.74,
gap +5,141.6), run3 0.0095 clean (load1 11.75, gap +3,514.6). The chain
rule is IQR ≤ 0.05. Batch B is **6/6 IQR-clean**. Anchor probe verdicts
`vs-1.0`: `indistinguishable-at-this-noise` / `above` / `above`; flip
cell: `indistinguishable-at-this-noise` / `below` / `below`. Absolute
magnitudes are not comparable across batches.

**The flip-cell series gains its 18th no-flip entry: one flip in eighteen
transitions.** The RATE question stays UNANSWERED. This transition sits
at 14m59s — the chain's second-shortest cross-tick gap, between the
12m52s (tick 1047) and 16m20s (tick 1001) entries. Cross-tick series now:
6m52s within-session / 12m52s / 14m59s / 16m20s / 24m33s / 25m36s /
27m27s / 29m21s / 30m14s / 70m26s / 124m20s / 318m29s.

**The anchor transition is ADJUDICATED, not an artifact.** Both batches
are sign-unanimous on the anchor, so the chain's adjudication rule returns
a clean **FLIP=no** (no non-unanimous artifact to void). The anchor's
IQR-clean runs on both sides read − (batch A −11,128.9 / −3,725.6;
batch B −11,167.0 / −8,321.3 / −12,133.8). The anchor's historic − sign
holds on both sides of a thirteenth cross-tick transition.

## What this bounds, honestly

- **CROSS-TICK / CROSS-SESSION datum**: gap and session restart remain
  confounded; in-session >=30 min stays INFEASIBLE at the 1800 s budget.
  14m59s is the chain's second-shortest cross-tick gap to date.
- **Load natural experiment (recorded as an observation).** Within this
  datum, the higher-load batch is again the noisier one: batch A (load1
  14.07–17.82, tick 1047's runs) 5/6 IQR-clean, its single dirty run at
  the batch's highest load (17.82); batch B (load1 11.75–15.1) 6/6
  IQR-clean. Same probe bytes, same staged fixture bytes (both
  sha-attested), same base commit. This is the #1396 noise-attribution
  hypothesis's **fifth supporting datum** (after PR #1398, ticks 0949,
  1033, 1047) and it agrees with the pattern's direction at a new load
  band; **it does not adjudicate the hypothesis** (cross-tick batches
  differ in more than load). The load source remains UNATTRIBUTED (other
  sessions' traffic not ruled out); "probe-idle (all sessions)" remains
  UNMEASURED. The gap window itself (10:51:10–11:06:09) carried no
  documented amu-gpu GPU dispatch (the 1047 tick's post-dispatch work —
  analysis, README, commit, push, PR #1403 — and this tick's
  pre-dispatch work: git fetch, worktree creation, batch-A copies and
  sha256 checks, script writes, the fixture staging run).
- **No protocol deviations this tick.** All six batch-B runs executed on
  the first attempt (`node_modules` symlinked to the shared checkout's
  before dispatch, per the established convention). Runs are internally
  adjacent by pair (11:06:09/11:06:24, 11:06:37/11:06:51,
  11:07:05/11:07:19). The carried `run-sweep.sh` body was machine-checked
  byte-identical to tick 1047's below `set -e` (only `EV=` differing)
  **before** dispatch; that check caught one transcription escape drift
  (a literal tab in the `RESULT` grep pattern had become backslash-t in
  the first write), which was fixed and re-verified before any run
  executed — the dispatched script bytes are the chain's.
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

**Base note.** Batch A ran on `005d48fb` (tick 1047's worktree); batch B
runs on `005d48fb` — the base delta is **empty** (same commit), so the
dispatched computation is identical regardless (pinned probe bytes, staged
fixture bytes, both sha-verified).

**Analyzer carry.** `analyze-1102.py` is carried from `analyze-1047.py`
with only the output filename and the docstring changed (the `diff` shows
exactly four changed line-pairs: the carry-source line, the batch
attribution pair, and the output-filename pair in docstring and code).
Parsing, the noise rule and the gap label are untouched. `run-sweep.sh` is
carried from the 1047 tick's; everything below `set -e` is byte-identical
except the `EV=` dir line (verified programmatically, see above), and the
header is rewritten only for this tick's series list, staging-rule status,
base note and gap provenance.

## States

- implemented (code + test): nothing in src/test this tick. The diff is
  this evidence dir (PRs #1346/#1390/#1394/#1395/#1396/#1398/#1399/#1400/
  #1402/#1403 shape). **Gate not run** (nothing to gate: no src/test
  namespace, no `run-tests.cljk` change). The suite's base state is the
  one measured on PR #1388's exact-base run (`cc2b2362`): 16F/15–17E, red
  set outside every amu-gpu diff, not green.
- measured (this document + logs): the 14m59s cross-tick datum above.
- UNMEASURED: the flip RATE; the #1396 anchor noise attribution (five
  supporting data, still unadjudicated); in-session >=30 min (INFEASIBLE
  at budget); a probe-idle-gap datum covering ALL sessions; the `:arm` /
  `:unknown` workgroup rows (`:measured? false` stays false).

## Files

- `run-A-*.log` — byte-identical copies of tick 1047's batch B logs (PR
  #1403), sha256: `f68c5260…` `1fc61b9d…` `082686bb…` (w64t31 pairs 1–3),
  `019c9a1d…` `29b1ed43…` `5d1b7696…` (w64t32 pairs 1–3) — matching the
  shas recorded in tick 1047's README table.
- `run-B-*.log` — this tick's six runs (exit 0, `RESULT verified=true`),
  sha256: `685a937d…` `dbc13dfb…` `903198b4…` (w64t31 pairs 1–3),
  `895739c2…` `a62c6154…` `20b12157…` (w64t32 pairs 1–3).
- `run-sweep.sh` — carried from the 1047 tick's (protocol section identical
  except `EV=`; byte-identity machine-verified).
- `analyze-1102.py` / `analyze-1102.txt` — the carried analyzer and its
  output.
