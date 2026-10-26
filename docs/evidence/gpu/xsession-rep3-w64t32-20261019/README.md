# xsession-rep3-w64t32-20261019 — third-session replication (tick 20261019-2030, JUN-58)

**Question.** PR #1377 measured that the chain's only sign flip — w64t32 loss
at lanes 2,095,104 (#1369 session) — did NOT reproduce in its session (3/3
negative at the identical shape) and concluded "the loss does not reproduce
across sessions". A third independent session adds one more sample: does
w64t32 come back negative (=> #1369 is the outlier session) or flip back
positive (=> the sign is unstable at even coarser resolution)?

**Method.** Byte-identical probe and fixtures to the #1369/#1377 chain
(shasum-verified against tick-20261019-2000 and tick-20261019-1716
worktrees): probe sha256 `3696ca0db0e28c5b41fa5c8551df2ae1302deb190e91722408117a06077ef652`,
w64 fixture sha256 `a25a69317b5c5a956279ccc37a5089adb489104a28ed89460b8928889b096254`
(as self-printed by every SHAPE line). Same five cells, same lanes
2,095,104, 3 cycles order-rotated (forward/reversed/rotated), fresh kbb
process per cell, `date; uptime` recorded per run. Same noise rule as
analyze-2000.py (IQR <= 0.05 + floor-share survival). All 15 runs
`RESULT verified=true`, all 15 IQR-clean, 3/3 survivors per cell.

**This session (clean-run est, ns/dispatch, negative = variant faster):**

| cell | run1 | run2 | run3 | est | signs |
|------|-------|-------|-------|-------|-------|
| w32t24 | -18,556.6 | -16,288.1 | -16,403.3 | **-17,082.7** | -/-/- |
| w32t31 | -26,059.6 | -26,277.3 | -25,673.8 | **-26,003.6** | -/-/- |
| w32t32 | -29,301.8 | -28,935.5 | -28,709.0 | **-28,982.1** | -/-/- |
| w64t31 | -12,576.2 | -14,020.5 | -11,949.2 | **-12,848.6** | -/-/- |
| w64t32 | +5,717.8 | +4,572.3 | +5,986.3 | **+5,425.5** | +/+/+ |

w64t32's three runs are `vs-1.0=below` (ratio stream fully below 1.0, not
straddling): the loss verdict is resolved at this session's noise.

**Cross-session series at the identical shape (w64t32, wg=1023, lanes=2,095,104):**

| session | runs | est | sign |
|---------|------|-----|------|
| #1369 (tick-1716 chain) | +4,397.5 / +4,644.5 / +5,284.2 | +4,775.4 (mean 3) | + |
| #1377 (tick-2000) | -8,128.9 / -7,036.1 / -7,475.6 | -7,546.9 | - |
| this (tick-2030) | +5,717.8 / +4,572.3 / +5,986.3 | +5,425.5 | + |

w64t31 anchor: -10,533.9 (#1369) / -9,896.8 (#1377) / -12,848.6 (this) —
sign -/-/- across all three sessions.

## Findings

1. **The w64t32 loss sign RETURNS.** The third session reproduces #1369's
   positive sign 3/3, magnitudes +4.6k..+6.0k overlapping #1369's
   +4.4k..+5.3k. #1377's "the loss does not reproduce across sessions" is
   itself session-limited: the measured sign series across three independent
   sessions is **+, -, +**.
2. **Within-session sign stability is 3/3 in every one of the three sessions**
   (9/9 runs per session sign-unanimous for w64t32). The instability sits at
   session resolution, not run resolution.
3. **The W=64 win/loss pairing (t31 win / t32 loss at the identical grid)
   holds in 2 of 3 sessions** (#1369, this one); the #1377 session is the
   exception (both negative). The "flip 31..32" is reproducible but not
   invariant.
4. **The w64t31 anchor's magnitude is session-dependent**: -9.9k..-12.8k
   (this session ~22-27% deeper than the first two). The 5-6% cross-session
   band the chain saw for the anchor does not extend to a third sample. The
   anchor's sign, not its magnitude, is the stable quantity.
5. w32 cells keep their #1377 signs (3/3 negative each) and the W=32
   gap-deepens-with-tiles ordering (-17.1k < -26.0k < -29.0k) reproduces.

**Honesty.** Measured here: the sign series above, within-session sign
stability, run-start load1 range 8.5-19.8 (overlapping the #1377 session's
11.4-19.6, so run-start load1 does not order the w64t32 signs — but with 3
sessions this is absence of separation, not a mechanism). UNMEASURED: the
mechanism of the session-level sign flip (GPU state / driver / host load).
No `:measured?` flip, no vendor dispatch row changed; `accelerator-targets`
rows stay provisional. JUN-57/59/60 stay unmeasured (hardware absent).

## Gate

`kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)" run-tests.cljk`
at this commit: 311 tests / 4,973 assertions / 4,942 passed / 16 failures /
15 errors (GATE-EXIT=1). Normalized FAIL/ERROR set vs #1377's completed
gate.log: 31 occurrences / 13 distinct entries both sides,
SETS-AND-COUNTS-IDENTICAL (`gate-vs-2000.txt`). Not a green suite and not
claimed green; the 13 base-red entries are outside this diff (probe +
4 sha-pinned fixtures + docs/evidence only).

## Provenance

- `scripts/test-gpu-subgroup-reduce-chunksweep.cljk` and
  `test/fixtures/gpu/subgroup-reduce-w{32,64,128,256}-sum.emitted.glsl`:
  byte-identical copies from the tick-20261019-2000 worktree (PR #1377),
  shasum-verified identical against tick-20261019-1716 as well.
- Verbatim run logs `run-{1,2,3}-{w32t24,w32t31,w32t32,w64t31,w64t32}.log`
  (date/uptime header, INFO/SHAPE/PROTOCOL/VERIFY/ARMTIME/GAP/SPEEDUP/
  FLOORSHARE/RESULT trailer, `time` footer).
- `run-sweep-2030.sh.txt` (the driver, idempotent), `analyze-2030.py` /
  `analyze-2030.txt` (same rules as analyze-2000.py), `run-gate-2030.sh.txt`,
  `gate.log`, `norm_gate.py` (copied from the chain), `gate-vs-2000.txt`.

Linear 未記録: the Linear connector is unavailable this session
(CONNECTION_REQUIRED), so no JUN-58 comment was posted.

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
