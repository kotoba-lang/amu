# crosstick-gap-0736B-w64t32-20261020 — cross-tick sign datum at a 27m27s gap (the chain's shortest cross-tick gap): w64t32 holds +, the anchor holds − (adjudicated, first clean-vs-clean), chain's first 12/12-IQR-clean comparison (tick 20261020-0805, JUN-58)

## The finding this tick

**At a 27m27s cross-tick gap (the chain's shortest cross-tick gap), both
cells held their signs: w64t32 +/+/+ (FLIP=no) and w64t31 anchor −/−/−
(FLIP=no) — in the chain's cleanest cross-batch comparison yet, the first
transition where all 12 runs across both batches are IQR-clean (every
batch×cell block 3/3).** Batch A is the 0736 tick's batch B (PR #1394's
logs, copied here byte-identical as `run-A-*.log`, sha256 below); batch B
ran in THIS tick (a later cron run, a fresh process):

| cell | batch A (Oct 20 07:38:34–07:40:20, tick 0736 / PR #1394) | batch B (Oct 20 08:07:47–08:09:19, tick 0805) | cross-batch |
|------|------|------|------|
| w64t31 (anchor) | mean(3) **−4,042.9**, signs **−/−/−** (3/3 IQR-clean, 3/3 surviving) | mean(3) **−2,951.2**, signs **−/−/−** (3/3 IQR-clean, 3/3 surviving) | FLIP=**no** |
| w64t32 (flip cell) | mean(3) **+788.1**, signs **+/+/+** (3/3 IQR-clean, 2/3 surviving) | mean(3) **+2,363.3**, signs **+/+/+** (3/3 IQR-clean, 3/3 surviving) | FLIP=**no** |

ns/dispatch, variant-chunked minus baseline-chunked; negative = variant
faster. All 12 runs `RESULT verified=true`, runner exit 0.

**The anchor adjudicates again — for the first time since #1384.** The
chain's set-of-signs rule adjudicates only between sign-unanimous batches.
The anchor's adjudicable transitions so far: 2337 (within-session, FLIP=no)
and #1384 (70m26s, FLIP=no). #1390 could not adjudicate (its batch B was
non-unanimous +/−/− — the artifact #1390 reported — which is why #1394
refused to adjudicate its analyzer's anchor FLIP=YES), and #1394's
comparison was not adjudicable either (its A side was #1390's batch). Both
sides here are unanimous AND fully clean (IQR 0.0201–0.0231 in A,
0.0212–0.0323 in B), so this transition adjudicates: **no flip** — the
anchor's third adjudicated transition, third no-flip, and its first
clean-vs-clean one.

**The chain's cleanest cross-batch comparison.** All twelve runs across
both batches pass IQR ≤ 0.05 (0.0145–0.0323 in B) — the chain's first
transition where every batch×cell block is 3/3 IQR-clean (the anchor's
first 3/3-vs-3/3 comparison; w64t32's 3/3-vs-3/3 is the second after
#1384). Batch B additionally passes the floor rule on 6/6 (as did #1384's
and #1394's batch B) at load1 18.24–28.56; the floor rule still excludes
one A-side run (0736's w64t32 run 2, floor/baseline 0.3142 >
1.2×0.2279). Load level alone does not determine batch noise; recorded as
an observation, not a mechanism claim.

## What this bounds, honestly

- **CROSS-TICK / CROSS-SESSION datum**: the two batches are different cron
  runs in different processes, so "gap" and "session restart" remain
  confounded; the in-session >=30 min question stays INFEASIBLE at the
  1800 s run budget (proven at tick 2254, three evidences). The 27m27s gap
  is the chain's shortest cross-tick gap to date (70m26s / 318m29s /
  124m20s precede it) — gap length itself is not a controlled variable.
- **A no-flip bounds nothing against a stochastic flip rate.** The w64t32
  cross-session series is now + (#1369) / − (#1377) / + (#1378) / +/+
  (#1380) / + (#1382) / +/+ (#1383) / + (#1384) / + (#1390) / + (#1394) /
  + (this tick): **one flip in eleven transitions**. The RATE question needs
  more transitions and stays UNANSWERED. This transition is the chain's
  first 12/12-IQR-clean comparison (see above), so it carries the least
  batch noise of any transition so far.
- **Gap provenance — no documented amu-gpu GPU traffic in the window.**
  Between batch A's end (07:40:20) and batch B's start (08:07:47) this
  tick's pre-dispatch work was file copies and sha256 checks only; one
  compile attempt at 08:06:26 was refused *before any device dispatch*
  (setup note below) and dispatched nothing. Like #1390's window, unlike
  #1394's, the window carries no documented amu-gpu GPU traffic. **Other
  sessions' traffic on this host is not ruled out**, so "probe-idle (all
  sessions)" remains UNMEASURED.
- **Absolute magnitudes drift; only the sign is compared.** w64t32 mean(3)
  moved +788.1 → +2,363.3 and w64t31 −4,042.9 → −2,951.2 across batches;
  the protocol's controlled quantity is the sign of the gap, and
  cross-batch magnitude comparison is not claimed.
- No value here is a workgroup-default value; every number above is
  measured on this host (Apple M1 Max / MoltenVK 1.3.357 / glslang
  11:16.6.0, `INFO Apple M1 Max|1.3.357|1024|1 aarch64-macos` self-printed
  by every run) at lanes 2,095,104. Nothing flips `:measured?` in
  `kotoba.compiler.accelerator-targets` — `:arm` and `:unknown` rows stay
  provisional (`:measured? false`), and this diff does not touch that file.

## Protocol and base note

**Probe identity: the chain's pinned bytes, sha256 `3696ca0d…`** (full:
`3696ca0db0e28c5b41fa5c8551df2ae1302deb190e91722408117a06077ef652`), run
as `scripts/gpu-subgroup-reduce-chunksweep-pinned-3696ca0d.cljk` and
re-verified by `run-sweep.sh`'s shasum guard before any run. Every SHAPE
line self-printed `fixture=subgroup-reduce-w64-sum.emitted.glsl
sha256=a25a6931…` — the chain's pinned variant-arm bytes.

**Chain inputs at this base (the PR #1393 staging rule).** The rule says to
run `sh scripts/gpu-sign-chain-stage-fixtures.sh` before dispatching the
pinned probe. That script and its archive live on PR #1393's branch and are
NOT on this base (origin/main `b915f5c6`). At this base `test/fixtures/gpu/`
**already holds the chain's pinned pre-fix bytes** — all four sha256 verified
against the archive README's table before dispatch (w32 `0cf6c406…`, w64
`a25a6931…`, w128 `c7931718…`, w256 `087107f9…`) — so the staging step is a
byte-identity no-op here and the rule's invariant (the probe sees the bytes
every prior datum ran) holds by construction. Once #1393 lands, future
chain worktrees must run the staging script first (their `test/fixtures/gpu/`
will hold the regenerated post-fix bytes).

**Bases differ and the delta is empty.** Batch A ran on origin/main
`a2a86a08`, batch B on `b915f5c6`; `git diff a2a86a08..b915f5c6 -- tools/
src/` is **empty** — zero runtime code delta between the bases (the delta is
ADR/doc/merge traffic only), so the executed dispatch path is identical by
construction.

**Analyzer carry.** `analyze-0805.py` is carried from `analyze-0736.py`
with only the output filename and the docstring changed; the `diff` shows
exactly ten changed lines in five pairs (2, 9, 10, 12, 19 — docstring text
and `out_path`). Parsing, the noise rule and the gap label are untouched.

**Setup note (one pre-dispatch refusal, recorded for the chain).** The very
first batch-B dispatch attempt (08:06:26) was refused *before any device
dispatch*: the fresh worktree had no `node_modules` and the guest compile
failed with `nbb engine must name an existing cli.js file, not a directory:
.../node_modules/nbb/cli.js`. Fixed by symlinking `node_modules` to the
shared checkout's (the same arrangement the prior chain worktrees use); the
partial log was deleted and the run re-dispatched at 08:07:47. No
unverified run entered the dataset: every included log carries `RESULT
verified=true` and `run-sweep.sh` aborts on anything else.

**Protocol deviations: none in the dataset.** All three run-pairs are
adjacent (pair 1 08:07:47/08:08:16, pair 2 08:08:34/08:08:50, pair 3
08:09:05/08:09:19), executed in the scripted rotated order.

## States

- implemented (code + test): nothing in src/test this tick. The diff is one
  pinned probe script + this evidence dir (like PRs #1346/#1390/#1394's
  shape). **Gate not run** (nothing to gate: no src/test namespace, no
  `run-tests.cljk` change). The suite's base state is the one measured on
  PR #1388's exact-base run (`cc2b2362`): 16F/15–17E, red set outside every
  amu-gpu diff, not green.
- measured (this document + logs): the 27m27s cross-tick datum above
  (w64t32 +/+/+ FLIP=no; anchor −/−/− FLIP=no; anchor's third adjudicated
  transition and first clean-vs-clean one; chain's first 12/12-IQR-clean
  cross-batch comparison).
- UNMEASURED: the flip RATE (one flip in eleven transitions; needs more),
  the in-session >=30 min gap (INFEASIBLE at the run budget), a
  probe-idle-gap datum covering ALL sessions (this window had no documented
  amu-gpu traffic but other sessions are unruled), and the `:arm` /
  `:unknown` workgroup rows in `kotoba.compiler.accelerator-targets`
  (`:measured? false` stays false).

## Files

- `run-A-*.log` — byte-identical copies of tick 0736's batch B logs (PR
  #1394), sha256: `36005df1…` `1d7c107d…` `2d8479f5…` (w64t31 pairs 1–3),
  `8e32db5b…` `edfc86c2…` `e900aad4…` (w64t32 pairs 1–3).
- `run-B-*.log` — this tick's six runs (exit 0, `RESULT verified=true`),
  sha256: `09c2b5da…` `1c4744f6…` `83b30270…` (w64t31 pairs 1–3),
  `309440cb…` `05d71926…` `0ea56b9a…` (w64t32 pairs 1–3).
- `run-sweep.sh` — carried from the 0736 tick's with the header (tick
  identity, chain-inputs note, base note, gap provenance) updated; the six
  `run` protocol lines are untouched.
- `analyze-0805.py` / `analyze-0805.txt` — the carried analyzer and its
  output.
