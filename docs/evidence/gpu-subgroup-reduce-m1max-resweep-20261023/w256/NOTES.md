# gpu-subgroup-reduce-m1max-resweep-20261023/w256 — the flip-contract anchor cell re-swept (JUN-58)

Tick: amu-gpu chain (bot/amu-gpu-chain). Tracking: JUN-58 (the Apple vendor
row), parent JUN-55. One row of work: one MEASUREMENT -- the re-sweep the
honest LEFT named as the real remainder ("A re-sweep of any measured row ...
is a MEASUREMENT row, one vendor at a time"), run on the only vendor this
host has (Apple Silicon).

## What this is a re-sweep OF

The flip contract's anchor cell: :baseline vs :subgroup-reduce on the MSL
route, Apple M1 Max (reported subgroup size 32), W = 256, n = 1,000,003,
the three operators -- the exact cell
docs/evidence/gpu-subgroup-reduce-m1max-20261023/ measured at 08:34 JST
today (commit 009c86ef, "the first hardware comparison of the emitted
arms"). This re-sweep ran at ~14:30 JST the same day, as a fully separate
session: fresh emit, fresh xcrun metal/clang builds, 6 fresh processes.
Same-day replication across sessions -- NOT cross-day, and it does not
claim temporal stability beyond this day.

## What ran (real hardware, real emitted bytes)

- Same driver as every cell: `python3 scripts/gpu-subgroup-reduce-metal-measure.py
  --out docs/evidence/gpu-subgroup-reduce-m1max-resweep-20261023/w256`
  (defaults = the anchor cell exactly: --runs 6 --workgroup 256
  --elements 1000003 --op-order sum,max,min). The historical cell's record
  was NOT touched: the run wrote only into this directory (the driver's
  named FOOTGUN -- default --out rewrites the historical run-log -- was
  avoided by passing --out).
- Device: Apple M1 Max; reported simdgroup size 32 (probe instrument,
  `[[threads_per_simdgroup]]`), in every fresh process's header.
- Protocol: identical to the anchor cell -- 6 fresh-process runs, 20
  interleaved pairs per operator per run with alternating AB/BA order, 2
  warmup submits per arm discarded, Metal GPU timestamps
  (GPUStartTime->GPUEndTime) around one reduce dispatch, verified
  read-back of the partials (run-log.txt: 720 sample lines = 6 x 3 x 2 x
  20; verify ok=1 on every arm of every operator of every run).
- Headers (the misshape-defect exposure point): every one of the six
  runs prints n=1000003, workgroup=256, op_order=sum,max,min. The shape
  and the op-order were forwarded, not defaulted-into-being-measured-
  silently. This is also the FIRST FULL HARDWARE RUN of the argv-corrected
  harness (7b053893's `argc >= 5` op-order gate fix, which until now had
  only the parse matrix and a source-pinning test behind it): the fixed
  gate forwarded the 5th positional correctly on all 6 runs.

## The numbers (summary.md, full tables; paired statistic = ADR-0358's)

| operator | paired ratio (median of 6 per-run ratios) | anchor cell 08:34 | shape-2 anchor (cited) |
|---|---|---|---|
| sum | **1.220** (per-run 1.218..1.222) | 1.223 | 1.220-1.227 |
| max | **1.218** (per-run 1.216..1.219) | 1.218 | 1.220-1.227 |
| min | **1.218** (per-run 1.217..1.219) | 1.216 | 1.220-1.227 |

**The anchor cell REPRODUCES.** All three operators land within 0.005 of
this morning's paired medians, same sign (:subgroup-reduce ~22% slower
than :baseline in every operator, every fresh process, both sessions).
The per-run spread is TIGHTER than the anchor cell's (1.216..1.222 vs
1.196..1.226). Absolute per-arm medians moved with the clock regime
(e.g. min-baseline 103,583 ns here vs 89,666 ns at 08:34) while the
paired within-run ratio held -- the same regime-invariance the sweep
protocol was designed around, now observed across sessions too.

Verified read-back, both arms, every run (summary.md, verbatim):
:max and :min bit-identical between arms and against the CPU reference
(3907 partials x 6 runs); :sum arms within 3.05e-5 of each other and
1.58e-5 of the reference -- the low-bit movement rule 2 permits for f32
:sum, reported as data.

## Determinism check (the emitter-identity guard)

`diff -r` of this run's six emitted sources against the historical anchor
cell's shaders/: BYTE-IDENTICAL (empty diff). Per the emit script's own
contract ("If a run of this script changes a file, an emitter changed"),
the two sessions compared the same emitted bytes.

## What this is NOT (nothing upgrades)

- No `:measured?` flag moves, no `:measured-cell` set changes, no
  selection answer changes, no workgroup row (ADR-0355/0358) is touched.
  The flip-set cells this re-sweeps were already `:measured? true`; a
  re-sweep CORROBORATES a measured row, it does not extend the flip set.
- This is not a cross-day replication and not a new shape, width, device
  or route. UNMEASURED scope is unchanged: shapes beyond the two contract
  cells; every Apple device but this M1 Max; W = 32 as a verdict (it is a
  decision); the GLSL arm beyond its LABELED BOOTSTRAP record (blocked on
  a wire-42 execution route, ADR 0371); the NVIDIA/Intel/ARM/AMD variant
  rows entirely (no hardware).
- The channel is the native-Metal harness (ADR-0360 question (1)'s
  2026-10-23 decision admits it as contract-satisfying FOR THE MSL ARM);
  wire 42 still executes SPIR-V through Vulkan only.

## Honest LEFT (the real remainder after this row)

- Re-sweeps of the remaining flip-set cells (the W = 32..1024 band, the
  shape-2 cells) are each their own MEASUREMENT row, one at a time; this
  tick covered only the W = 256 shape-1 anchor.
- Cross-day replication of any cell needs a later-day run (a cron tick on
  another day), not more same-day sessions.
- The blocked/absent-hardware rows stay exactly as the 2026-10-23
  correction record left them.
