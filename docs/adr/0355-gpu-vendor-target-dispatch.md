# ADR-0355 -- Per-vendor GPU target dispatch and provisional workgroup defaults

- Status: accepted; v1 dispatch table implemented, workgroup defaults
  provisional and unmeasured
- Date: 2026-10-18

## Decision

The accelerator pipeline gains one deterministic dispatch table,
`kotoba.compiler.accelerator-targets`, that turns a device descriptor
(`:vendor-id` or `:vendor` name, optional `:api`) into a vendor keyword, one
of ADR-0002's three emission targets, and a workgroup size.

| vendor  | PCI id | api-less default target | provisional workgroup | execution width |
|---------|--------|-------------------------|-----------------------|-----------------|
| nvidia  | 4318   | cuda-v1                 | 256                   | 32 (warp, assumed) |
| apple   | 4203   | msl-v1                  | 256                   | **32 (MEASURED, M1 Max)** |
| intel   | 32902  | wgsl-v1                 | 128                   | 8/16/32 (subgroup, assumed 32) |
| arm     | 5045   | wgsl-v1                 | 128                   | 4-32 (Mali, assumed 16) |
| amd     | 4098   | wgsl-v1                 | 256                   | 64 (wavefront, assumed) |
| unknown | --     | wgsl-v1                 | 256                   | --              |

Rules:

1. The functions are TOTAL. An unknown vendor or api answers the documented
   fallback (:unknown / :wgsl-v1 / 256), never a throw. Dispatch time is
   where a refusal costs the most, and a portable default is honest about
   what it is.
2. An api that names its shading language decides outright (:cuda ->
   :cuda-v1, :metal -> :msl-v1, :vulkan/:webgpu -> :wgsl-v1). A missing or
   unknown api falls back to the vendor default.
3. The workgroup values are PROVISIONAL DESIGN DEFAULTS: powers of two
   within ADR-0002's [1, 1024] bound that are multiples of each row's
   execution width. No workgroup size has been measured as tuning on any
   vendor. Measurement is PER FACT: each row carries `:size-measured?` and
   `:execution-width-measured?` with a `:basis` apiece, `recommend` answers
   both flags, and the answer-level `:measured?` is true only when every fact
   in the answer is measured. A fact marked unmeasured may not be reported as
   optimization evidence until hardware measurement (tracked as JUN-57..60)
   replaces it -- and the flag flips for that fact and that vendor only.
4. Same descriptor in, same map out. The table adds no nondeterminism to the
   byte-identical artifact regime of ADR-0002.

## Honest state (measured 2026-10-18, amu at 9b946bb2; row flip 2026-10-19)

- Implemented: the ADR-0002 emitters (WGSL / CUDA C / MSL) and this dispatch
  table with tests.
- Measured (the one flipped fact): apple execution width = 32
  (gl_SubgroupSize at W = 64), Apple M1 Max via MoltenVK (Vulkan 1.3.357),
  three verified processes, `:execution-width-measured? true` with the
  evidence at `docs/evidence/gpu-subgroup-measured-row-m1max-20261019`.
  The measurement says nothing about Intel or ARM devices: their execution
  widths stay UNMEASURED.
- Unmeasured (flips still barred): every workgroup SIZE is provisional for
  every vendor. The workgroup sweeps on this host (2026-10-18/19, six
  protocols) found no stable size effect above noise and one kernel-shape-
  conditional W=32 penalty; that is not a tuning result for 256, so the
  apple size row's flip bar (a protocol whose noise floor is below the
  effect it claims, more than six runs of one shape) is unmet.
- Not implemented: wiring accelerator lowering into the compile pipeline (its
  only callers are tests), any CUDA or Metal execution path (the runtime
  `:gpu/compute` wire 42 is Vulkan only, `tools/kexe_gpu_vulkan.c`), and
  every vendor optimization. Device class does not branch the v1 table.
- selfhost (`docs/selfhost-priority.md`) is paused at the 2026-10-12
  checkpoint. This work is owner-directed (2026-10-18) alongside it and
  claims no selfhost evidence.

## Consequences

- One place decides vendor -> target -> workgroup. The runtime loader and the
  emitters stop inventing their own defaults as they get wired up.
- Per-vendor optimization (NVIDIA / Apple / Intel / ARM) replaces provisional
  rows with measured ones one row at a time, and flips `:measured?` only for
  rows that carry hardware evidence. First flip: apple execution width
  (2026-10-19, JUN-58). Flips are per fact -- a measured execution width
  does not make the row's workgroup size measured.
- An unmeasured row is labeled unmeasured in the code and here, so a reader
  can tell a design default from a tuning result without trusting prose.
