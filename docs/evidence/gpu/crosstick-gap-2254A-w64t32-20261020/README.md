# crosstick-gap-2254A-w64t32-20261020 — first >=30-MIN GAP sign datum (cross-tick): no flip at 70m13s (tick 20261020-0006, JUN-58)

## The finding this tick

**The w64t32 flip-cell sign does NOT flip across a 70m13s cross-tick gap (corrected 2026-10-20: measured from the last batch-A run’s END = start + 12.974s; the earlier 70m26s used its start).**
This is the chain's first datum at a >=30 min gap: the 2221/2254 ticks'
in-tick holds died at this platform's 1800 s run budget (proven at 2254,
three evidences) and the 2337 tick bounded within-session stability at
6m52s. The >=30 min question is only reachable across ticks, so this probe
pairs the 2254 tick's batch A (PR #1382's logs, copied here byte-identical)
with a batch B run in THIS tick — a later cron run, a fresh process. Both
cells are sign-unanimous in both batches (6/6 runs per cell):

| cell | batch A (Oct 19 22:56:23–22:58:10, tick 2254 / PR #1382) | batch B (Oct 20 00:08:36–00:09:48, tick 0006) | cross-batch |
|------|------|------|------|
| w64t31 (anchor) | mean(3) **-13,640.3**, signs -/-/- (clean est -13,690.0, 2 survivors) | mean(3) **-14,873.7**, signs -/-/- (3/3 IQR-clean) | FLIP=**no** |
| w64t32 (flip cell) | mean(3) **+5,372.1**, signs +/+/+ (3/3 IQR-clean) | mean(3) **+4,604.8**, signs +/+/+ (3/3 IQR-clean) | FLIP=**no** |

Cross-tick gap batchA-end → batchB-start: **70m13s** (last batch-A run end = its start + 12.974s). ns/dispatch,
variant-chunked minus baseline-chunked; negative = variant faster. All 12
runs `RESULT verified=true`, runner exit 0.

## What this bounds, honestly

- This is a **CROSS-TICK / CROSS-SESSION datum**: the two batches are
  different cron runs in different processes, so "gap" and "session
  restart" are confounded and cannot be separated here. It does **not**
  answer "would the sign have flipped over 70 min inside one session" —
  that design remains INFEASIBLE at the 1800 s run budget.
- A **no-flip bounds nothing against a stochastic flip rate**. The chain's
  identical-shape cross-session series is + (#1369) / - (#1377) / +
  (#1378) / +/+ (#1380) / + (#1382): flips DO occur between sessions, two
  in five transitions (the + / - / + / + / + / + series has two sign
  changes across its five adjacent transitions). This datum adds one same-sign transition at a known
  >=30-min gap (#+1382 → this tick) to that series; the rate question needs
  more transitions and stays UNANSWERED.
- The gap is **NOT probe-idle**: the 2337 tick ran its 12 probe runs at
  23:37–23:48 inside this window. This is sign stability across a
  >=30-min wall-clock cross-tick window with intervening probe traffic.
- No value here is a workgroup-default value; every number above is
  measured on this host (Apple M1 Max, MoltenVK 1.3.357) at lanes
  2,095,104. Nothing flips `:measured?` in
  kotoba.compiler.accelerator-targets — that requires the per-vendor
  workgroup sweep (backlog 3), not a sign probe.

## Protocol and base note

Byte-identical probe (sha256 `3696ca0d…`, verified on both bases) and
fixtures (w64 `a25a6931…` as self-printed by every SHAPE line) to the
#1369/#1377/#1378/#1380/#1382 chain; lanes 2,095,104; 3 runs per cell per
batch; cell order rotated per run-pair (t31,t32 / t32,t31 / t31,t32); fresh
kbb process per run; `date; uptime` recorded per run. `run-sweep.sh.txt B` is
idempotent (a run whose log exists is skipped). The six batch-A logs are
byte-identical copies of the 2254 tick's (`run-A-*.log` sha256:
1c0c0197…, 2495b11f…, 67a63834…, 35de036f…, 9ef537be…, 9bb2105a…).
`analyze-0006.py` is carried from `analyze-2337.py` with only the output
filename, docstring, and the gap LABEL text changed (this gap crosses a
tick boundary, so the label "probe-idle gap" would be wrong) — parsing and
the noise rule (IQR <= 0.05 and floor share <= 1.2x the cell's IQR-clean
minimum floor share) are untouched. Batch B ran at load1 20.2–23.5, 6/6
IQR-clean.

**Bases differ and the delta is accounted for.** Batch A ran on
origin/main `35b45ddf`, batch B on `068ec02d`. The runtime code delta
between them is only `tools/kexe_gpu_vulkan.c` (KEXE_GPU_BARRIER_TRACKED —
`getenv`-gated, default OFF, **unset in both runs**, so the executed
dispatch path is identical); everything else in the delta is test/docs/
deps. Absolute ns/dispatch values are therefore comparable only as an
observation; the sign comparison is the controlled quantity.

## States

- implemented (code + test): nothing this tick — evidence-only diff, no
  src/test .cljk namespace touched, gate not run (nothing to gate).
- measured (this document + logs): the 70m26s cross-tick no-flip datum
  above.
- UNMEASURED: the flip RATE (one more same-sign transition added; the
  question needs more cross-session transitions), the in-session >=30 min
  gap (INFEASIBLE at the run budget), per-vendor workgroup rows in
  kotoba.compiler.accelerator-targets (`:measured? false` stays false).

## Next-tick handoff

- The cross-tick protocol now works end-to-end (runner + analyzer carried
  from 2337, one copied endpoint). If the rate question stays priority:
  each tick can add one transition — either another cross-tick pair (this
  tick's batch B becomes the next pair's endpoint A) or a full in-session
  two-batch probe as a repeat-series session. Count sign agreements over
  transitions; do not pool gaps below 30 min with cross-tick gaps without
  labeling.
- Backlog 4 (JUN-57/59/60 hardware-free design slices) remains open and is
  not gap-bound.

Worktree base: origin/main `068ec02d`. node_modules symlinked to the
shared checkout's (nbb 1.5.212-cljk.1, same version the chain ran).
