# crosstick-gap-0840B-w64t32-20261020 — cross-tick sign datum at a 30m14s gap (tick 20261020-0916, JUN-58): flip cell holds +/+/+ (13th transition, no flip); anchor reads historic − sign-unanimous; analyzer FLIP=YES on the anchor is NON-ADJUDICATED (batch A non-unanimous)

## The finding this tick

**At a 30m14s cross-tick gap (the chain's third-shortest), the w64t32 flip
cell held +/+/+ in both batches (FLIP=no) — the series' 13th transition
without a flip (one flip in thirteen) — and the w64t31 anchor's batch B is
sign-unanimous −/−/− (2/3 IQR-clean) with both clean runs re-reading the
anchor's historic − sign; the analyzer's raw FLIP=YES on the anchor is a
NON-ADJUDICATED artifact because batch A's anchor is non-unanimous
(+/−/+ under load, the #1390 pattern repeating). The anchor transition is
INCONCLUSIVE for adjudication; the flip-cell transition adjudicates as
no-flip, noise-labeled on batch A's side.**

| cell | batch A (Oct 20 08:38:40–08:50:25, tick 0840 / PR #1396) | batch B (Oct 20 09:20:39–09:24:18, tick 0916) | cross-batch |
|------|------|------|------|
| w64t31 (anchor) | mean(3) **+68,969.7**, signs **+/−/+** (1/3 IQR-clean — the 0840 load-plagued batch) | mean(3) **−13,534.5**, signs **−/−/−** (2/3 IQR-clean) | analyzer FLIP=**YES — NOT adjudicable** (batch A non-unanimous) |
| w64t32 (flip cell) | mean(3) **+19,873.4**, signs **+/+/+** (1/3 IQR-clean) | mean(3) **+6,491.8**, signs **+/+/+** (2/3 IQR-clean) | FLIP=**no** (noise-labeled on batch A) |

ns/dispatch, variant-chunked minus baseline-chunked. All 12 runs `RESULT
verified=true`, runner exit 0. Batch-B IQR: anchor 0.3558 fails (run1,
load1 48.83), runs 2–3 clean (0.0326 / 0.0255, load1 42.62 / 32.15,
gap −14,958.0 / −15,172.9 — the historic anchor sign, re-read cleanly);
flip cell 0.4109 fails (run2, load1 52.17), runs 1 and 3 clean (0.0270 /
0.0105, load1 68.81 / 25.96, gap +6,006.8 / +4,874.0). The chain rule is
IQR ≤ 0.05. Absolute magnitudes are not comparable across batches.

**The flip-cell series gains one more no-flip entry (noise-labeled): one
flip in thirteen transitions.** The RATE question stays UNANSWERED. Batch
B is the chain's cleanest batch since #1395's 12/12 (4/6 IQR-clean vs
#1396's 2/6), and — unlike #1396 — both cells are sign-unanimous in batch
B, so this datum would have been fully adjudicable had batch A been clean.

**The anchor's − is recovered, the 0840 anchor's + is not corroborated.**
#1396's batch-B anchor (+/−/+, only its − run IQR-clean at −460.0) was the
noisiest anchor reading in the chain; this tick's sign-unanimous −/−/−
with two clean runs (−14,958.0 / −15,172.9, matching the historic anchors
−2,951.2 at #1395 and −4,042.9 at #1394) supports the reading that the
#1396 anchor's + runs were load noise, not a sign change. This is a
NOISE-ATTRIBUTION HYPOTHESIS with one supporting datum, not an
adjudication: the chain's rule voids the #1396→0916 anchor comparison
itself, and no pair of sign-unanimous anchor batches straddles the #1396
window.

## What this bounds, honestly

- **CROSS-TICK / CROSS-SESSION datum**: gap and session restart remain
  confounded; in-session >=30 min stays INFEASIBLE at the 1800 s budget.
  30m14s slots between the chain's 29m21s (#1396) and 70m26s (#1384).
- **The anchor FLIP=YES is NOT a measured flip.** The analyzer's raw set
  comparison prints FLIP=YES (batch A's set {+,−} vs batch B's {−}); the
  chain's adjudication rule voids it because batch A's anchor is
  non-unanimous (the same rule as #1394's refusal of #1390's artifact). Reported as INCONCLUSIVE, not as a flip.
- **Load confound.** Batch B ran while this host carried other work (load1
  25.96–68.81; run-B-1-w64t32 at 68.81). "Probe-idle (all sessions)"
  remains UNMEASURED. The gap window itself (08:50:25–09:20:39) carried no
  amu-gpu GPU dispatch (this tick's pre-dispatch work: git reads/fetch,
  worktree creation, file copies, sha256 checks, one aborted pre-dispatch
  compile — see the deviation below).
- **Protocol deviation (recorded):** the first batch-B attempt aborted
  BEFORE any device dispatch — `amu compile` refused the chunksweep guest
  because the fresh worktree had no `node_modules` (nbb engine missing;
  `COULD-NOT-RUN` line, no `RESULT`). The unverified log was deleted and
  the run re-executed after creating the `node_modules` symlink to the
  shared checkout's (the tick 0840 worktree's convention). Nothing from
  the aborted attempt entered the dataset; the six logged runs are the
  whole of batch B. Runs are internally adjacent by pair (09:20:39/09:22:23,
  09:23:05/09:23:36, 09:23:58/09:24:18).
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

**Chain inputs at this base (the PR #1393 staging rule).** #1393 is still
OPEN; its staging script is not on this base (origin/main `9b084efe`).
`test/fixtures/gpu/` holds the chain's pinned pre-fix bytes — all four
sha256 verified before dispatch (w32 `0cf6c406…`, w64 `a25a6931…`, w128
`c7931718…`, w256 `087107f9…`) — so the staging step is a byte-identity
no-op here. Once #1393 lands, future chain worktrees must run the staging
script first.

**Base note: the chain's first same-base cross-tick pair.** Batch A ran on
`9b084efe` and batch B runs on the same `9b084efe` (the shared checkout had
not advanced at worktree creation). The base delta is exactly empty — no
executed-path analysis is needed this time.

**Analyzer carry.** `analyze-0916.py` is carried from `analyze-0840.py`
with only the output filename and the docstring changed (the `diff` shows
exactly ten changed lines in five pairs). Parsing, the noise rule and the
gap label are untouched.

## States

- implemented (code + test): nothing in src/test this tick. The diff is one
  pinned probe script + this evidence dir (PRs #1346/#1390/#1394/#1395/#1396
  shape). **Gate not run** (nothing to gate: no src/test namespace, no
  `run-tests.cljk` change). The suite's base state is the one measured on
  PR #1388's exact-base run (`cc2b2362`): 16F/15–17E, red set outside every
  amu-gpu diff, not green.
- measured (this document + logs): the 30m14s cross-tick datum above.
- UNMEASURED: the flip RATE; the anchor transition at this gap
  (INCONCLUSIVE); the #1396 anchor +/−/+ noise attribution (one supporting
  datum, not adjudicated); in-session >=30 min (INFEASIBLE at budget); a
  probe-idle-gap datum covering ALL sessions; the `:arm` / `:unknown`
  workgroup rows (`:measured? false` stays false).

## Files

- `run-A-*.log` — byte-identical copies of tick 0840's batch B logs (PR
  #1396), sha256: `2b08a87e…` `2fcae30a…` `389562b3…` (w64t31 pairs 1–3),
  `e3a510be…` `80bf3fc4…` `95e718ff…` (w64t32 pairs 1–3).
- `run-B-*.log` — this tick's six runs (exit 0, `RESULT verified=true`),
  sha256: `9631aa5b…` `80aa3eab…` `e1b4611a…` (w64t31 pairs 1–3),
  `b273c795…` `736edc90…` `52f2c37f…` (w64t32 pairs 1–3).
- `run-sweep.sh` — carried from the 0840 tick's with the header updated;
  the six `run` protocol lines are untouched (only the `EV=` dir line
  differs below the header).
- `analyze-0916.py` / `analyze-0916.txt` — the carried analyzer and its
  output.
