# gpu/wsweep-load2x-20261019 -- fixed-stream W-sweep at 2^21 lanes (JUN-58)

Raw logs from `scripts/test-gpu-subgroup-reduce-loadsweep.cljk` (sha256
871bfde4a14e4168fba9808581acd7b2a704f47054cac49eee54e1f35f1da462,
byte-identical to PRs #1349/#1350/#1352), 9 verified runs (3 per workgroup
size) on Apple M1 Max / MoltenVK (Vulkan 1.3.357), glslang 11:16.6.0,
aarch64-macos, 2026-10-19 10:21:54-10:23:26 JST. Every run verified x[i]=i+1
and the first four workgroup partials of BOTH reduce arms bit-exact (f32,
sum W^2*g + W(W-1)/2 + W, g = 0..3) before printing any timing line; all 9
runs printed `RESULT verified=true` and exited 0. Host load averages
8.72-13.70 throughout (other tenants; `uptime` inside each log).

## Why this probe exists

The W=64 load chain (PRs #1349/#1350/#1352) grows the gap (variant minus
baseline, ns/dispatch) with load, but at fixed W every added workgroup also
adds W lanes to the x[] stream: workgroup count and stream size are
proportional, so the chain cannot say which one drives the growth
(PR #1352, "Mechanism UNRESOLVED"). This probe breaks the proportionality
from the other side: **the x[] stream is held constant at 2,097,152 lanes
(2^21) per dispatch at every W**, so the workgroup count moves the opposite
way -- W=64 -> 32,768 wg, W=128 -> 16,384 wg, W=256 -> 8,192 wg. W=32 is
NOT admissible at this stream: 2^21/32 = 65,536 groups exceeds the 65,535
grid-dim limit the script enforces (exit 3).

The W=64 cell (2^21 lanes, 32,768 wg) is exactly PR #1350's 2x point, so
the sweep re-anchors the chain's +2284 ns gap on the day of measurement.
Run order is 3 cycles of (w64, w128, w256) in that FIXED order -- it is
not rotated, so a monotonic host or thermal drift correlates with W
rather than biasing the sizes symmetrically (review finding). The W
comparison below is read with that caveat. Everything else (probe bytes,
sha-pinned fixtures, 3 arms, 512-dispatch kept buffers, 32 rounds x 3
REPLAYs, parity-alternating arm order, 96 samples, bit-exact verification
before any timing line) is the chain's.

Setup note: the first driver pass produced no runs (fresh worktree had no
`node_modules/nbb`; the script answered COULD-NOT-RUN exit 3). After
carrying the chain worktree's `node_modules` over (untracked, not part of
this diff) all 9 runs completed.

## baseline/variant ratio (median of 32 within-round ratios; BELOW 1.0 = variant slower)

| run | W   | wg      | ratio med | iqr    | min    | max    | vs-1.0 (script verdict)   | floor/base | ns/dispatch b / v / f        | gap v-b (ns) |
|-----|-----|---------|-----------|--------|--------|--------|---------------------------|------------|------------------------------|--------------|
| 1   | 64  | 32,768  | 0.9666    | 0.0122 | 0.8757 | 1.0779 | indistinguishable         | 0.876      | 62762 / 64967 / 54862        | +2205        |
| 2   | 64  | 32,768  | 0.9598    | 0.0130 | 0.7249 | 1.0617 | indistinguishable         | 0.874      | 63355 / 65647 / 55292        | +2292        |
| 3   | 64  | 32,768  | 0.9658    | 0.0098 | 0.9313 | 0.9810 | below (all 32 rounds)     | 0.877      | 63278 / 65525 / 55525        | +2247        |
| 1   | 128 | 16,384  | 0.8415    | 0.0164 | 0.8155 | 0.8676 | below (all 32 rounds)     | 0.681      | 61084 / 72600 / 41683        | +11516       |
| 2   | 128 | 16,384  | 0.8441    | 0.0182 | 0.8042 | 0.8865 | below (all 32 rounds)     | 0.741      | 62227 / 73519 / 46059        | +11292       |
| 3   | 128 | 16,384  | 0.8448    | 0.0213 | 0.8064 | 0.8708 | below (all 32 rounds)     | 0.615      | 62039 / 73329 / 37854        | +11290       |
| 1   | 256 | 8,192   | 0.8012    | 0.0227 | 0.3221 | 1.2590 | indistinguishable         | 0.551      | 66256 / 82645 / 37805        | +16389       |
| 2   | 256 | 8,192   | 0.8051    | 0.0183 | 0.5778 | 0.9085 | below (all 32 rounds)     | 0.491      | 66590 / 82819 / 32536        | +16230       |
| 3   | 256 | 8,192   | 0.8153    | 0.0545 | 0.5764 | 1.0225 | indistinguishable         | 0.697      | 69658 / 83930 / 50825        | +14272       |

Gap means (ns/dispatch, variant - baseline): **+2248 (W=64) / +11366
(W=128) / +15630 (W=256)**. The W=64 mean reproduces PR #1350's same-cell
three runs (+2284 mean; 2203/2368/2280) to within 36 ns. Ratio medians at
W=128 are the tightest in the chain (IQR .016-.021); W=256 run 3 is the
noisiest (IQR .055, kept, not dropped).

## Finding

1. **A per-workgroup-cost mechanism is refuted: the gap grows 5.1x (W=128)
   and 6.9x (W=256) while the workgroup count halves and quarters.** With
   the stream pinned at 2^21 lanes, a gap proportional to workgroup count
   (anchored at the W=64 cell's +2248 over 32,768 wg) predicts +1124 at
   16,384 wg and +562 at 8,192 wg. Measured: +11366 and +15630 -- an order
   of magnitude above the prediction at W=128, and the wrong sign of trend.

2. **An x[]-stream-size mechanism is refuted too: at identical stream the
   gap differs 7x between W cells.** A gap driven by lanes streamed would
   hold at +2248 for all three W. Measured W=128/W=256 gaps are 5.1x/6.9x
   that. Whatever the W=64 load chain's gap growth is made of, a model of
   the form gap = f(workgroups, stream) with no W term is dead.

3. **The dominant term is the workgroup size W (the reduce shape).** At
   fixed stream and falling workgroup count the gap grows monotonically
   with W, replicating off the launch floor the wsweep-20261019 fixed-2^20
   row's direction (ratio medians 0.96/1.01/0.84/0.77 across
   W=32/64/128/256, whose W=32/64 rows were floor-bound): here at 2^21
   lanes the medians are 0.96 (W=64) / 0.84 (W=128) / 0.80-0.82 (W=256).
   W=128/256 are off the floor (floor/baseline 0.49-0.55); W=64 is NOT --
   its floor/baseline is 0.874-0.877, more floor-bound than the 0.82 row
   the chain already calls floor-bound, and two of its three ratio ranges
   cross 1.0, so the W=64 point (incl. the +2248 re-anchor) is not a
   stable algorithmic anchor (review finding). The W effect spans
   2.2k -> 15.6k ns at 2^21 lanes; the entire W=64 load effect of the
   chain spans -468 -> +6454 ns across 2^20 -> 4.2M lanes. For this pair
   of reduce algorithms on this device, the shape is a bigger lever than
   the load.

What this does NOT settle: within one W, workgroups and stream remain
proportional (lanes = W x wg is the kernel's construction), so the W=64
chain's residual growth-with-load is still confounded at fixed W -- it is
now a secondary question, since points 1-2 show neither term explains the
gap's magnitude. A within-W separation needs a kernel where one workgroup
processes a variable number of W-sized chunks (loop inside the kernel);
that variant does not exist yet (implementation slice, not taken here).
One device (Apple M1 Max) only. This diff flips no :measured? flag in
kotoba.compiler.accelerator-targets. Note on repo state: PR #1336 landed
on main after this branch's measurement base (ff-synced in before commit)
and its ADR-0358 marked the :nvidia/:apple/:intel/:amd workgroup rows
:measured? true from the gpu-workgroup-sweep harness (:arm and :unknown
remain provisional). That is a different quantity from the
baseline-vs-subgroup-reduce gap measured here: this result is evidence
about the reduce-algorithm choice and neither validates nor contradicts
the workgroup-size rows. The Intel (JUN-59) and Mali (JUN-60) comparisons
need hardware this bot does not have.

## Gate (completed)

Canonical suite at the worktree root
(`kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)" run-tests.cljk`,
wrapper run-gate-1019.sh) ran to COMPLETION twice on this tree; `gate.log`
here is the authoritative run, taken AFTER the branch was ff-synced to
origin/main (722e480b) and BEFORE the commit; `gate-presync-0631a2ad.log`
is the earlier run at the branch's original base 0631a2ad. Post-sync
result: **311 tests / 4973 assertions / 4942 passed / 16 failures / 15
errors (GATE-EXIT=1) -- not a green suite, and not claimed as one.**
(Figures read from gate.log's own summary line: 4942 is the passed-assertion
count, not the total; 4973 is the total.)
(Pre-sync: 304 tests / 4939 assertions / 4908 passed / 16 failures / 15
errors. PR #1336's 7 new tests pass.) The FAIL/ERROR test-name sets are
byte-compared three ways -- post-sync vs pre-sync vs PR #1352's landed
gate.log: **all IDENTICAL** (13 unique names, 16 FAIL / 15 ERROR
occurrences). The red set is pre-existing base red (first-hand at base
bea7b9b2 in the chain; unchanged through 0631a2ad and 722e480b). This
diff adds no tested namespace (scripts + 4 sha-pinned golden GLSL fixtures
+ docs/evidence only).

JUN-58 (parent JUN-55). Linear 未記録 (Linear connector
CONNECTION_REQUIRED, reconnect needs the user; unattended cron cannot).
