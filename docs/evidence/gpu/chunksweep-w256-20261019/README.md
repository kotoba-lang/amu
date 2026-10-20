# chunksweep-w256-20261019 -- the W=64 tile-split flip does not reproduce at W=256

JUN-58 mechanism slice (parent JUN-55). PR #1355 ran the chunked-loop
reduce-variant grid at W=64 and flagged "one W (64)" as a non-claim. This
slice takes the same grid B (lanes fixed at 2^21, total reduce work
constant) at **W=256** -- the size of the :apple workgroup row -- plus one
same-day W=64 anchor cell interleaved into every cycle.

## Provenance

The probe is `scripts/test-gpu-subgroup-reduce-chunksweep.cljk`, byte-
identical to PR #1355's copy (sha256
`3696ca0db0e28c5b41fa5c8551df2ae1302deb190e91722408117a06077ef652`, the
same check that PR asserted over its chain); only argv differs per run.
Variant bytes are the sha-pinned emitter fixtures
`test/fixtures/gpu/subgroup-reduce-w{32,64,128,256}-sum.emitted.glsl`
(W=256 `087107f9...`, W=64 anchor `a25a6931...`), verified in-script before
any timing line. Protocol is PR #1355's: three interleaved arms (baseline
shared-tree chunked, variant subgroup-reduce chunked, floor), one kept
command buffer each recording a batch of 512 identical DISPATCHes, then 32
rounds of 3 REPLAYs with the slot order alternating 012/210; 96 samples.
Per-run bit-exact verification (x[i]=i+1; first 4 workgroup partials must
equal L^2*g + L(L+1)/2, L=W*chunks, f32-exact integers) precedes every
timing line; all 15 runs printed `RESULT verified=true` and exited 0.

Runs: 5 cells x 3 cycles, cell order rotated per cycle (forward, reversed,
rotated) to spread host-load drift. Apple M1 Max / MoltenVK 1.3.357,
glslang 11:16.6.0. Raw logs are `run-<cycle>-<cell>.log` here (uptime and
wall time inside each).

## Grid B at W=256 (lanes 2^21 fixed; gap = variant minus baseline ns/dispatch)

| cell | shape (wg x tiles) | run 1 | run 2 | run 3 | mean | ratio med (b/v) |
|---|---|---|---|---|---|---|
| c1 | 8,192 x 1 | +16,047 | +16,031 | +46,579* | +26,219 | 0.806 / 0.809 / 0.914* |
| c2 | 4,096 x 2 | +6,818 | +6,605 | +6,702 | +6,708 | 0.908 / 0.911 / 0.911 |
| c4 | 2,048 x 4 | +4,776 | +2,929* | +9,997* | +5,901 | 0.939 / 0.960* / 0.960* |
| c8 | 1,024 x 8 | +7,790 | +7,648 | +7,849 | +7,762 | 0.900 / 0.906 / 0.903 |
| anchor (W=64) | 32,768 x 1 | +2,606 | +2,357 | +11,703* | +5,556 | 0.963 / 0.961 / 0.959* |

`*` = noisy run: the per-round ratio IQR crosses or crowds 1.0, or the
floor share is inflated (see below). The c2 and c8 cells are tight (three
runs agree within 200 ns).

## Finding

**The W=64 verdict flip does not generalize to W=256.** At W=256 / 2^21
lanes the subgroup-reduce variant is slower at every tile count tested --
12 of 12 runs have a positive gap, including the noisy ones. The tiles
axis helps once (1 -> 2 tiles removes ~9-10k ns, +16.0k -> +6.7k) and then
saturates above zero (+5.9k at 4 tiles, +7.8k at 8 tiles); at W=64 the
same axis drove the gap monotonically to -18.0k (PR #1355: +2,668 ->
-6,760 -> -11,451 -> -18,048). The algorithm verdict is therefore a
function of W **and** tiles-per-workgroup, not tiles alone: at 2^21 lanes
the variant never beats the baseline tree at W=256 up to 8 tiles/group,
while at W=64 it wins from 2 tiles up.

Dispatch consequence (design input, not yet an implemented rule): a
"tiles >= 2 -> emit :subgroup-reduce" rule is wrong at W=256, which is
exactly the :apple workgroup row size. Any emission-side choice between
the shared-tree reduce and the subgroup reduce needs W in the predicate;
on this device the safe rule for W=256 keeps the baseline tree even in
multi-tile loops.

Anchors: the W=256 c1 cell (1 tile) is the chain's unchunked W=256 point
with a loop wrapper around it and reproduces it within ~3% (runs 1-2
+16.0k vs #1353's +15,630); the W=64 anchor cell reproduces PR #1355's b1
(+2,668) within 60-310 ns on its clean runs. Run 3 of every cell is a
host-noise window; the recorded load averages are the run's own
load averages lines (run-3-anchor-w64-2097152-c1.log: 29.31 16.57 13.02;
run-3-w256-2097152-c2.log: 22.80 16.10 12.95 — 1-min/5-min/15-min), not
the 9-11 clean-run band previously claimed here; floor/baseline inflates
to 0.79-0.88 there vs 0.38-0.45 at W=256 in clean runs. The sign of the
gap is positive in every run, noise window included.

## Non-claims

- One device (Apple M1 Max through MoltenVK, not a native Metal path), one
  lane count (2^21), one workload (x[i]=i+1 f32 sum), one tile grid
  (1/2/4/8 tiles). The boundary between 8 and more tiles at W=256 is
  UNMEASURED (8 is the top of this grid); so is any lane count other than
  2^21 here.
- c4 at W=256 is noise-limited (ratio IQR 0.14-0.36 in 2 of 3 runs); its
  mean is quoted but only c2/c8 are tight cells.
- The W=64 anchor cell is floor-bound (floor/baseline 0.85), as PR #1355
  flagged for its 1-tile cells; the anchor claim is the gap's sign and its
  reproduction of b1, not absolute time.
- This diff flips no `:measured?` flag in
  `kotoba.compiler.accelerator-targets` and is not a vendor dispatch row.
  The Intel (JUN-59) and Mali (JUN-60) comparisons need hardware this bot
  does not have.

## Gate (completed)

Canonical suite at the worktree root
(`kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)" run-tests.cljk`,
wrapper run-gate-1122.sh) ran to COMPLETION on this tree: **311 tests /
4973 assertions / 4942 passed / 16 failures / 15 errors (GATE-EXIT=1) --
not a green suite, and not claimed as one.** The FAIL/ERROR lines,
normalized for the worktree path embedded in run-tests.cljk, are
byte-identical to PR #1353's landed gate.log (16 FAIL / 15 ERROR
occurrences over the same 13 distinct kind+name entries). Pre-existing
base red; this diff adds no tested namespace (probe script + 4 sha-pinned
emitter fixtures + docs/evidence only). `gate.log` is in this directory.

JUN-58 (parent JUN-55). Linear 未記録 (Linear connector
CONNECTION_EXPIRED; reconnect needs the user, unattended cron cannot).
