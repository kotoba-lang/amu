# The first hardware comparison of the :subgroup-reduce MSL arm vs :baseline (JUN-58)

Tick: amu-gpu chain (bot/amu-gpu-chain). Tracking: JUN-58 (the Apple vendor
row), parent JUN-55. One row of work: one MEASUREMENT -- the interleaved
baseline-vs-variant reduce comparison on the only vendor this host has
(Apple Silicon), the measurement backlog item 2 names.

## What ran (real hardware, real emitted bytes)

- Device: **Apple M1 Max** (32 cores, Metal 4), macOS. The tested device's
  reported subgroup size, read from the runtime
  `[[threads_per_simdgroup]]` binding by the probe instrument: **32**. This
  is the first MEASURED subgroup-size fact for this device class; ADR-0362's
  "Apple's SIMD-group width is 32 per the Metal feature-set tables ... is
  UNVERIFIED here" stays true for the MoltenVK/Vulkan struct it describes --
  this run measured the Metal-native binding, not
  `VkPhysicalDeviceSubgroupProperties`.
- Shaders: the emitter's own bytes, both arms, three operators, W = 256 (the
  measured Apple workgroup row, ADR-0358) -- `accelerator/lower` with
  `:msl-v1` x {:baseline, :subgroup-reduce}, written by
  `scripts/gpu-subgroup-reduce-metal-measure.cljk` into `shaders/` here.
  Nothing is hand-written except the probe instrument and the host harness.
- Protocol (the workgroup sweeps' regime, ADR-0358): 6 fresh-process runs,
  20 interleaved pairs per operator per run with alternating AB/BA order,
  2 warmup submits per arm discarded. Timer: Metal GPU timestamps
  (GPUStartTime -> GPUEndTime) around one reduce dispatch; host
  submit->completion ns recorded as secondary. n = 1,000,003 f32 values in
  [0, 1) (no NaN payloads, no negative zeros -- rule 2's ordinary-value
  domain), padded lanes exercised (n is not a multiple of W).

## The numbers (median GPU ns per dispatch; full tables in summary.md)

| operator | baseline | :subgroup-reduce | paired ratio (median of 6 per-run ratios) |
|---|---|---|---|
| sum | 103,000 | 126,084 | **1.223** |
| max | 102,396 | 125,188 | **1.218** |
| min | 89,666 | 101,625 | **1.216** |

**The variant is ~22% SLOWER than baseline on this device at this shape, in
every fresh process and every operator.** The per-run ratios sit in
1.196..1.226 across all six processes. Absolute per-process medians vary
(run 5 and 6 landed in a lower clock regime -- per-run medians as low as
~33 us), but the paired within-run ratio is stable across those regimes,
which is exactly why the sweep protocol uses the paired statistic. The
design assumption behind the row -- "removing most of the barrier cascade
wins" (ADR-0356's Intel rationale, inherited by the Apple row) -- is NOT
supported on this device at W = 256; it is a design assumption that this
measurement contradicts for the measured cell. What is left open: other W,
other n, other Apple generations, and whether the MSL arm's particular fold
(shuffle loop + cross-SIMD-group tree) or the barrier tree itself is the
loser here.

## Verified read-back (every fresh process, both arms)

- :max and :min: the partials are BIT-IDENTICAL between the two arms and
  against the double CPU reference -- rule 2's ordinary-domain claim is now
  observed on hardware for these inputs (3907 partials x 6 runs, bit-exact).
- :sum: the arms differ by at most 3.05e-5 across partials (vs partial
  magnitudes ~128) and each sits within 1.58e-5 of the CPU reference -- the
  low-bit movement rule 2 permits for f32 :sum. Reported as data
  (`max_abs_vs_other` in summary.md), not hidden behind pass/fail.

## What this is NOT (the locks stay locked)

- This is NOT the measurement ADR-0360's contract names. That contract
  requires the wire-42 route, which does not exist since the C loader
  removal (ADR 0371 -- the provider is the replacement track and is not
  implemented). This run dispatched the MSL arms through the Metal API
  directly (a standalone harness,
  `scripts/gpu-subgroup-reduce-metal-measure.m`, built by
  `scripts/gpu-subgroup-reduce-metal-measure.py`).
- **No `:measured?` flag moves.** Every variant row keeps answering
  `:measured? false`; no workgroup row of ADR-0355/0358 is touched (a
  different axis). The flip stays blocked on (a) the contract's route
  clause and (b) the per-tested-device scoping the flip would need
  (ADR-0358's `:measured-device` machinery exists for workgroup rows only).
- Whether a native Metal harness satisfies the measurement contract, and
  what the Apple row should select given this result (the variant is slower
  in the measured cell), are DESIGN QUESTIONS proposed by this evidence and
  decided nowhere. Recorded as a proposed amendment in ADR-0360.
- This is one workload shape, one W, one device, one operator family.
  Nothing here is optimality evidence for any other configuration.

## Reproduce

    kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)" \
      run-tests.cljk   # unchanged from base for this diff (see below)
    python3 scripts/gpu-subgroup-reduce-metal-measure.py --runs 6

The driver emits, builds (xcrun metal / xcrun clang), runs and records; the
transcripts are compile-log.txt and run-log.txt here, the statistics
summary.md. Build artifacts go to a scratch temp dir and are deleted.

## Gate

This diff touches NO compiler or test namespace -- only `scripts/` (two
measurement scripts), this evidence directory and ADR-0360's amendment
record. The gate rule binds "the namespaces you touched"; there are none.
For the record, the accelerator test family at this commit is green (the
scoped run is in scoped-gate.txt here). The FULL gate
(`kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)" run-tests.cljk`)
is RED AT BASE and unchanged by this diff: it aborts at namespace load with
'Could not find namespace: kotoba.form' (kotoba.compiler.js-value-target
requires it; pinned kotoba-sema a3303527 carries no kotoba/form.cljk) --
the same failure earlier chain commits reproduce on clean checkouts of
their bases.
