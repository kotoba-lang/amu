# tilecross-w64-20261019 -- the W=64 win band extends to 16 tiles: the
# a sign change lies in 17..31 tiles; 9..15 remain unmeasured (not excluded)

JUN-58 mechanism slice (parent JUN-55). PR #1358's iso-L diagonal named one
UNMEASURED region in its non-claims: at W=64 the subgroup-reduce variant's
tile axis is non-monotone -- +2,668 (1 tile) -> -6,760 (2) -> -11,451 (4)
-> -18,048 (8) (PR #1355) -> +5,412 (32, PR #1358) -- and "the 8-to-32
crossing is UNMEASURED (tiles 9..31 at W=64 are admissible under the
harness; they were not run)". This slice runs the missing midpoint: tiles
16 (L=1024), with 1/8/32-tile anchors run in the same session so the new
point is compared against reproductions, not against another session's
numbers.

## Provenance

The probe is `scripts/test-gpu-subgroup-reduce-chunksweep.cljk`, byte-
identical to PRs #1353/#1355/#1356/#1358's copies (sha256
`3696ca0db0e28c5b41fa5c8551df2ae1302deb190e91722408117a06077ef652`);
only argv differs per run. The variant bytes are the sha-pinned emitter
fixture `test/fixtures/gpu/subgroup-reduce-w64-sum.emitted.glsl` (sha256
`a25a69317b5c5a956279ccc37a5089adb489104a28ed89460b8928889b096254`,
the same file PR #1355/#1356/#1358 used; w32/w128/w256 fixtures ride along
byte-identical but are unused here), verified in-script before any timing
line. Protocol is PR #1358's: three interleaved arms (baseline shared-tree
chunked, variant subgroup-reduce chunked, floor), one kept command buffer
each recording a batch of 512 identical DISPATCHes, then 32 rounds of 3
REPLAYs with the slot order alternating 012/210; 96 samples. Per-run
bit-exact verification (x[i]=i+1; first 4 workgroup partials must equal
L^2*g + L(L+1)/2, L=W*chunks, f32-exact integers) precedes every timing
line; all 12 runs printed `RESULT verified=true` and exited 0.

Runs: 4 cells x 3 cycles, cell order rotated per cycle (forward, reversed,
rotated) via `run-sweep-1217.sh.txt`. Apple M1 Max / MoltenVK 1.3.357, glslang
11:16.6.0. Raw logs `run-<cycle>-<cell>.log` here (uptime and wall time
inside each). Worktree env: `npm ci` (8 packages, gitignored) for nbb;
not part of this diff.

## The W=64 tile axis at lanes 2^21 (gap = variant minus baseline
ns/dispatch; L = W*tiles = per-workgroup lanes)

| cell | shape (W x tiles) | L | workgroups | run 1 | run 2 | run 3 | mean(3) |
|---|---|---|---|---|---|---|---|
| b1 | 64 x 1 | 64 | 32,768 | +2,520 | +2,429 | +2,370 | +2,440 |
| t8 | 64 x 8 | 512 | 4,096 | -18,392 | -18,652 | -17,634 | **-18,226** |
| t16 | 64 x 16 | 1,024 | 2,048 | -13,421 | -13,582 | -14,982 | **-13,995** |
| t32 | 64 x 32 | 2,048 | 1,024 | +5,606 | +4,623 | +3,654 | **+4,628** |

Noise rule (identical to PR #1358's, stated and applied uniformly): a run
is noisy when its per-round ratio IQR exceeds 0.05 or its floor share is
inflated (>1.2x the cell's clean minimum). **No run is excluded this
session** -- all 12 pass both tests (ratio IQR 0.0073-0.0220; floor share
t8 0.320-0.324, t16 0.262-0.272, t32 0.239-0.244; b1 0.849-0.853 is
floor-bound as #1355/#1358 flagged -- its claim is the gap's sign and its
reproduction of b1, not absolute time). mean(3) is therefore all three
runs in every cell.

Anchors (same session, same probe, same protocol): t8 reproduces PR
#1355's 8-tile point (-18,048) at -18,226 (~1%); b1 reproduces #1355's b1
(+2,668) and sits inside #1358's b1 repro band (+2,306..+2,582) at
+2,370..+2,520; t32 reproduces #1358's iso64 cell (tight mean +5,412,
tight runs +4,972/+5,853) at +4,628 mean (runs +3,654..+5,606) -- same
sign, ~15% lower mean. Host load was higher this session than #1358's
(1-min 12.7-25.8 vs 5-14); every run still passes the stated noise rule.

## Finding

**At 16 tiles (L=1024, W=64) the subgroup-reduce variant is still faster:
-13,995 ns/dispatch mean of 3 runs, all 3 negative (-13,421 / -13,582 /
-14,982), all clean under the noise rule.** Of the tile counts measured at
W=64 (1, 8, 16, 32) the variant wins at 8 and 16 and loses at 1 and 32, so
at least one sign change lies in 17..31 tiles (L=1088..1984 at W=64,
still UNMEASURED). What this slice does NOT establish is that 17..31 is
the whole crossing region: the axis is non-monotone and tiles 9..15 are
unmeasured, so one or more further sign changes inside 9..15 cannot be
excluded. Narrowing the crossing to 17..31 would require monotonicity
after tile 8 (not established) or measurements at 9..15.

The tile axis stays non-monotone and is now single-peaked on measured
points: +2,440 (1) -> -18,226 (8) -> -13,995 (16) -> +4,628 (32). The
variant's margin is deepest at 8 tiles and already shrinking at 16, so
the crossing is not at a tile count this harness can pin with one more
midpoint -- tiles 24 (L=1536) is the next bisection of 17..31.

Dispatch consequence (design input, not implemented here): the measured
W=64 wins are at the sampled tile counts 2, 4 (PR #1358's rows), 8 and 16
(this slice) -- a contiguous 2..16 emission band is NOT established: 3,
5..7 and 9..15 are unmeasured and the axis is non-monotone. A rule of
"2 <= tiles <= 8 -> emit :subgroup-reduce" would have missed a
-14,000 ns win at 16 tiles; a rule of "2..16" would select the variant at
unmeasured counts without evidence. The predicate still needs W and
per-workgroup work (W x tiles) jointly (#1358's conclusion, unchanged):
W=256 loses at every measured tile count, W=64 wins at the measured win
points. For the :apple row (W=256) the safe rule is unchanged and now
doubly confirmed: keep the baseline tree.

## Non-claims

- One device (Apple M1 Max through MoltenVK, not a native Metal path), one
  lane count (2^21), one workload (x[i]=i+1 f32 sum).
- tiles 2..7, 9..15 and 17..31 at W=64 are UNMEASURED. At least one
  crossing lies in 17..31 (the measured 16-win -> 32-loss sign change);
  the crossing is NOT located, and because the axis is non-monotone,
  further crossings inside 9..15 are not excluded. Any L at W=32 is
  UNMEASURED. At W=256 the >8-tile region remains inadmissible under
  this harness (the f32-exact readback needs 3L^2 + L(L+1)/2 < 2^24, so
  L <= ~2176).
- Magnitudes: t16's run spread is 1,561 ns between extremes and the ratio
  min/max columns show occasional outlier rounds (e.g. b1 0.49-1.79)
  although IQRs stay <= 0.022. The claims are the gap signs, the means,
  and the anchor reproductions -- not precise magnitudes.
- This diff flips no `:measured?` flag in
  `kotoba.compiler.accelerator-targets` and is not a vendor dispatch row.
  The Intel (JUN-59) and Mali (JUN-60) comparisons need hardware this bot
  does not have.

## Gate (completed)

Canonical suite at the worktree root
(`kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)" run-tests.cljk`,
wrapper `run-gate-1217.sh.txt`) ran to COMPLETION on this tree: **311 tests /
4973 assertions / 4942 passed / 16 failures / 15 errors (GATE-EXIT=1) --
not a green suite, and not claimed as one.** The FAIL/ERROR lines,
normalized for the worktree path embedded in run-tests.cljk, are
byte-identical to PR #1358's gate.log (`diff` of the normalized FAIL/ERROR
extracts is empty; #1358's log is itself documented as byte-identical to
#1353's landed base-red log: 16 FAIL / 15 ERROR occurrences over the same
13 distinct kind+name entries). Pre-existing base red; this diff adds no
tested namespace (probe script + 4 sha-pinned emitter fixtures +
docs/evidence only). `gate.log` is in this directory.

JUN-58 (parent JUN-55). Linear 未記録 (Linear connector
CONNECTION_REQUIRED; reconnect needs the user, unattended cron cannot).
