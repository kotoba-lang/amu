# ADR-0355 -- Per-vendor GPU target dispatch and provisional workgroup defaults

- Status: accepted; v1 dispatch table implemented, workgroup defaults
  provisional and unmeasured
- Date: 2026-10-18

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

The accelerator pipeline gains one deterministic dispatch table,
`kotoba.compiler.accelerator-targets`, that turns a device descriptor
(`:vendor-id` or `:vendor` name, optional `:api`) into a vendor keyword, one
of ADR-0002's three emission targets, and a workgroup size.

| vendor  | PCI id | api-less default target | provisional workgroup | assumed execution width |
|---------|--------|-------------------------|-----------------------|-------------------------|
| nvidia  | 4318   | cuda-v1                 | 256                   | 32 (warp)               |
| apple   | 4203   | msl-v1                  | 256                   | 32 (SIMD-group)         |
| intel   | 32902  | wgsl-v1                 | 128                   | 8/16/32 (subgroup)      |
| arm     | 5045   | wgsl-v1                 | 128                   | 4-32 (Mali)             |
| amd     | 4098   | wgsl-v1                 | 256                   | 64 (wavefront)          |
| unknown | --     | wgsl-v1                 | 256                   | --                      |

Rules:

1. The functions are TOTAL. An unknown vendor or api answers the documented
   fallback (:unknown / :wgsl-v1 / 256), never a throw. Dispatch time is
   where a refusal costs the most, and a portable default is honest about
   what it is.
2. An api decides its route outright (:cuda ->
   :cuda-v1, :metal -> :msl-v1, :vulkan -> :glsl-v1, :webgpu -> :wgsl-v1). A
   missing or unknown api falls back to the vendor default. Amended
   2026-10-22 by ADR-0359 decision 3: :vulkan answered :wgsl-v1 before;
   Vulkan names no shading language (it opens compiled SPIR-V), and the only
   source-to-SPIR-V path this repository owns is glslang from GLSL. WebGPU
   keeps its language; the api-less vendor defaults are unchanged.
3. The workgroup values are PROVISIONAL DESIGN DEFAULTS: powers of two
   within ADR-0002's [1, 1024] bound that are multiples of each vendor's
   published execution width. Nothing in this repository has measured them.
   `recommend` marks every answer `:measured? false`, and no caller may
   report these values as optimization evidence until hardware measurement
   (tracked as JUN-57..60) replaces the row it stands on. [SUPERSEDED IN
   PART 2026-10-19 by ADR-0358: four of the six rows (:nvidia, :apple,
   :intel, :amd) are MEASURED -- "nothing has measured them" and "every
   answer :measured? false" stopped being true that day, and `recommend`'s
   flag is scoped to each row's one named measured device (uB5G, amended
   2026-10-22). The provisional rule above still binds :arm and :unknown.
   The code docstring that carried the old state was corrected 2026-10-24,
   docs/evidence/gpu/workgroup-prose-rootcause-20261024.txt.]
4. Same descriptor in, same map out. The table adds no nondeterminism to the
   byte-identical artifact regime of ADR-0002.

## Honest state (measured 2026-10-18, amu at 9b946bb2)

- Implemented: the ADR-0002 emitters (WGSL / CUDA C / MSL) and this dispatch
  table with tests.
- Not implemented: wiring accelerator lowering into the compile pipeline (its
  only callers are tests), any CUDA or Metal execution path (the runtime
  `:gpu/compute` wire 42 is Vulkan only, `tools/kexe_gpu_vulkan.c`), and
  every vendor optimization. Device class does not branch the v1 table.
  SUPERSEDED 2026-10-22 -- see the loader-removal bullet below.
- selfhost (`docs/selfhost-priority.md`) is paused at the 2026-10-12
  checkpoint. This work is owner-directed (2026-10-18) alongside it and
  claims no selfhost evidence.
- Loader removal 2026-10-22 (amu 36479076, JUN-29; `docs/c-loader-removal.md`;
  replacement route amu ADR 0371). The `:gpu/compute` execution path named
  above is GONE: the loader's GPU brokers (`tools/kexe_gpu_vulkan.c`,
  `tools/kexe_gpu_metal.m`) and the probe harnesses (`scripts/test-gpu-*.cljk`)
  were removed with the C loader. Wire 42 has no route at any layer today --
  the seed checker refuses it (E2115) and the static runtime serves wires
  35/37/38/39 only. The accepted replacement is ADR 0371's GPU provider
  process: its decision 1 (the platform boundary) is owner-accepted
  2026-10-22 and its steps 1-2 (protocol table, runtime transport) are
  implemented; the provider, launcher and seed admission are NOT. Until
  they land, NO wire-42 measurement is re-takeable on any host, the
  JUN-58 measurement wiring (Apple, this host) is BLOCKED on the provider,
  and the per-vendor workgroup sweep (JUN-57..60 rows) cannot run.
- The measured rows of ADR-0358 keep their provenance and their label:
  measured 2026-10-18/19 through the then-existing loader path on the M1
  Max. They stand as measurements OF THAT PATH. Nothing re-measures them
  today; they are not provisional (the `:measured?` flags stay as ADR-0358
  set them) and they are not re-derivable until a provider answers INFO.

## Consequences

- One place decides vendor -> target -> workgroup. The runtime loader and the
  emitters stop inventing their own defaults as they get wired up.
- Per-vendor optimization (NVIDIA / Apple / Intel / ARM) replaces provisional
  rows with measured ones one row at a time, and flips `:measured?` only for
  rows that carry hardware evidence.
- An unmeasured row is labeled unmeasured in the code and here, so a reader
  can tell a design default from a tuning result without trusting prose.
- Reporting landed before branching (2026-10-19; shape settled 2026-10-22):
  the loader reports device class as its own wire-42 request, `DEVCLASS` ->
  one word (discrete|integrated|virtual|cpu|other -- the chosen device's
  VkPhysicalDeviceType as a stable token, `tools/kexe_gpu_vulkan.c`), and
  `device-class` maps that word into `device-classes` (total: a word outside
  the loader's five answers :unknown). The earlier fifth-INFO-field shape is
  superseded (owner-directed merge 740caee4): the INFO answer is exactly the
  four fields `<device>|<api>|<maxWgX>|<unified>`, and the harnesses read it
  that way (`scripts/test-gpu-compute.cljk` for INFO,
  `scripts/test-gpu-devclass.cljk` for DEVCLASS). SUPERSEDED 2026-10-22
  (36479076): both harnesses and the DEVCLASS producer (the broker) are
  removed. `device-class`'s five-word map stays implemented and tested as a
  pure map; a future ADR-0371 provider must answer the same five words, or
  the map is re-pointed at the provider's class token -- that decision lands
  with the provider, and until then no DEVCLASS answer exists to map. The
  v1 table still does not branch on device class; when a row needs the
  branch, it lands with the measurement that justifies it (JUN-57..60).

## Amendment (2026-10-25, the measurement channel for row flips)

The Consequences bullet "flips `:measured?` only for rows that carry
hardware evidence" gains its channel rule (the 2026-10-25 licensing
decision, record `docs/evidence/gpu/wgsl-wallclock-row-mapping-20261025.txt`):
hardware evidence for a workgroup row is evidence from THE ROW'S OWN
CHANNEL -- the ADR-0358 protocol (one workload shape, six LocalSize
variants differing in nothing else, within-run paired size-vs-size
comparison, each size timed twice with the first submit discarded,
submit->fence host clock) taken on the wire-42 loader path the rows'
provenance names, or its ADR-0371 provider successor once one answers
INFO. A read on any other channel is a route-level measurement OF THAT
CHANNEL and answers no row -- the same provenance discipline that keeps
the ADR-0358 rows labelled "of that path" cuts both ways.

Applied the day it was decided: the 2026-10-25 Chrome 155 Dawn/Metal
wall-clock read of the two WGSL reduce arms (M1 Max) maps onto NO row
-- different route (a third channel even for Apple, where ADR-0358
already disclaims MoltenVK as "not a native Metal path"), different
workload family (reduce kernels, not the one ewise-FMA shape),
arm-vs-arm pairing at fixed W rather than within-run size-vs-size
pairing, and no clock/thermal regime control. Its batch32 argmin
W = 32 in 11/12 shape-op-arm rows (re-derived from the committed log;
the timing commit's "10/12" does not re-derive) would CONTRADICT the
kept `:apple` 256 if it were mapped -- it is not, and the channel rule
is what keeps that contradiction out of the table. No row moves; the
provisional `:arm`/`:unknown` rows stay provisional (`:measured?
false`). REOPEN CONDITION: a row run on the row's own channel
(JUN-57..60, blocked on the ADR-0371 provider) is new evidence, as is
a future amendment that names a new row channel with its own paired
size protocol. Nothing else reopens the mapping.

## Dated note (2026-10-27, JUN-59 probe: the Intel host's ANV step)

The Intel issue's named first step -- "is ANV/mesa usable for
measurement at all?" -- is ANSWERED YES at the fleet's one Intel host
(aiueos-6600hs-1; the 2026-10-18 note's "vulkaninfo shows only
llvmpipe, ANV suspected unsupported" does not reproduce). ANV (Mesa
25.2.8, `xe` kernel driver) enumerates "Intel(R) Graphics (BMG G31)"
(8086:e223, DISCRETE_GPU) with compute-stage subgroups (size 32, all
eight core VkSubgroupFeatureFlagBits) and maxComputeWorkGroupSize
1024; the llvmpipe-only view is exactly the view of an account without
`/dev/dri/renderD128` access (nobody: llvmpipe only, render-node open
denied; aiueos/root: both devices). PROBED host facts, not
optimization evidence: no timing ran, no row moves, and a subgroup
8/16/32 measurement on this host is a future row whose channel
standing under the 2026-10-25 rule is UNDECIDED. Evidence:
`docs/evidence/gpu/intel-anv-probe-20261027/` (record.txt is the
finding).
