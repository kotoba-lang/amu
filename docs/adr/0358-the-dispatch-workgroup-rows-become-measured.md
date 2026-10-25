# ADR-0358 -- The dispatch workgroup rows become measured

- Status: accepted and implemented (JUN-85 optimize stage)
- Date: 2026-10-19

> **Dated note (2026-10-24, ADR 0371).** The GPU execution path this ADR
> refers to is deleted: the C loader `tools/kexe_loader.c`, and wire 42's
> `:gpu/compute` brokered by `tools/kexe_gpu_vulkan.c`. ADR 0371 replaced
> it with a provider process that the static launcher starts and that
> speaks the same wire-42 protocol. Since #1510 two things hold: main's
> compiler refuses that provider's `--format platform-linked` build, and
> its qualifications are outside mandatory native CDCI (`AGENTS.md`). So
> no current route executes a GPU artifact. The text below is kept as
> written.

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
