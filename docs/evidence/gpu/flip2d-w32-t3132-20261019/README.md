# flip2d-w32-t3132-20261019 — the 31->32 flip transplanted to W=32
# (tick 20261019-2000, JUN-58)

Question: the W=64 tile-crossing chain's only measured sign change (tiles=31
win / tiles=32 loss, lanes 2,095,104, PRs #1360/#1369) — is it tile-driven
(survives a W change) or a (W, tiles, grid) interaction (does not)?

Cells at lanes 2,095,104 = 2^5·3^2·7·11·31 (the #1360/#1369 flip grid):

| cell    | shape              | L    | wg   | role |
|---------|--------------------|------|------|------|
| w32t24  | W=32 chunks=24     | 768  | 2728 | NEW (win anchor at W=64) |
| w32t31  | W=32 chunks=31     | 992  | 2112 | NEW (flip pair, W-transplant) |
| w32t32  | W=32 chunks=32     | 1024 | 2046 | NEW (flip pair, W-transplant) |
| w64t31  | W=64 chunks=31     | 1984 | 1056 | same-session anchor (#1369 win) |
| w64t32  | W=64 chunks=32     | 2048 | 1023 | same-session anchor (#1360/#1369 loss) |

3 cycles rotated (forward/reversed/rotated), 15 runs, every run
`RESULT verified=true`. Probe sha256 3696ca0d… and fixture pins
byte-identical to the PR chain (#1246/#1716 worktrees hold the same probe
bytes — verified by shasum).

Files: run-sweep-2000.sh.txt (protocol; kept as text -- the repo's
workflow-lint refuses POSIX shell execution files), run-{1,2,3}-*.log (raw, incl. uptime
and wall clock), analyze-2000.py + analyze-2000.txt (chain noise rule:
ratio IQR <= 0.05, floor share <= 1.2x the cell's IQR-clean minimum),
gate.log (suite run for this diff).

Headline numbers (chain noise rule; gap = variant − baseline ns/dispatch,
negative = variant faster): see analyze-2000.txt. Sign structure:

- w32t24  -22,859.8 clean-run est (2/3 clean), signs -/-/-
- w32t31  -28,378.3 (3/3 clean), signs -/-/-
- w32t32  -32,315.1 (3/3 clean), signs -/-/-
- w64t31  -9,896.8 (3/3 clean), signs -/-/-
- w64t32  -7,546.9 (3/3 clean), signs -/-/-

Two facts:

1. At W=32 there is NO 31->32 flip: all three cells are variant wins and
   the gap DEEPENS with tiles (-22.9k -> -28.4k -> -32.3k).
2. The W=64 t32 loss does not reproduce across sessions at the identical
   shape: #1369 measured +4,397.5/+4,644.5/+5,284.2 (3/3 positive) and
   #1360 +4,010.7/+5,264.6 (clean runs) at W=64 chunks=32 wg=1023 lanes
   2,095,104; this session measures -8,128.9/-7,036.1/-7,475.6 (3/3
   negative) at the same shape with the same probe and fixture bytes.
   The t31 anchor DOES reproduce in the same session (-9,896.8 vs
   #1369's -10,533.9, 5-6% apart), so the probe still behaves as before
   where the earlier sessions agreed.

This flips no :measured? flag and adds no vendor dispatch row.
