# ADR-0358 -- The dispatch workgroup rows become measured

- Status: accepted and implemented (JUN-85 optimize stage)
- Date: 2026-10-19

## Decision

Four of ADR-0355's six provisional workgroup rows are replaced by measured
rows: a hardware measurement now chooses each size, and `recommend` answers
`:measured? true` for those vendors. `:arm` (no Mali hardware) and `:unknown`
stay provisional and keep `:measured? false`.

Measurement: the wire-42 workgroup sweep (scripts/gpu-workgroup-sweep,
test/fixtures/gpu/gpu-workgroup-sweep.kotoba). One workload shape -- 2^20
threads, f32 ewise FMA, 256 FMAs per thread -- compiled to six SPIR-V files
whose ONLY difference is LocalSize (32/64/128/256/512/1024), one dispatch per
size, submit->fence host clock, each size timed twice per run with the first
submit discarded as warmup. Paired runs on the measurement hosts named in
JUN-85. Raw runs: docs/evidence is not written; the runs live in the JUN-58 /
JUN-85 records and the harness reproduces them.

| vendor | host | runs | measured outcome | row |
|---|---|---|---|---|
| amd | aiueos-node-260910, Radeon 680M (RADV) | 6 | 1024 won 5/6, 28% faster than the provisional 256 (median 334,528 vs 467,981 ns) | **1024** (was 256) |
| apple | main-2, M1 Max (MoltenVK) | 16 | 32-1024 medians within ~5%, no size won more than 6/16 | 256 kept (most frequent paired winner) |
| intel | aiueos-6600hs-1, BMG G31 (ANV) | 6 | 32-256 flat within 2% (64 won 4/6 on noise-level margins), 512/1024 marginally slower | 128 kept (subgroup-safe row inside the flat band) |
| nvidia | xavier, Tegra Xavier (nvgpu) | 6 | 128-1024 flat within 2%, 32 is 22% slower | 256 kept (inside the flat band) |

Keeping a size on a flat band rather than chasing a noise-level winner is the
point: the row records what measurement supports, not the luckiest cell.

## Non-claims

- One workload shape. `:measured? true` says a hardware measurement chose the
  size for THIS kernel family; it is not optimality for every kernel, every
  input size, or every driver.
- Apple ran through MoltenVK, not a native Metal path.
- The timer is the loader's host clock around submit->fence; no in-kernel
  clock bracket. Host noise produced 5-12 ms outliers in some cells; paired
  within-run comparison is the statistic used, and none of the flat-band rows
  claims more than the band.
- `:arm` (Mali) has no hardware and stays provisional. AMD's row moved to
  1024, the top of ADR-0002's bound -- nothing here says larger would not be
  better; the bound is a contract, not a measured ceiling.

## Scoping amendment (2026-10-22): the flag is scoped per row, per named device

uB5G's device scoping in `recommend` had two leaks, both now fixed
(`kotoba.compiler.accelerator-targets` and its test):

- a descriptor naming a device through the `:vendor` name key -- the key
  `classify-vendor` matches and `device-from-info` fills with deviceName --
  was NOT counted as named, so `{:vendor "Apple M3"}` inherited the Apple
  row's `:measured? true` although the measurement ran on one M1 Max
  configuration. The old test pinned the leak: the `:vendor`-only spelling
  of the M3 was asserted true while the `:vendor` + `:name` spelling of the
  same device was asserted false.
- the measured-device check was hard-coded to "m1 max", so the measured
  NVIDIA device spelled by name (Tegra Xavier) was denied its own row flag.

Each measured row now carries `:measured-device` -- the name fragment of the
ONE device its measurement ran on, taken from the host column above
(`xavier` / `m1 max` / `g31` / `680m`) -- and a named device keeps the
row's flag only when its name carries that fragment (case-insensitive, the
`name-vendor-fragments` matching idiom). The fragment match is coarse by
design (a name containing the fragment counts as the measured device); it
narrows the flag and never widens it past a named device. An unnamed,
vendor-id-only descriptor keeps the row-level flag as the only available
signal; an INFO-derived descriptor (`:max-workgroup-x` present) still never
transfers it.

No size, no row flag and no measurement changed: this narrows WHEN the
row's flag reaches a caller. Nothing here re-measures anything, and no
`:measured?` row flips.
