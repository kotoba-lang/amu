# tilecross-w64-t24-20261019 -- the W=64 win band extends to 24 tiles: the
# 16-to-32 crossing is narrowed to 25..31, and 17..31 is unmeasurable at 2^21

JUN-58 mechanism slice (parent JUN-55). PR #1359 narrowed the W=64 tile
crossing to "17..31 tiles UNMEASURED" and named "tiles 24 (L=1536) is the
next bisection of 17..31". This slice takes that bisection, after a design
correction the previous slice's plan needed:

**At lanes 2^21, tiles 24 is not admissible under this harness** -- and
neither is ANY tile count in 17..31. `valid-shape?` requires lanes/(W*tiles)
integral, so at 2^21 lanes (W=64) the tile count must divide 2^15, i.e. be a
power of two; 17..31 contains none. Demonstrated by running the proposed
shape: `refuse-t24-at-2pow21.log`, exit 3, `COULD-NOT-RUN shape W=64
lanes=2097152 chunks=24 is not admissible`. The 8-to-32 crossing therefore
cannot be bisected at the chain's standard lane count at all -- tile axes at
2^21 only have points at tiles 1, 2, 4, 8, 16, 32.

Design decision for this slice: move grid B to **lanes 2,095,104 = 6144*341
= 0.098% below 2^21**, the nearest lane count to 2^21 where tiles 8/16/24/32
are all admissible (verified against the probe's own rules: wg
4092/2046/1364/1023, lanes/256 = 8184, L=2048 f32 bound 14,681,088 < 2^24;
of 25..31 only tiles=31 is admissible at this lane count too -- 2,095,104/64
= 32,736 = 2^5*3*11*31). The new cell is **n24 (tiles 24, L=1536)**; n8/n16/
n32 run in the same session as the tile axis; cal16 runs the PR-#1359 t16
cell exactly (lanes 2^21) as a session-drift calibration against the known
point.

## Provenance

The probe is `scripts/test-gpu-subgroup-reduce-chunksweep.cljk`, byte-
identical to PRs #1353/#1355/#1356/#1358/#1359's copies (sha256
`3696ca0db0e28c5b41fa5c8551df2ae1302deb190e91722408117a06077ef652`, checked
in this worktree before any run); only argv differs per run. The variant
bytes are the sha-pinned emitter fixture
`test/fixtures/gpu/subgroup-reduce-w64-sum.emitted.glsl` (sha256
`a25a69317b5c5a956279ccc37a5089adb489104a28ed89460b8928889b096254`, the
same file the chain used; w32/w128/w256 fixtures ride along byte-identical
but are unused here), verified in-script before any timing line. Protocol is
PR #1359's: three interleaved arms (baseline shared-tree chunked, variant
subgroup-reduce chunked, floor), one kept command buffer each recording a
batch of 512 identical DISPATCHes, then 32 rounds of 3 REPLAYs with the slot
order alternating 012/210; 96 samples. Per-run bit-exact verification
(x[i]=i+1; first 4 workgroup partials must equal L^2*g + L(L+1)/2, f32-exact
integers) precedes every timing line; all 15 runs printed `RESULT
verified=true` and exited 0.

Runs: 5 cells x 3 cycles, cell order rotated per cycle (forward, reversed,
rotated) via `run-sweep-1246.sh.txt`. Apple M1 Max / MoltenVK 1.3.357, glslang
11:16.6.0. Raw logs `run-<cycle>-<cell>.log` here (uptime and wall time
inside each). Worktree env: `npm ci` (8 packages, gitignored) for nbb; not
part of this diff.

## The W=64 tile axis at lanes 2,095,104 (gap = variant minus baseline
ns/dispatch; L = W*tiles = per-workgroup lanes)

| cell | shape (W x tiles) | L | workgroups | run 1 | run 2 | run 3 | mean(3) | clean-run est. |
|---|---|---|---|---|---|---|---|---|
| cal16 (2^21) | 64 x 16 | 1,024 | 2,048 | -8,565 N | -13,157 | -5,964 N | -9,229 | -13,157 (r2) |
| n8 | 64 x 8 | 512 | 4,092 | -34,036 N | -18,591 | -23,931 N | -25,519 | **-18,591 (r2)** |
| n16 | 64 x 16 | 1,024 | 2,046 | +5,302 N | -14,392 N | -12,686 | -7,258 | **-12,686 (r3)** |
| n24 | 64 x 24 | 1,536 | 1,364 | -21,060 N | -20,441 | -22,910 N | -21,471 | **-20,441 (r2)** |
| n32 | 64 x 32 | 2,048 | 1,023 | +5,265 | +4,011 | +28,861 N | +12,712 | **+4,638 (r1,r2)** |

Noise rule (identical to PR #1358/#1359's, stated and applied uniformly): a
run is noisy when its per-round ratio IQR exceeds 0.05 or its floor share is
inflated (>1.2x the cell's clean minimum; "clean minimum" = the minimum
floor share among the cell's IQR-clean runs). N marks excluded runs. This
session ran under much higher host load than the chain's prior sessions
(1-min load 16.9-48.2 across runs, vs 5-14 in #1358 and 12.7-25.8 in
#1359), and 9 of 15 runs are excluded: cal16 r1/r3 (IQR 0.508/0.409), n8
r1/r3 (0.671/0.513; r3 floor share 0.628 also inflated), n16 r1 (0.698) and
r2 (0.056, marginal over 0.05), n24 r1 (floor share 0.334 vs 1.2x clean min
0.326) and r3 (0.358), n32 r3 (0.187 + floor share inflated). The clean-run
estimate column is the mean of the surviving runs (one run for cal16/n8/
n16/n24, two for n32); mean(3) is shown for transparency but is NOT the
claim where runs are excluded. Every surviving run's speedup effect exceeds
its own IQR (0.007-0.05), as the protocol requires.

Sensitivity note (cal16 only): under the alternative reading "clean minimum
= minimum floor share over all of the cell's runs", r2's floor share 0.3206
is 0.6% over 1.2x*0.2656 and cal16 would have zero surviving runs. Both
readings agree on the sign; cal16's claim is its reproduction of the known
point (see anchors), not a new estimate.

Anchors (same session, same probe, same protocol). The new lane count is
validated against the 2^21 chain by reproducing its points at wg counts
within 4 workgroups of the originals: n32 reproduces PR #1359's t32 mean
(+4,628) at **+4,638 (0.2%)**; n8 reproduces #1359's t8 (-18,226) at
**-18,591 (2.0%)**; n16 reproduces #1359's t16 (-13,995) at **-12,686
(9.4%)**; cal16 (the exact #1359 t16 cell at 2^21) lands at **-13,157
(6.0%)**. Same sign everywhere, magnitudes within 10% despite the load --
the 0.098% lane-count move does not move the axis.

## Finding

**At 24 tiles (L=1536, W=64, lanes 2,095,104) the subgroup-reduce variant
is still faster: gap -20,441 ns/dispatch on the surviving run, and the sign
is not a noise artifact -- all 3 runs are negative and tightly clustered
(-21,060 / -20,441 / -22,910, spread 2,469 ns = 12% of the mean(3)
-21,471).** The W=64 win band therefore extends past 16 tiles: of the tile
counts measured at W=64 across the chain (1, 8, 16, 24, 32) the variant wins
at 8, 16 and 24 and loses at 1 and 32. The crossing PR #1359 bounded at
"17..31 tiles" is narrowed to **25..31 tiles (L=1600..1984 at W=64), still
UNMEASURED**.

The tile axis stays non-monotone and is now two-dipped on measured points:
+2,440 (1, #1359 at 2^21) -> -18,591 (8) -> -12,686 (16) -> -20,441 (24) ->
+4,638 (32) at the new lane count (1-tile point UNMEASURED here). The
variant's margin at 24 tiles is deeper than at 8 or 16, so no local
extrapolation from 16 or 32 would have found this: the crossing is not a
smooth function of per-workgroup work (W x tiles).

Dispatch consequence (design input, not implemented here): the measured
W=64 wins are at the sampled tile counts 2 (chain row), 8, 16 and 24
(1-tile point UNMEASURED at this lane count; chain's 2^21 point loses) --
a contiguous 2..24 emission band is NOT established: 2..7, 9..15 and
17..23 are unmeasured and the axis is non-monotone, so a 2..24 rule
would select the variant at unmeasured counts without evidence. A rule
of "2 <= tiles <= 16 -> emit :subgroup-reduce" would have missed a
-20,000 ns win at 24 tiles. The predicate still needs W and
per-workgroup work (W x tiles) jointly (#1358's conclusion, unchanged):
W=256 loses at every measured tile count, W=64 wins at the measured win
points. For the :apple row (W=256) the safe rule is unchanged and now
triply confirmed: keep the baseline tree.

## Non-claims

- One device (Apple M1 Max through MoltenVK, not a native Metal path), one
  workload (x[i]=i+1 f32 sum), one lane count plus its 0.098% calibration
  variant. Host load was high (16.9-48.2) and 9/15 runs are excluded by the
  stated noise rule; four of five clean-run estimates rest on a single run.
  The claims are the gap SIGNS (robust: n24 is negative in all 3 runs), the
  anchor reproductions, and the crossing bound -- not precise magnitudes.
- tiles 2..7, 9..15, 17..23 and 25..31 at W=64 are UNMEASURED. The crossing
  is bounded to 25..31, not located. At lanes 2^21 NO tile count in 17..31
  is admissible under this harness (tiles must divide 2^15); at lanes
  2,095,104 only tiles=31 of 25..31 is admissible (2,095,104/64 = 32,736 =
  2^5*3*11*31), so bisecting 25..31 further needs another lane-count move of
  the same kind (e.g. a lane count divisible by 64*28). Any L at W=32 is
  UNMEASURED. At W=256 the >8-tile region remains inadmissible under this
  harness (the f32-exact readback needs 3L^2 + L(L+1)/2 < 2^24, so L <=
  ~2176).
- The axis values at 8/16/32 tiles here are the NEW lane count's (wg
  4092/2046/1023 vs 2^21's 4096/2048/1024); their agreement with the 2^21
  chain (within 0.2-9.4%) is the evidence that the move is benign, not a
  proof for other lane counts.
- This diff flips no `:measured?` flag in
  `kotoba.compiler.accelerator-targets` and is not a vendor dispatch row.
  The Intel (JUN-59) and Mali (JUN-60) comparisons need hardware this bot
  does not have.

## Gate (completed in the follow-up tick 20261019-1700; result below)

Canonical suite at the worktree root
(`kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)" run-tests.cljk`,
wrapper `run-gate-1246.sh.txt`). The tick-1246 attempt was STARTED at 13:05 JST
2026-10-19 and died at session teardown mid-suite (288/490 log lines, no
summary line; that partial log is what the tick-1246 commit captured as
"started, NOT completed"). The follow-up tick re-ran the same wrapper from
scratch (log overwritten) to completion on 2026-10-19 ~17:15 JST:

    Ran 311 tests containing 4973 assertions.
    16 failures, 15 errors.
    nbb: 311 tests, 4942 passed, 16 failed, 15 errors
    GATE-EXIT=1

This diff adds no tested namespace (probe script + 4 sha-pinned emitter
fixtures + docs/evidence only), so the gate claim is that the base red
reproduces unchanged. Normalized FAIL/ERROR comparison (kind + test name,
file:line stripped) against PR #1359's completed `gate.log`, via
`norm_gate.py` in this directory (sha256
`c3197a69bd6517b8a6fc9a8a95a97a3316a677ef8de10cce77ab05aeec1da563`;
output saved verbatim as `gate-vs-1359.txt` in this
directory): **31 occurrences, 13 distinct kind+name entries in both logs,
SETS-AND-COUNTS-IDENTICAL** -- the same 16 FAIL / 15 ERROR the chain has
documented as base red since PR #1353, byte-identical at the kind+name
level. No new failure is attributable to this diff. The suite is NOT green
and is not claimed green: the 13 base-red entries (row-tuple-element-
argument-test, numbered-grants-at-any-count, same-policy-read-twice-is-equal,
malformed-policy-still-refused-by-name, text-edit-rebound-state-is-a-row-test,
min-max-qualified-on-typed-wasm-test, named-grants-at-any-count,
refuses-macos-static-host-*, native-constructors-charge-fuel-test,
packages-macos-with-a-macos-profile-and-platform-load-command,
every-source-namespace-is-reachable-from-the-tests) remain red at base and
are outside this diff. With this evidence the slice is complete:
"measurement completed and verified, gate evidence landed".

JUN-58 (parent JUN-55). Linear 未記録 (Linear connector
CONNECTION_REQUIRED; reconnect needs the user, unattended cron cannot).
