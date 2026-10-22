# tilecross-w64-t31-20261019 -- the W=64 win band reaches 31 tiles: the
# 25..31 bracket's only admissible point is negative, and the measured flip
# to loss lands between 31 and 32

JUN-58 mechanism slice (parent JUN-55). PR #1360 narrowed the W=64 tile
crossing to "25..31 tiles UNMEASURED" and recorded that at the grid-B lane
count (2,095,104) only tiles=31 of 25..31 is admissible
(2,095,104/64 = 32,736 = 2^5*3*11*31; `valid-shape?` needs lanes/(W*tiles)
integral). This slice takes that point -- no lane-count move needed -- and
brackets it with same-session anchors.

## Design

New cell **n31** (W=64, chunks=31, L=1984, wg=1056, lanes 2,095,104),
exactly the shape PR #1360 named as the sole admissible member of 25..31.
Same-session anchors **n24** and **n32** run in every cycle so the sign call
for n31 is made against neighbors measured in this session (both anchors
were measured at this exact grid in PR #1360: clean -20,441 and +4,638).
3 cycles, cell order rotated (forward, reversed, rotated) via
`run-sweep-1716.sh.txt`; 9 runs, no retries.

## Provenance

The probe is `scripts/test-gpu-subgroup-reduce-chunksweep.cljk`, byte-
identical to the PR chain's copies (#1353-#1360; sha256
`3696ca0db0e28c5b41fa5c8551df2ae1302deb190e91722408117a06077ef652`, checked in
this worktree before any run); only argv differs per run. The variant bytes
are the sha-pinned emitter fixture
`test/fixtures/gpu/subgroup-reduce-w64-sum.emitted.glsl` (sha256
`a25a69317b5c5a956279ccc37a5089adb489104a28ed89460b8928889b096254`; w32/w128/
w256 fixtures ride along byte-identical but are unused here), verified
in-script before any timing line. Protocol is PR #1359's: three interleaved
arms (baseline shared-tree chunked, variant subgroup-reduce chunked, floor),
one kept command buffer each recording a batch of 512 identical DISPATCHes,
then 32 rounds of 3 REPLAYs with slot order alternating 012/210; 96 samples.
Per-run bit-exact verification (x[i]=i+1; first 4 workgroup partials must
equal L^2*g + L(L+1)/2, f32-exact integers) precedes every timing line; all
9 runs printed `RESULT verified=true` and exited 0.

Host: Apple M1 Max (MacBookPro18,4) / MoltenVK 1.3.357, glslang 11:16.6.0.
Raw logs `run-<cycle>-<cell>.log` here (uptime and wall time inside each).
Worktree env: `npm ci` (8 packages, gitignored) for nbb; not part of this
diff. Analysis: `analyze-1716.py` (line-oriented extraction +
the chain's noise rule), output saved verbatim as `analyze-1716.txt`.

## The W=64 tile axis at lanes 2,095,104 (gap = variant minus baseline
ns/dispatch; L = W*tiles = per-workgroup lanes)

| cell | shape (W x tiles) | L | workgroups | run 1 | run 2 | run 3 | mean(3) |
|---|---|---|---|---|---|---|---|
| n24 (anchor) | 64 x 24 | 1,536 | 1,364 | -19,438.5 | -20,194.3 | -20,409.2 | **-20,014.0** |
| **n31 (new)** | 64 x 31 | 1,984 | 1,056 | -10,632.8 | -10,754.9 | -10,213.9 | **-10,533.9** |
| n32 (anchor) | 64 x 32 | 2,048 | 1,023 | +5,284.2 | +4,644.5 | +4,397.5 | **+4,775.4** |

Noise rule (identical to PR #1358/#1359/#1360's, stated and applied
uniformly): a run is noisy when its per-round ratio IQR exceeds 0.05 or its
floor share is inflated (>1.2x the cell's clean minimum). **No run is
excluded this session** -- all 9 runs pass both tests (ratio IQR
0.0068-0.0304; floor shares 0.2100-0.2392 per cell, well inside the 1.2x
band). Host 1-min load 13.39-21.69 across runs, below PR #1360's 16.9-48.2.
For every cell mean(3) equals the clean-run estimate because all 3 runs
survive. Every run's speedup effect exceeds its own IQR, as the protocol
requires.

Anchors (same session, same grid, same probe, same protocol): n24
reproduces PR #1360's clean n24 (-20,441) at **-20,014.0 (2.1%)**; n32
reproduces PR #1360's clean n32 (+4,638) at **+4,775.4 (3.0%)**. Same sign,
magnitudes within ~3%: this session is comparable to the chain's, and the
n31 call below is bracketed by both signs measured here.

## Finding

**At 31 tiles (L=1984, W=64, lanes 2,095,104) the subgroup-reduce variant
is still faster: gap -10,533.9 ns/dispatch (mean(3) = clean-run estimate;
all 3 runs negative, spread 541 ns = 5% of the mean).** The 25..31 bracket's
only admissible point is a win for the variant. Measured axis at W=64 now:

    +2,440 (1, #1359 at 2^21) -> -18,591 (8) -> -12,686 (16) -> -20,441 (24)
    -> -10,533.9 (31) -> +4,775.4 (32)   [8/16/24/31/32 at lanes 2,095,104]

The measured sign change -- the flip from win to loss -- is now located
**between 31 and 32 tiles**, one tile wide on the measured axis. The margin
shrinkage is monotone in the last step (24 -> 31 -> 32: -20,441 -> -10,534 ->
+4,775) but the axis as a whole remains non-monotone (24 is deeper than 16
or 31), so no smooth extrapolation is licensed.

Dispatch consequence (design input, not implemented here): the W=64
emission band is now **8..31 tiles of the measured axis** (2..7, 9..15,
17..23, 25..30 UNMEASURED; 1-tile point loses at 2^21 and is unmeasured at
this grid). Rules of "2 <= tiles <= 16" or "2 <= tiles <= 24" would both
miss wins; the predicate still needs W and per-workgroup work (W x tiles)
jointly (#1358's conclusion, unchanged). For the :apple row (W=256) the
safe rule is unchanged and now quadruply confirmed: keep the baseline tree.

## Non-claims

- One device (Apple M1 Max through MoltenVK, not a native Metal path), one
  workload (x[i]=i+1 f32 sum), one lane count. Claims are gap signs, the
  anchor reproductions, and the measured 31-to-32 flip -- not precise
  magnitudes (n32's 3-run spread is 18.6% of its mean).
- tiles 2..7, 9..15, 17..23 and **25..30 at W=64 remain UNMEASURED**. The
  flip to loss is measured between 31 and 32, but because the axis is
  non-monotone, a local loss band inside 25..30 cannot be excluded from
  these data. Bisecting 25..30 needs another lane-count move of the PR
  #1360 kind (e.g. a lane count divisible by 64*28). Any L at W=32 is
  UNMEASURED. At W=256 the >8-tile region remains inadmissible under this
  harness (f32-exact readback bound 3L^2 + L(L+1)/2 < 2^24, so L <= ~2176).
- This diff flips no `:measured?` flag in
  `kotoba.compiler.accelerator-targets` and is not a vendor dispatch row.
  The Intel (JUN-59) and Mali (JUN-60) comparisons need hardware this bot
  does not have.

## Gate (completed in this tick)

Canonical suite at the worktree root
(`kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)" run-tests.cljk`,
wrapper `run-gate-1716.sh.txt`), run to completion in this tick (log overwritten
once after a first wrapper invocation lost its cwd before the suite started;
the completed run is the only suite run in `gate.log`):

    Ran 311 tests containing 4973 assertions.
    16 failures, 15 errors.
    nbb: 311 tests, 4942 passed, 16 failed, 15 errors
    GATE-EXIT=1

This diff adds no tested namespace (probe script + 4 sha-pinned emitter
fixtures + docs/evidence only), so the gate claim is that the base red
reproduces unchanged. Normalized FAIL/ERROR comparison (kind + test name,
file:line stripped) against PR #1360's completed `gate.log`, via
`norm_gate.py` in this directory (sha256
`c3197a69bd6517b8a6fc9a8a95a97a3316a677ef8de10cce77ab05aeec1da563`;
output saved verbatim as `gate-vs-1360.txt` in this directory):
**31 occurrences, 13 distinct kind+name entries in both logs,
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
CONNECTION_EXPIRED; reconnect needs the user, unattended cron cannot).
