# ADR-0364 -- The AMD row: the subgroup-size-parametric reduce on the Vulkan and WGSL routes

- Status: accepted as design. The selection row is implemented 2026-10-23
  (code + tests in `kotoba.compiler.accelerator-variants`); the row is
  UNMEASURED.
- Date: 2026-10-23
- Tracking: JUN-84 / Linear AWAI-40 (AMD / RDNA). Parent JUN-55 / AWAI-35.
  One vendor per decision, the rule ADR-0356 set and ADR-0357 (ARM),
  ADR-0360 (Apple), ADR-0361 (NVIDIA) and ADR-0363 (Intel/ARM on WGSL)
  followed.

## Decision

`:amd` gains the row the other four vendors already carry: the SAME
`:subgroup-reduce` variant of ADR-0356 -- a subgroup-size-parametric
intra-subgroup fold, one write barrier, a cross-subgroup tree over the
`W/S` partials -- on TWO routes:

- the Vulkan route (`:vulkan` / `:glsl-v1`), where every designed row
  lives and the one route that has ever executed anything here (RADV is
  AMD's Vulkan driver; the 2026-10-18 wire-42 probe answered
  `AMD Radeon 680M (RADV REMBRANDT)|1.4.318|1024|1` on the aiueos box --
  a probe reading, not a measurement of this variant); and
- the WGSL route (`:webgpu` / `:wgsl-v1`), because `:wgsl-v1` is `:amd`'s
  vendor-DEFAULT emission target for an api-less device
  (`vendor-default-target`), the exact rationale ADR-0363 used to put
  Intel and ARM on this route.

The selection predicate is vendor `:amd` (as ADR-0355 classifies it: PCI
4098 / 0x1002, or a `radeon` / `amd` device-name fragment), op `:reduce`,
operator in `{:sum :max :min}`, `W >= 32`, under ADR-0356 rule 3
(emission admission -- both routes admit `:subgroup-reduce` since
2026-10-23) and rule 6's capability gate: the descriptor must report the
fold's subgroup operations (`:subgroup-ops` containing `:basic` and
`:shuffle-relative`) and a subgroup size (`:subgroup-size`) that divides
`W`. AMD has no compute-capability contract (there is no AMD analogue of
the CUDA row's sm_70+ floor): an absent capability is not a refusal, and
nothing beyond the shared gate binds this row. Every other answer is what
the rules already say: `:amd` on the MSL or CUDA routes (other vendors'
native routes), any other vendor (`:unknown`, `:qualcomm`, ...), another
shape, or a device that confirms no capability answers `:baseline`.

## RDNA wave 32 / wave 64: the width is queried, never dispatched on

This is the answer to AWAI-40's scope item 1 (how the gfx9/10/11 wave
size difference is handled): it is NOT handled at selection time, and
that is the design. RDNA devices choose the wave size per shader
(wave32 or wave64 -- the hardware subgroup size on the Vulkan path), and
a selection table that picked a fold width from the vendor name would be
wrong on one of the two. The emission already queries the width at
RUNTIME (`gl_SubgroupSize` on the GLSL arm, the WGSL subgroup builtin on
the WGSL arm) and never bakes it, so one emission is correct under both
waves; rule 6's divisibility gate (`S | W`) admits both waves for every
KIR-admitted workgroup row (32..1024 are powers of two, and both 32 and
64 divide all of them). The measured workgroup row for `:amd` (1024,
ADR-0358) is a DIFFERENT axis and is unchanged here; it too is compatible
with both waves.

Not designed, named rather than hidden (AWAI-40 scope items 2 and 3):

- A wave32 shuffle/DPP reduce row (RDNA `v_readlane`/`v_writelane`, DPP
  permutes) is NOT designed. It would be AMD's analogue of
  `:warp-shuffle-reduce`, it would bake a wave width the device chooses,
  and its benefit is exactly the unmeasured assumption the shared row
  already carries. The parametric fold is the designed answer until a
  measurement says otherwise.
- RDNA-specific instructions (`v_fma_f32`, DPP, `ds_swizzle`) are not
  lower targets for this repository: the emitters answer GLSL / WGSL /
  MSL / CUDA SOURCE and instruction selection belongs to the consuming
  driver's compiler (RADV's LLVM). No `:amd`-native emission arm is
  designed or needed for this row, and AWAI-40 scope item 3 is closed as
  "not lowerable here, by construction", not as a gap.

## Design facts (vendor documentation and one probe reading, not measurements)

AMD's execution width is the wave: 64 on GCN/CDNA, 32 or 64 on RDNA
(shader-chosen). Vulkan subgroup support (core 1.1) exposes the
shuffle-relative operations the fold needs on RADV; rule 6 consumes the
descriptor's REPORTED facts, not the vendor name, so the row is admitted
only for a device that says so. Nothing here has measured this variant on
AMD hardware. What IS measured for AMD, and is NOT this row: ADR-0358
replaced the AMD workgroup row with a measured one (1024, 5/6 paired-run
wins over the provisional 256, Radeon 680M / RADV) -- a workgroup size
measurement on one workload shape, nothing more. Every `select-variant`
answer for `:amd` keeps `:measured? false`, and no report may cite this
row as optimization evidence until a hardware measurement replaces its
basis.

## Consequences

- `kotoba.compiler.accelerator-variants` selects `:subgroup-reduce` for
  `:amd` on the Vulkan and WGSL routes under the shared gate; the
  "no designed row" clause in its docstrings is superseded by this ADR.
- ADR-0363's consequence "`:amd`, `:unknown`, `:qualcomm` and any other
  vendor keep answering `:baseline` on every route" is SUPERSEDED as to
  `:amd` (2026-10-23, this ADR): `:unknown`, `:qualcomm` and every other
  vendor keep answering `:baseline` everywhere; `:amd` answers on the
  Vulkan and WGSL routes and `:baseline` elsewhere. Apple and NVIDIA keep
  their ADR-scoped routes and still answer `:baseline` on the WGSL route.
- The route matrix is now complete for all five classified vendors:
  Intel rides Vulkan+WGSL (ADR-0356/0363), ARM rides Vulkan+WGSL
  (ADR-0357/0363), Apple rides Vulkan+MSL (ADR-0360), NVIDIA rides
  Vulkan+CUDA (ADR-0361), AMD rides Vulkan+WGSL (this ADR).
- The measurement contract is unchanged and per-vendor: `:amd`'s variant
  row needs an AMD measurement channel (the ADR 0371 provider, whose
  SUBGROUP answer would fill rule 6's keys on the Vulkan route); until
  one exists the row fails closed without a filled descriptor, exactly
  like every other row.
