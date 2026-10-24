# insession-gap6m-w64t32-20261019 — first WITHIN-SESSION two-batch sign datum: no flip at a 6m7s gap (tick 20261019-2337, JUN-58)

## The finding this tick

**The w64t32 flip-cell sign does NOT flip across a 6m7s probe-idle gap (corrected 2026-10-20: measured from the last batch-A run’s END = start + 44.030s; the earlier 6m52s used its start)
inside one cron session.** This is the first completed two-batch sign probe
of the chain: every earlier session (#1369/#1377/#1378/#1380/#1382) ran a
single ~1.5 min batch, and the 2221/2254 ticks' two-batch attempts died
during their gap hold at this platform's 1800 s run budget. Both cells are
sign-unanimous across the gap (6/6 runs per cell):

| cell | batch A (23:37:38–23:39:25) | batch B (23:46:17–23:48:13) | cross-batch |
|------|------|------|------|
| w64t31 (anchor) | mean(3) **-8,472.3**, signs -/-/- (clean est -12,145.5, 1 survivor) | mean(3) **-14,090.8**, signs -/-/- (3/3 IQR-clean, est -14,090.8) | FLIP=**no** |
| w64t32 (flip cell) | mean(3) **+8,366.5**, signs +/+/+ (clean est +4,344.7, 1 survivor) | mean(3) **+5,038.8**, signs +/+/+ (3/3 IQR-clean, est +5,038.8) | FLIP=**no** |

Probe-idle gap batchA-end → batchB-start: **6m7s** (the last batch-A run’s end = 23:40:09.030, its start + 44.030s), both batches inside
ONE cron session (this tick). ns/dispatch, variant-chunked minus
baseline-chunked; negative = variant faster. All 12 runs
`RESULT verified=true`, runner exit 0, runner skip-list idempotent.

## What this bounds, honestly

- A **no-flip bounds nothing against a stochastic flip rate** (the chain's
  identical-shape cross-session series is + (#1369) / - (#1377) / + (#1378)
  / +/+ (#1380) / + (#1382), so flips do occur between sessions). What this
  adds is the first datum that the sign is **stable within one session
  across a multi-minute gap**: whatever the flip mechanism, a ~7 min
  in-session wait alone did not trigger it here.
- The **>=30 min in-tick question remains UNANSWERED and is INFEASIBLE as
  designed** on this platform (proven at tick 2254 from three evidences:
  agent.log budget=1800s notices, executions.db longest tick ever 30.4
  min, budget notice arriving mid-hold). The maximum feasible in-session
  gap after setup + two batches + analysis + PR is ~8–10 min; this probe
  took 6m52s to keep the wrap-up inside the budget with margin (2221 and
  2254 both died during their holds).
- No value here is a workgroup-default value; every number above is
  measured on this host (Apple M1 Max, MoltenVK 1.3.357) at lanes
  2,095,104. Nothing flips `:measured?` in
  kotoba.compiler.accelerator-targets — that requires the per-vendor
  workgroup sweep (backlog 3), not a sign probe.

## Noise rule (chain rule carried from analyze-2221/2254.py)

IQR <= 0.05 and floor share <= 1.2x the cell's IQR-clean minimum floor
share. Batch A ran under falling but high host load (load1 22.8→36.7):
2 of its 6 runs are IQR-dirty (w64t31 run 3; w64t32 run 3); the two run-1 samples (IQR 0.0420 / 0.0257, within the 0.05 limit) are IQR-CLEAN and excluded only by the floor-share test, each
cell leaving 1 survivor. Batch B ran at load1 13.2–19.0: **all 6 runs
IQR-clean, all 6 survive** — batch B's estimates are the clean ones and
they are in line with the chain's batch values (#1382 batch A: anchor
-13,640.3 clean-est / w64t32 +5,372.1), so nothing suggests the base's
KEXE_GPU_BARRIER_TRACKED merge (dispatch barriers via driver hazard
tracking) shifted these gaps (observation, not a controlled comparison).

## Protocol

Byte-identical probe (sha256 `3696ca0d…`) and fixtures (w64 `a25a6931…`,
w32 `0cf6c406…`, w128 `c7931718…`, w256 `087107f9…`, as self-printed by
every SHAPE line) to the #1369/#1377/#1378/#1380/#1382 chain; lanes
2,095,104; 3 runs per cell per batch; cell order rotated per run-pair
(t31,t32 / t32,t31 / t31,t32); fresh kbb process per run; `date; uptime`
recorded per run. `run-sweep.sh.txt A|B` is idempotent (a run whose log exists
is skipped; one batch-B run killed mid-flight by the tool-call time cap was
deleted and re-run, see commit message). `analyze-2337.py` is carried from
`analyze-2254.py` with only the output filename, docstring, and a
timestamp-parse fix (inherited `stamp()` mis-parsed the `date` line; latent
in 2221/2254 because their missing batch B made the script exit before
reaching it) — the noise rule itself is untouched.

Worktree base: origin/main `3b4ea5ea` (merges KEXE_GPU_BARRIER_TRACKED,
after the chain's base). node_modules symlinked to the shared checkout's
(nbb 1.5.212-cljk.1, same version the chain ran).

## States

- implemented (code + test): nothing this tick — evidence-only diff, no
  src/test .cljk namespace touched, gate not run (nothing to gate).
- measured (this document + logs): the 6m52s within-session no-flip datum
  above.
- UNMEASURED: flip timescale at >=30 min (infeasible in-tick; needs a
  cross-tick protocol), per-vendor workgroup rows in
  kotoba.compiler.accelerator-targets (`:measured? false` stays false).

## Next-tick handoff

- If the flip-timescale question stays priority: a cross-tick protocol
  (batch A in one tick, batch B in a later tick, explicitly labeled
  cross-session) is the only way to reach a >=30 min gap; 2254's batch A
  logs already exist as one endpoint. Alternatively bound a flip RATE
  statistically: repeat this 6m52s in-session probe across sessions and
  count sign agreement.
- Backlog 4 (JUN-57/59/60 hardware-free design slices) remains open and is
  not gap-bound.

CORRECTION (2026-10-24, later tick): the blanket workgroup-row claim in
this record -- every/any row of kotoba.compiler.accelerator-targets
:measured? false / provisional -- is FALSE as written. ADR-0358
(2026-10-19, uB5G scoping amendment 2026-10-22) measured four of the six
rows (:nvidia, :apple, :intel, :amd, each scoped to its one
:measured-device name fragment); only :arm and :unknown remain
:measured? false. The claim's oldest standing source was the
accelerator-targets ns docstring, corrected 2026-10-24. Runtime state
and the full census of this claim's surface:
docs/evidence/gpu/workgroup-prose-rootcause-20261024.txt. Everything
else in this record -- its numbers, its "no row moved" claims -- stands
unchanged.
