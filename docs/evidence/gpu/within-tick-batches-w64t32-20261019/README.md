# within-tick-batches-w64t32-20261019 — two-batch sign probe (tick 20261019-2106, JUN-58)

**Question.** The cross-session series at the identical shape (w64t32,
wg=1023, lanes 2,095,104) is **+, -, +** across three sessions (PR #1369
+, #1377 -, #1378 +) while within every session the 3 runs are sign-unanimous
(9/9). The observed flip window is <= 31 minutes (the #1377 batch ran
20:06-20:10 JST, the #1378 batch started 20:38 JST with the opposite sign).
So "session" may be no coarser than a wall-clock gap of tens of minutes. Can
the w64t32 sign flip between two batches separated by a >= 30 minute idle
gap? If yes, the flip timescale is <= 30 min and "session" is a
batch-resolution artifact; if no, the flip timescale is > 30 min and session
is a longer-timescale state.

**Method.** Byte-identical probe and fixtures to the #1369/#1377/#1378 chain
(probe sha256 `3696ca0db0e28c5b41fa5c8551df2ae1302deb190e91722408117a06077ef652`,
w64 fixture sha256 `a25a69317b5c5a956279ccc37a5089adb489104a28ed89460b8928889b096254`,
w32 `0cf6c4069c5ae06835c03ef65e5a6e12a605d7d2518bd81f965510b603814722`, as
self-printed by every SHAPE line). Two cells (w64t31 anchor, w64t32 flip
cell) at lanes 2,095,104; 3 runs per cell per batch; cell order rotated per
run-pair (t31,t32 / t32,t31 / t31,t32); fresh kbb process per run;
`date; uptime` recorded per run. Same noise rule as the chain
(analyze-2000.py / analyze-2030.py: IQR <= 0.05 + floor-share survival).

**Protocol deviation (honest).** The design was "two batches inside ONE tick,
separated by a >= 30 min idle gap". Batch A ran 21:09:56-21:11:18 JST in the
tick-20261019-2106 session, which then ENDED before the gap elapsed (the gap
cannot be held inside one session: foreground waits are capped at 600 s).
Batch B ran in the FOLLOWING cron session at 21:48:46-21:50:08 JST, so the
"inside one tick" containment is NOT satisfied; the wall-clock gap is real
(37 min 28 s from batch A completion to batch B start) and exceeds the 30 min
design. The gap was probe-idle (this bot ran no chunksweep in between) but
the host was NOT idle: batch B ran under load1 15-17 with another agent's
`kbb run-tests.cljk` running concurrently (batch A ran under load1 7-9).
Because the gap also straddles a session boundary, a flip here would have
been confounded with the boundary; a no-flip is interpretable but cannot
bound a stochastic flip rate.

**All 12 runs `RESULT verified=true`, all 12 IQR-clean, 3/3 survivors per
cell per batch.** (ns/dispatch; negative = variant faster)

| batch | cell | run1 | run2 | run3 | est (mean 3) | signs |
|-------|------|------|------|------|--------------|-------|
| A | w64t31 | -18,271.5 | -15,114.3 | -14,087.9 | **-15,824.6** | -/-/- |
| A | w64t32 | +5,325.2 | +5,310.5 | +5,444.3 | **+5,360.0** | +/+/+ |
| B | w64t31 | -17,189.5 | -15,006.8 | -14,986.3 | **-15,727.5** | -/-/- |
| B | w64t32 | +5,607.4 | +4,772.5 | +6,124.0 | **+5,501.3** | +/+/+ |

All 12 runs' ratio streams are fully on one side of 1.0 (`vs-1.0=above` /
`below`, no straddling): both signs are resolved at this session's noise.

## Findings

1. **No flip across the 37.5-minute gap.** w64t32 is +/+/+ and +/+/+ in the
   two batches (+5,360.0 / +5,501.3); the w64t31 anchor is -/-/- and -/-/-.
   The sign does not reset at every session boundary: the #1377 flip across a
   ~31-minute gap is not a deterministic per-boundary event. The flip
   timescale remains **UNRESOLVED** — this single no-flip observation bounds
   nothing against a stochastic flip rate; the strict "can it flip inside one
   tick at <= 30 min" question is **still open** (see deviation above).
2. **Within-batch sign unanimity holds for w64t32 in every batch ever run at
   this shape: 15/15 runs** (3 runs x #1369/#1377/#1378 sessions + 3 runs x
   2 batches here). The instability sits at >= batch resolution, never at run
   resolution.
3. **The w64t31 anchor magnitude drifted again**: -15.8k now vs -9.9k /
   -10.5k / -12.8k in the three prior sessions (this session ~23-60% deeper),
   while agreeing tightly inside the tick (A/B differ by 0.6%). Anchor
   magnitude is session-dependent — 4 samples now.
4. Batch A and batch B agree within 2.6% (w64t32) and 0.6% (w64t31) despite
   a 2x load difference (7-9 vs 15-17): at this shape the gap sign and rough
   magnitude are robust to that load range; the load sensitivity of the
   absolute timing is UNMEASURED.

## Cross-session series at the identical shape (w64t32, wg=1023, lanes 2,095,104)

| session | est | sign |
|---------|-----|------|
| #1369 (tick-1716 chain) | +4,775.4 | + |
| #1377 (tick-2000) | -7,546.9 | - |
| #1378 (tick-2030) | +5,425.5 | + |
| tick-2106 batch A | +5,360.0 | + |
| tick-2106 batch B | +5,501.3 | + |

w64t31 anchor: -10,533.9 (#1369) / -9,896.8 (#1377) / -12,848.6 (#1378) /
-15,824.6 (A) / -15,727.5 (B) — sign -/-/-/-/- across all observations.

## What is left

- The original single-tick question needs a session that can hold the >= 30
  min gap internally (or a tick runner with a longer foreground budget), or
  more (batch-pair, gap) samples to estimate a flip rate per hour instead of
  chasing individual flips.
- All numbers here are hardware measurements on this host (Apple M1 Max,
  MoltenVK 1.3.357) of the subgroup-reduce chunk-sweep probe only. The
  workgroup defaults in `kotoba.compiler.accelerator-targets` remain
  provisional (`:measured? false`) and are not touched by this probe.

`gate.log` is the canonical suite run
(`kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)" run-tests.cljk`);
`gate-vs-2030.txt` is `norm_gate.py` FAIL/ERROR-set comparison against the
tick-2030 gate. This diff adds no source or test namespaces. The gate was
taken at base 35b45ddf: 311 tests / 4,942 passed / 16 failed / 15 errors,
FAIL/ERROR set **SETS-AND-COUNTS-IDENTICAL** to tick-2030's documented base
red. Note: the base bump 3594390e..35b45ddf (PR #1374, `kotoba.compiler.project`)
does not change the totals because `kotoba.compiler.project-test` is not in
`run-tests.cljk`'s namespace lists — that namespace is outside this gate's
coverage, and outside this diff.
