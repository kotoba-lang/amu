# crosstick-gap-0805B-w64t32-20261020 — cross-tick sign datum at a 29m21s gap (tick 20261020-0840, JUN-58): flip cell holds +/+/+ (noise-labeled), anchor analyzer FLIP=YES is NON-ADJUDICATED (batch B non-unanimous under load)

## The finding this tick

**At a 29m21s cross-tick gap, the w64t32 flip cell held +/+/+ in both
batches (FLIP=no) but batch B is NOISE-LABELED (only 2/6 runs IQR-clean,
host load1 up to 80.07); the w64t31 anchor's analyzer FLIP=YES is a
NON-ADJUDICATED artifact — batch B's anchor is non-unanimous (+/−/+) under
load, and the chain's set-of-signs rule adjudicates only between
sign-unanimous batches (the #1390 pattern repeating). This transition is
INCONCLUSIVE for adjudication.**

| cell | batch A (Oct 20 08:07:47–08:09:19, tick 0805 / PR #1395) | batch B (Oct 20 08:38:40–08:50:25, tick 0840) | cross-batch |
|------|------|------|------|
| w64t31 (anchor) | mean(3) **−2,951.2**, signs **−/−/−** (3/3 IQR-clean) | mean(3) **+68,969.7**, signs **+/−/+** (1/3 IQR-clean) | analyzer FLIP=**YES — NOT adjudicable** (batch B non-unanimous) |
| w64t32 (flip cell) | mean(3) **+2,363.3**, signs **+/+/+** (3/3 IQR-clean) | mean(3) **+19,873.4**, signs **+/+/+** (1/3 IQR-clean) | FLIP=**no** (noise-labeled) |

ns/dispatch, variant-chunked minus baseline-chunked. All 12 runs `RESULT
verified=true`, runner exit 0. The batch-B IQR-fails are extreme (0.2685 /
0.6167 / 0.6777 / 0.7519 — the chain rule is IQR ≤ 0.05) at load1
26.17–80.07; only run2 of each cell is IQR-clean (0.0181 / 0.0163), and
both clean runs carry the historic signs (anchor −460.0, flip cell
+1,974.6). Absolute magnitudes are not comparable across batches.

**The flip-cell series gains one more no-flip entry (noise-labeled): one
flip in twelve transitions.** The RATE question stays UNANSWERED. This
datum is the chain's NOISIEST transition to date (2/6 IQR-clean in batch B,
vs 12/12 at #1395) and adds the least adjudication weight of any series
entry; a re-run under lower load would be a new datum, not a replacement.

## What this bounds, honestly

- **CROSS-TICK / CROSS-SESSION datum**: gap and session restart remain
  confounded; in-session >=30 min stays INFEASIBLE at the 1800 s budget.
  29m21s slots between the chain's 27m27s (#1395) and 70m26s (#1384).
- **The anchor flip is NOT a measured flip.** The analyzer's raw set
  comparison prints FLIP=YES; the chain's adjudication rule voids it because
  batch B's anchor is non-unanimous under load (same as #1394's refusal of
  #1390's artifact). Reported as INCONCLUSIVE, not as a flip.
- **Load confound.** Batch B ran while this host carried other work (load1
  26–80; run-B-3-w64t32 at 80.07). "Probe-idle (all sessions)" remains
  UNMEASURED. The gap window itself (08:09:19–08:38:40) carried no
  documented amu-gpu GPU dispatch (this tick's pre-dispatch work: git
  reads/fetch, worktree creation, file copies, sha256 checks).
- **Protocol deviation (recorded):** the first sweep process was killed by
  the tool's 420 s foreground timeout mid-run-B-2-w64t32 (08:44–08:45);
  that partial log had no `RESULT` line, was deleted unverified, and the
  run was re-executed in a fresh background sweep (08:47:36). One aborted
  device dispatch occurred between pair 1 and pairs 2–3; pairs 1, 2, 3 are
  each internally adjacent (08:38:40/08:41:18, 08:47:36/08:47:53,
  08:48:08/08:50:25). No unverified run entered the dataset.
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

**Bases differ; the executed path is unchanged.** Batch A ran on
`b915f5c6`, batch B on `9b084efe`. `git diff b915f5c6..9b084efe -- tools/`
is EMPTY; the only src/ delta is ONE NEW self-contained namespace
(`src/kotoba/compiler/runner_cap_dispatch.cljk`, PR #1389) referenced by
nothing in src/, tools/ or the probe (grep: zero references outside its own
file and tests).

**Analyzer carry.** `analyze-0840.py` is carried from `analyze-0805.py`
with only the output filename and the docstring changed (the `diff` shows
exactly ten changed lines in five pairs). Parsing, the noise rule and the
gap label are untouched.

## States

- implemented (code + test): nothing in src/test this tick. The diff is one
  pinned probe script + this evidence dir (PRs #1346/#1390/#1394/#1395
  shape). **Gate not run** (nothing to gate: no src/test namespace, no
  `run-tests.cljk` change). The suite's base state is the one measured on
  PR #1388's exact-base run (`cc2b2362`): 16F/15–17E, red set outside every
  amu-gpu diff, not green.
- measured (this document + logs): the 29m21s cross-tick datum above.
- UNMEASURED: the flip RATE; the anchor transition at this gap
  (INCONCLUSIVE); in-session >=30 min (INFEASIBLE at budget); a
  probe-idle-gap datum covering ALL sessions; the `:arm` / `:unknown`
  workgroup rows (`:measured? false` stays false).

## Files

- `run-A-*.log` — byte-identical copies of tick 0805's batch B logs (PR
  #1395), sha256: `09c2b5da…` `1c4744f6…` `83b30270…` (w64t31 pairs 1–3),
  `309440cb…` `05d71926…` `0ea56b9a…` (w64t32 pairs 1–3).
- `run-B-*.log` — this tick's six runs (exit 0, `RESULT verified=true`),
  sha256: `2b08a87e…` `2fcae30a…` `389562b3…` (w64t31 pairs 1–3),
  `e3a510be…` `80bf3fc4…` `95e718ff…` (w64t32 pairs 1–3).
- `run-sweep.sh` — carried from the 0805 tick's with the header updated;
  the six `run` protocol lines are untouched (only the `EV=` dir line
  differs below the header).
- `analyze-0840.py` / `analyze-0840.txt` — the carried analyzer and its
  output.
