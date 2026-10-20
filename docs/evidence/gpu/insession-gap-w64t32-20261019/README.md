# insession-gap-w64t32-20261019 — batch A COMPLETE, batch B NOT RUN (tick 20261019-2254, JUN-58)

## The finding this tick: the >=30-min in-tick design is INFEASIBLE on this platform

The 2221 tick designed the strictly-inside-tick two-batch sign probe with a
>=30 min probe-idle gap (protocol designed at tick 2254 (the referenced design directory was never committed; the protocol is stated inline below)).
**That design cannot fit this platform's agent run budget of 1800 s**, and
this tick verified it from three independent tool outputs:

1. `agent.log`: every tick logs `Run budget wrap-up notice injected
   (budget=1800s, elapsed=...)` shortly before it ends (e.g. 22:39:26 for
   the 22:15 tick).
2. `cron/executions.db`: the longest tick of this job's 64+ runs lasted
   30.4 min (2026-10-19 21:00:11--21:30:36); no run has ever exceeded it.
3. This tick received the platform notice `Run time budget nearly
   exhausted` while holding the gap, ~13 min after batch A ended.

A >=30 min gap plus two ~2 min batches plus setup plus analysis plus the
PR exceeds 1800 s even with zero slack. The strict "can the w64t32 sign
flip between two batches >=30 min apart inside ONE tick" question
therefore **cannot be answered as designed**; it must be re-posed (e.g.
flip-rate bounds across ticks, or an explicitly cross-session protocol).
This tick attempted the largest in-session variant that could fit
(see `run-sweep.sh.txt` header); the budget ran out during the gap.

## Batch A (COMPLETE, 6/6 `RESULT verified=true`, runner exit 0)

Run window 22:56--22:58 JST 2026-10-19; probe and fixtures byte-identical
to the #1369/#1377/#1378/#1380 chain (probe sha256 `3696ca0d...`,
w64 fixture `a25a6931...`, w32 `0cf6c406...`, w128 `c7931718...`, w256
`087107f9...`, as self-printed by every SHAPE line). lanes 2,095,104;
cell order rotated per run-pair; fresh kbb process per run.
(ns/dispatch; negative = variant faster)

| cell | run1 | run2 | run3 | mean(3) | signs |
|------|------|------|------|---------|-------|
| w64t31 (anchor) | -12,792.0 | -13,541.0 | -14,587.9 | **-13,640.3** | -/-/- |
| w64t32 (flip cell) | +4,971.7 | +6,434.6 | +4,710.0 | **+5,372.1** | +/+/+ |

Noise (chain rule IQR <= 0.05): w64t32 is 3/3 IQR-clean (0.0104/0.0166/
0.0094); the anchor's run 2 is IQR-dirty (iqr=0.1250,
`vs-1.0=indistinguishable-at-this-noise`) -- the anchor's clean est is
runs 1+3 only. Host load was high and falling during batch A
(load1 53.5 -> 24.2).

**Batch A alone is NOT a flip result** -- it is one batch. What it does
add: the w64t32 sign at 22:56 JST is **+** (loss), extending the
identical-shape cross-session series to + (#1369) / - (#1377) / +
(#1378) / +/+ (#1380) / **+ (this tick, batch A)**.

## Batch B (NOT RUN)

The gap hold reached >=13 min probe-idle (batch A ended 22:58; no
chunksweep ran after) when the run-budget notice arrived. No batch B was
started. The within-session flip question at ANY gap remains
**UNANSWERED**. The runner (`run-sweep.sh.txt B`) is idempotent and will not
overwrite the batch-A logs, but a batch B run in a LATER cron session is
cross-session evidence, not the in-session answer -- it must be labeled so.

## Next-tick handoff

- The in-session question needs a NEW design that fits 1800 s: the
  maximum feasible in-session gap is roughly 8--10 min (setup + 2
  batches + analysis + PR already cost ~15 min of the budget). A flip at
  such a gap would still bound the timescale; a no-flip would not.
- Alternatively pick a backlog row that is not gap-bound (backlog 4:
  JUN-57/59/60 hardware-free design slices).
- Unlanded chain content (probe + 4 sha-pinned fixtures) is carried
  byte-identically on this branch; `bot/amu-gpu-20261019-2221` carries
  the aborted strict-probe's partial evidence.
