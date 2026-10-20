# crosstick-gap-0006B-w64t32-20261020 — chain's LONGEST gap (318m15s) sign datum (cross-tick): w64t32 holds +; w64t31 anchor non-unanimous under load — anchor flip INCONCLUSIVE (tick 20261020-0530, JUN-58)

## The finding this tick

**At a 318m15s cross-tick gap (the chain's longest; previous max 70m26s), the
w64t32 flip cell held its sign (+/+/+ all-run, no flip), while the w64t31
anchor went sign-non-unanimous for the first time in the chain — and that
anchor "flip" is noise-confounded, NOT adjudicated.** Batch A is the 0006
tick's batch B (PR #1384's logs, copied here byte-identical as
`run-A-*.log`, sha256 below); batch B ran in THIS tick (a later cron run, a
fresh process):

| cell | batch A (Oct 20 00:08:36–00:09:48, tick 0006 / PR #1384) | batch B (Oct 20 05:28:17–05:34:14, tick 0530) | cross-batch |
|------|------|------|------|
| w64t31 (anchor) | mean(3) **−14,873.7**, signs −/−/− (3/3 IQR-clean) | mean(3) **−1,784.2**, signs **+/−/−** (1/3 IQR-clean; clean-run est **−4,600.6**) | analyzer says FLIP=**YES** — see below, **INCONCLUSIVE** |
| w64t32 (flip cell) | mean(3) **+4,604.8**, signs +/+/+ (3/3 IQR-clean) | mean(3) **+9,237.0**, signs +/+/+ (1/3 IQR-clean; clean-run est **+2,543.0**) | FLIP=**no** |

ns/dispatch, variant-chunked minus baseline-chunked; negative = variant
faster. All 12 runs `RESULT verified=true`, runner exit 0.

**Why the anchor's FLIP=YES is not a finding.** The chain's flip protocol
compares sign-unanimous batches. NOTE: the GAP signs are UNPAIRED
  differences of per-arm marginal medians -- the pinned probe persists no
  per-round pairs, so a paired (median-of-differences) sign cannot be
  computed from these logs. The signs are descriptive accordingly. Batch B is the chain's noisiest: 2 of 6
runs survive (4 fail the noise rule: IQR 0.0503-0.5847, worst = w64t32 run 1
at 0.5847; the anchor's single positive
run at IQR **0.2750** is NOT the batch's worst -- 0.5847 (w64t32 run 1) is,
and 0.2750 is mid-pack here, `vs-1.0=indistinguishable-at-this-noise`),
and only one run per cell survives (IQR ≤ 0.05 **and** floor-share ≤ 1.2x
the cell's clean minimum). Both survivors match the historic signs
(anchor −4,600.6, flip cell +2,543.0). The naive all-run mean of the anchor
is dragged to −1,784.2 with a positive run only because of the dirty run.
The analyzer's set-of-signs FLIP rule cannot adjudicate a non-unanimous
batch, so the anchor transition is reported **INCONCLUSIVE**, and the
all-run `+` sign on the anchor is reported as a noise artifact, not a flip.

**Host load is the confound, measured and recorded.** Batch B ran at
load1 **25.2–53.09** (other work on this host, source not investigated)
against batch A's 20.18–23.49 and 2337's 13–19 clean window. This is the
chain's first datum collected under heavy concurrent load; the anchor's
sign fragility is exactly what the noise rule exists to catch.

## What this bounds, honestly

- **CROSS-TICK / CROSS-SESSION datum**: the two batches are different cron
  runs in different processes, so "gap" and "session restart" remain
  confounded; the in-session >=30 min question stays INFEASIBLE at the
  1800 s run budget (proven at tick 2254, three evidences).
- **A no-flip bounds nothing against a stochastic flip rate.** The w64t32
  cross-session series is now + (#1369) / − (#1377) / + (#1378) / +/+
  (#1380) / + (#1382) / +/+ (#1383) / + (#1384) / + (this tick): TWO flips
  in nine transitions (+ to - at #1377, - to + at #1378 -- corrected from
  'one flip'), and this tick adds one same-sign transition at the
  chain's longest gap. The RATE question needs more transitions and stays
  UNANSWERED — and this transition is noise-dirty (1/3 clean runs), so it
  is a weak one.
- **Gap provenance**: no GPU probe traffic is recorded by any amu-gpu
  evidence dir between batch A's end (00:09:48) and batch B's start
  (05:28:17); the intervening ticks 0028/0347/0422/0445 were
  kernel-emission and CPU gate-suite work. **Other sessions' traffic on
  this host is not ruled out**, so the window is NOT claimed probe-idle
  beyond amu-gpu's own records.
- **Protocol deviation (recorded)**: pair 1's runs are 5m57s apart
  (05:28:17 / 05:34:14) instead of adjacent — the first pass's pair-1
  anchor run refused (`COULD-NOT-RUN`, the fresh worktree had no
  `node_modules`; `bin/amu` needs `node_modules/nbb/cli.js`, later wired
  as the chain's symlink to the shared checkout's `node_modules`), the
  partial log (0 RESULT lines) was deleted per the 2337 precedent and
  re-run last via the idempotent runner. Actual execution order:
  t32(1), t32(2), t31(2), t31(3), t32(3), t31(1). The deleted log's only
  content was the refusal line, `date`/`uptime`, and that error message.
- No value here is a workgroup-default value; every number above is
  measured on this host (Apple M1 Max, MoltenVK 1.3.357, glslang
  11:16.6.0) at lanes 2,095,104. Nothing flips `:measured?` in
  `kotoba.compiler.accelerator-targets` — `:arm` and `:unknown` rows stay
  provisional (`:measured? false`), and this diff does not touch that file.

## Protocol and base note

**Probe identity: the chain's pinned bytes, sha256 `3696ca0d…`.** Batch B
ran `scripts/gpu-subgroup-reduce-chunksweep-pinned-3696ca0d.cljk` — a
byte-identical copy of the probe the 2254/2337/0006 batches ran, carried
verbatim (sha256 re-checked by `run-sweep.sh.txt` before any run) because
origin/main's `scripts/test-gpu-subgroup-reduce-chunksweep.cljk` has since
**advanced** (`3c965429` gap signs from paired round samples, `55da4342`
COULD-NOT-RUN, `25089b82` bound the init dispatch grid; `66742df7…` at
this base) and computes GAP differently (paired round differences vs the
chain's marginal-median gap). The pinned copy lives under `scripts/`
because the probe resolves its root as *script dir / `..`*. Fixtures
identical to the chain (w64 `a25a6931…`, self-printed by every SHAPE
line). `analyze-0530.py` is carried from `analyze-0006.py` with only the
output filename and docstring changed (diffed: parsing, the noise rule and
the gap label are untouched).

**Bases differ and the delta is accounted for.** Batch A ran on
origin/main `068ec02d`, batch B on `e8f2ae61`. The runtime code delta
between them is only `tools/kexe_gpu_vulkan.c` (KGPU_MAX_KEPT 4 → 8 kept
command-buffer slots; this probe keeps slots 0..2, so the submitted
command buffers and the executed dispatch path are **identical**); the
rest of the delta is `src` runner_* compiler namespaces the probe does not
consult, plus test/docs/scripts. Absolute ns/dispatch values are
comparable only as an observation; the sign comparison is the controlled
quantity.

## States

- implemented (code + test): nothing in src/test this tick. The diff is
  one pinned probe script + this evidence dir (like PR #1346's shape).
  **Gate not run** (nothing to gate: no src/test namespace, no
  `run-tests.cljk` change). The suite's base state is the one recorded on
  PRs #1386–#1388: 16F/15–17E at base, red set outside every amu-gpu diff,
  not green.
- measured (this document + logs): the 318m15s cross-tick datum above
  (w64t32 holds +; w64t31 anchor INCONCLUSIVE under load).
- UNMEASURED: the flip RATE (one more, weak, same-sign transition; needs
  more), a clean long-gap datum (this one is load-confounded), the
  in-session >=30 min gap (INFEASIBLE at the run budget), and the `:arm` /
  `:unknown` workgroup rows in `kotoba.compiler.accelerator-targets`
  (`:measured? false` stays false).

## Files

- `run-A-*.log` — byte-identical copies of tick 0006's batch B logs
  (sha256: `19d0e8cd…`, `ba8842b2…`, `b1629362…`, `38e202ae…`, `2c5071cf…`,
  `cf6e854f…` for A-1-w64t31 … A-3-w64t32 in the order the analyzer reads
  them; full hashes in the PR).
- `run-B-*.log` — this tick's six runs (exit 0, `RESULT verified=true`).
- `run-sweep.sh.txt` — carried from the 0006 tick's with the probe path (the
  pinned copy + its sha256 guard) and header text updated; the six `run`
  protocol lines are untouched.
- `analyze-0530.py` / `analyze-0530.txt` — the carried analyzer and its
  output.
