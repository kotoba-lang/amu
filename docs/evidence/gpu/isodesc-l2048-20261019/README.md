# isodesc-l2048-20261019 -- at constant per-workgroup reduce work the
# subgroup-reduce variant loses at every W; the W=64 win band does not
# extend to 32 tiles

JUN-58 mechanism slice (parent JUN-55). PR #1356 measured grid B (lanes
fixed at 2^21, reduce work constant per cell) at W=256 and concluded the
algorithm verdict is a function of W **and** tiles-per-workgroup, naming
"any emission-side choice needs W in the predicate" as design input. Two
questions were left open: (a) at constant per-workgroup reduce work
L = W*chunks, does the gap depend on W at all; (b) does the W=64 tile
axis -- which drove the gap monotonically to -18,048 by 8 tiles (PR
#1355) -- keep falling past 8 tiles. This slice answers both with one
iso-L diagonal.

## Provenance

The probe is `scripts/test-gpu-subgroup-reduce-chunksweep.cljk`, byte-
identical to PR #1355's and #1356's copy (sha256
`3696ca0db0e28c5b41fa5c8551df2ae1302deb190e91722408117a06077ef652`);
only argv differs per run. Variant bytes are the sha-pinned emitter
fixtures `test/fixtures/gpu/subgroup-reduce-w{32,64,128,256}-sum.emitted.glsl`
(W=64 `a25a6931...`, W=128 `c7931718...`, W=256 `087107f9...`),
verified in-script before any timing line. Protocol is PR #1356's: three
interleaved arms (baseline shared-tree chunked, variant subgroup-reduce
chunked, floor), one kept command buffer each recording a batch of 512
identical DISPATCHes, then 32 rounds of 3 REPLAYs with the slot order
alternating 012/210; 96 samples. Per-run bit-exact verification
(x[i]=i+1; first 4 workgroup partials must equal L^2*g + L(L+1)/2,
L=W*chunks, f32-exact integers) precedes every timing line; all 12 runs
printed `RESULT verified=true` and exited 0.

Runs: 4 cells x 3 cycles, cell order rotated per cycle (forward,
reversed, rotated) via `run-sweep-1152.sh.txt`. Apple M1 Max / MoltenVK
1.3.357, glslang 11:16.6.0. Raw logs `run-<cycle>-<cell>.log` here
(uptime and wall time inside each).

## The iso-L diagonal (L = 2048 lanes per workgroup, 1,024 workgroups,
2^21 lanes; gap = variant minus baseline ns/dispatch)

| cell | shape (W x tiles) | run 1 | run 2 | run 3 | mean(3) | tight mean |
|---|---|---|---|---|---|---|
| iso64 | 64 x 32 | +4,972 | -5,806* | +5,853 | +1,673 | +5,412 (2) |
| iso128 | 128 x 16 | +13,449* | +12,761 | +13,243 | +13,151 | +13,002 (2) |
| iso256 | 256 x 8 | +8,221 | +8,084 | -1,486* | +4,940 | +8,152 (2) |
| anchor | 64 x 1 (32,768 wg) | +2,535 | +2,582 | +2,306 | +2,474 | +2,474 (3) |

`*` = noise window, per the rule below. Noise rule (stated, applied
uniformly): a run is noisy when its per-round ratio IQR exceeds 0.05
(6 of 6 remaining runs are 0.0063-0.0241) or its floor share is inflated
(>1.2x the cell's clean minimum -- iso128 run 1: floor/baseline 0.474 vs
0.343 clean; its gap is in family with the tight runs anyway). The
anchor cell is floor-bound in every run (floor/baseline 0.85) as PR
#1355 flagged; its claim is the gap's sign and its reproduction of b1,
not absolute time.

Anchors: iso256 (256 x 8) reproduces PR #1356's c8 (+7,762 mean of 3
tight runs) at +8,152 tight mean (+8,221/+8,084) -- within ~5%. The
W=64 1-tile anchor reproduces PR #1355's b1 (+2,668) at +2,306..+2,582
(85-362 ns). Host load was 5-14 throughout (other tenants). The two runs
whose ratio IQR exceeds 0.05 are run-2-iso64-c32 (load 7.77) and
run-3-iso256-c8 (13.87); several non-noisy runs report higher load
snapshots than 7.77 (13.72, 13.54, 11.67), so only the iso256-c8 noise
window coincides with the highest loads and host load does not explain
the iso64-c32 window.

## Finding

**At constant per-workgroup reduce work (L=2048) the subgroup-reduce
variant is slower at every W tested.** 6 of 6 tight runs on the iso-L
diagonal have a positive gap -- W=64 +5,412 (tight mean), W=128
+13,002, W=256 +8,152 -- and so do all 3 anchor runs. The gap is not
monotone in W along the diagonal (W=128 is the worst point for the
variant, +13k), but its **sign is W-independent at this L**.

Combined with PRs #1355/#1356 (same probe, same protocol, same
workload), the shape of the verdict region on this device is now:

- W=64: gap +2,668 (1 tile) -> -6,760 (2) -> -11,451 (4) -> -18,048 (8)
  -> **+5,412 (32 tiles, this PR)**. The tile axis is **non-monotone**:
  the variant wins at the sampled counts 2, 4 and 8 tiles (L=128-512;
  tiles 3 and 5..7 are UNMEASURED, so this is wins at three points, not
  a continuous 2-8 band) and loses again by 32 tiles (L=2048). The
  8-to-32 crossing is UNMEASURED (tiles 9..31 at W=64 are admissible
  under the harness; they were not run).
- W=256 (the :apple workgroup row): positive at every tile count
  measured, 1-8 tiles (L=256-2048), now including the iso-L cell.
- W=128: first data point ever, at L=2048: positive, and the largest gap
  on the diagonal.
- Cross-W at L=512 (from #1355/#1356, same 4,096 workgroups): W=64
  -18,048 vs W=256 +6,708 -- same L, same count, opposite verdicts.

Dispatch consequence (design input, not implemented here): neither W
alone nor tiles alone nor L alone orders the verdict. A "tiles >= 2 ->
emit :subgroup-reduce" rule is wrong at W=256 (any tiles) and wrong at
W=64 with 32 tiles; the W=64 advantage is measured at the sampled counts
2, 4 and 8 tiles (3 and 5..7 unmeasured -- not a continuous band), not a
trend. Any emission-side predicate needs W and per-workgroup work
(W x tiles) jointly. For the :apple row (W=256) the safe rule is
unchanged and now iso-L-confirmed: keep the baseline tree.

## Non-claims

- One device (Apple M1 Max through MoltenVK, not a native Metal path),
  one lane count (2^21), one workload (x[i]=i+1 f32 sum). The iso-L
  diagonal is one L (2048); L values between 512 and 2048 at W=64 (the
  8-to-32 crossing) and any L at W=32 are UNMEASURED.
- At W=256 the >8-tile boundary PR #1356 named is **inadmissible under
  this harness**, not merely unmeasured: the f32-exact readback requires
  3L^2 + L(L+1)/2 < 2^24, so L <= ~2176 and W=256 admits at most 8
  whole tiles at any lane count. Measuring it needs a different workload
  or verifier (implementation slice, not taken here).
- iso64's tight runs (+4,972/+5,853) spread by 881 ns and one run is a
  noise window whose gap flips sign; the claim is the tight runs' sign
  and the +5.4k tight mean, not a precise magnitude.
- This diff flips no `:measured?` flag in
  `kotoba.compiler.accelerator-targets` and is not a vendor dispatch row.
  The Intel (JUN-59) and Mali (JUN-60) comparisons need hardware this bot
  does not have.

## Gate (completed)

Canonical suite at the worktree root
(`kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)" run-tests.cljk`,
wrapper `run-gate-1152.sh.txt`) ran to COMPLETION on this tree: **311 tests /
4973 assertions / 4942 passed / 16 failures / 15 errors (GATE-EXIT=1) --
not a green suite, and not claimed as one.** The FAIL/ERROR lines,
normalized for the worktree path embedded in run-tests.cljk, are
byte-identical to PR #1356's gate.log (itself documented as
byte-identical to #1353's landed base-red log: 16 FAIL / 15 ERROR
occurrences over the same 13 distinct kind+name entries). Pre-existing
base red; this diff adds no tested namespace (probe script + 4 sha-pinned
emitter fixtures + docs/evidence only). `gate.log` is in this directory.

JUN-58 (parent JUN-55). Linear 未記録 (Linear connector
CONNECTION_REQUIRED; reconnect needs the user, unattended cron cannot).
