# crosstick-gap-0530B-w64t32-20261020 — cross-tick sign datum at a 124m2s gap: the chain's FIRST 6/6 IQR-clean batch; w64t32 holds +; the anchor reads its historic − cleanly (tick 20261020-0736, JUN-58)

## The finding this tick

**At a 124m2s cross-tick gap (corrected 2026-10-20: measured from the last batch-A run’s END = start + 17.026s; the earlier 124m20s used its start), w64t32 held its sign (+/+/+) but its effect is WITHIN NOISE (distances
from 1.0: 0.0062/0.0109/0.0045, each below its run's IQR), so the w64t32
flip question is UNRESOLVED at this noise -- a sub-IQR effect is not a
result. The w64t31 anchor read its historic − sign. (NOT the chain's
first clean batch: the within-tick batches evidence records 12 IQR-clean
runs; and 5/6 -- not 6/6 -- pass the COMBINED noise rule here) — while the host was busy (load1 25–39).** Batch A is
the 0530 tick's batch B (PR #1390's logs, copied here byte-identical as
`run-A-*.log`, sha256 below); batch B ran in THIS tick (a later cron run, a
fresh process):

| cell | batch A (Oct 20 05:28:17–05:34:14, tick 0530 / PR #1390) | batch B (Oct 20 07:38:34–07:40:20, tick 0736) | cross-batch |
|------|------|------|------|
| w64t31 (anchor) | mean(3) **−1,784.2**, signs +/−/− (1/3 IQR-clean; clean est −4,600.6) | mean(3) **−4,042.9**, signs **−/−/− (3/3 IQR-clean)** | analyzer FLIP=YES — **not adjudicated**, see below |
| w64t32 (flip cell) | mean(3) **+9,237.0**, signs +/+/+ (1/3 IQR-clean; clean est +2,543.0) | mean(3) **+788.1**, signs **+/+/+ (3/3 IQR-clean)** | FLIP=**no** |

ns/dispatch, variant-chunked minus baseline-chunked; negative = variant
faster. All 12 runs `RESULT verified=true`, runner exit 0. NOTE: the GAP
values and signs here come from the PINNED chain probe's marginal-median
subtraction; the parent's live probe has since moved to the median of
paired per-round differences. The two methods can disagree in sign; these
signs are the unpaired kind and are labelled accordingly.

**Why the anchor's FLIP=YES is not a flip finding.** The chain's set-of-signs
rule adjudicates only between sign-unanimous batches. Batch A was
non-unanimous (+/−/−, its lone `+` the batch's worst run at IQR 0.2750, the
artifact PR #1390 already reported), so the comparison **cannot** adjudicate
a transition — same rule, same direction as #1390's INCONCLUSIVE call. What
this datum settles is the anchor's **sign itself**: the chain's first 3/3
clean anchor batch since #1384 reads **−/−/−** (IQR 0.0201–0.0231), matching
the historic anchor sign (#1384 −/−/− at −14,873.7; #1390's lone clean
survivor −4,600.6). #1390's anchor `+` is now doubly a noise artifact.

**Noise state of batch B (corrected).** All six batch-B runs are IQR-clean,
but only 5/6 pass the COMBINED noise rule (IQR ≤ 0.05 **and** floor-share ≤ 1.2x the cell's clean minimum: w64t31
3/3 survive; w64t32 2/3 survive — run 2's floor/baseline 0.3142 exceeds
1.2x0.2279=0.2735, though its IQR 0.0403 passes), at load1 **25.06–39.46**
— higher than 2337's "clean window" (13–19). Load level alone does not
determine batch noise; recorded as an observation, not a mechanism claim.

## Batch-A pair-rotation disclosure

The claimed run-pair rotation does not hold for batch A: the committed
timestamps show run-A-1-w64t32 starts before its supposed adjacent anchor
(the rotation order the protocol names is not what the timestamps show).
Batch A is copied from PR #1390's logs and is recorded here as-is; its
pair-order deviation is disclosed rather than corrected, and the batch-B
'no deviation' statement covers batch B only.

## What this bounds, honestly

- **CROSS-TICK / CROSS-SESSION datum**: the two batches are different cron
  runs in different processes, so "gap" and "session restart" remain
  confounded; the in-session >=30 min question stays INFEASIBLE at the
  1800 s run budget (proven at tick 2254, three evidences).
- **A no-flip bounds nothing against a stochastic flip rate.** The w64t32
  cross-session series is now + (#1369) / − (#1377) / + (#1378) / +/+
  (#1380) / + (#1382) / +/+ (#1383) / + (#1384) / + (#1390) / + (this
  tick): **two flips in ten transitions** (+→− at #1369/#1377, −→+ at #1377/#1378 --
corrected from 'one flip'). The RATE question needs more
  transitions and stays UNANSWERED. This transition is the chain's first
  between two 3/3-IQR-clean w64t32 batches (A was 1/3 clean), so it is
  still weighted by A's noise.
- **Gap provenance — the window is NOT probe-idle.** Between batch A's end
  (05:34:14) and batch B's start (07:38:34) amu-gpu ran real GPU work on
  this host: the post-fix `:subgroup-reduce` EXEC probe (PRs #1391/#1392,
  ticks 0556/0624, ~05:56–06:5x — 14-case device executions) and the chain's
  staged-fixture smoke (PR #1393, tick 0715, ~07:1x). Unlike #1390's window
  this one carries **documented amu-gpu GPU traffic**, recorded here as a
  confound of this datum. Other sessions' traffic is not ruled out.
- **Absolute magnitudes drift; only the sign is compared.** w64t32 mean(3)
  moved +9,237.0 → +788.1 and w64t31 −1,784.2 → −4,042.9 across batches;
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
re-verified by `run-sweep.sh.txt`'s shasum guard before any run. Every SHAPE
line self-printed `fixture=subgroup-reduce-w64-sum.emitted.glsl
sha256=a25a6931…` — the chain's pinned variant-arm bytes.

**Chain inputs at this base (the PR #1393 staging rule).** The rule says to
run `sh scripts/gpu-sign-chain-stage-fixtures.sh` before dispatching the
pinned probe. That script and its archive live on PR #1393's branch and are
NOT on this base (origin/main `a2a86a08`). At this base `test/fixtures/gpu/`
**already holds the chain's pinned pre-fix bytes** — all four sha256 verified
against the archive README's table before dispatch (w32 `0cf6c406…`, w64
`a25a6931…`, w128 `c7931718…`, w256 `087107f9…`) — so the staging step is a
byte-identity no-op here and the rule's invariant (the probe sees the bytes
every prior datum ran) holds by construction. Once #1393 lands, future
chain worktrees must run the staging script first (their `test/fixtures/gpu/`
will hold the regenerated post-fix bytes).

**Bases differ and the delta is empty.** Batch A ran on origin/main
`e8f2ae61`, batch B on `a2a86a08`; `git diff e8f2ae61..a2a86a08 -- tools/
src/` is **empty** — zero runtime code delta between the bases (the delta is
ADR/doc/merge traffic only), so the executed dispatch path is identical by
construction.

**Analyzer carry.** `analyze-0736.py` is carried from `analyze-0530.py`
with only the output filename and the docstring changed; the `diff` shows
exactly five lines (2, 9, 10, 12, 14, 19 — docstring text and
`out_path`). Parsing, the noise rule and the gap label are untouched.

**Protocol deviations: none.** All three run-pairs are adjacent (pair 1
07:38:34/07:38:49, pair 2 07:39:03/07:39:42, pair 3 07:40:02/07:40:20),
executed in the scripted rotated order.

## States

- implemented (code + test): nothing in src/test this tick. The diff is one
  pinned probe script + this evidence dir (like PRs #1346/#1390's shape).
  **Gate not run** (nothing to gate: no src/test namespace, no
  `run-tests.cljk` change). The suite's base state is the one measured on
  PR #1388's exact-base run (`cc2b2362`): 16F/15–17E, red set outside every
  amu-gpu diff, not green.
- measured (this document + logs): the 124m2s cross-tick datum above
  (w64t32 holds +; anchor −/−/− fully clean; first 6/6-IQR-clean batch).
- UNMEASURED: the flip RATE (one more same-sign transition, 1 in 10; needs
  more), the in-session >=30 min gap (INFEASIBLE at the run budget), a
  probe-idle-gap datum (this window carried documented GPU traffic), and
  the `:arm` / `:unknown` workgroup rows in
  `kotoba.compiler.accelerator-targets` (`:measured? false` stays false).

## Files

- `run-A-*.log` — byte-identical copies of tick 0530's batch B logs (PR
  #1390), sha256: `74a39654…` `90a89ca4…` `b008fd3e…` (w64t31 pairs 1–3),
  `b3c7d1fa…` `94a846ef…` `8653167a…` (w64t32 pairs 1–3).
- `run-B-*.log` — this tick's six runs (exit 0, `RESULT verified=true`),
  sha256: `36005df1…` `1d7c107d…` `2d8479f5…` (w64t31 pairs 1–3),
  `8e32db5b…` `edfc86c2…` `e900aad4…` (w64t32 pairs 1–3).
- `run-sweep.sh.txt` — carried from the 0530 tick's with the header (tick
  identity, chain-inputs note, base note, gap provenance) updated; the six
  `run` protocol lines are untouched.
- `analyze-0736.py` / `analyze-0736.txt` — the carried analyzer and its
  output.
