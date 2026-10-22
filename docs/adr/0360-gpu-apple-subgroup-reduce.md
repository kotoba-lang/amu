# ADR-0360 -- The Apple row: the subgroup-size-parametric reduce on the Vulkan route

- Status: accepted as design. The selection row is implemented 2026-10-23
  (code + tests in `kotoba.compiler.accelerator-variants`); the row is
  UNMEASURED.
- Date: 2026-10-23
- Tracking: JUN-58 (Apple). Parent JUN-55. This is one vendor per decision,
  the rule ADR-0356 set and ADR-0357 (ARM) followed.

## Decision

The Apple row of the per-vendor kernel variant table is the SAME
`:subgroup-reduce` variant ADR-0356 designed for Intel and ADR-0357 bound
for ARM: a subgroup-size-parametric intra-subgroup fold, one write barrier,
a cross-subgroup tree over the `W/S` partials. The selection predicate is
vendor `:apple` (as ADR-0355 classifies it: PCI 4203, or an `apple` /
`m1`/`m2`/`m3`/`m4` device-name fragment), op `:reduce`, operator in
`{:sum :max :min}`, `W >= 32`, on the Vulkan route (`:vulkan` or
`:glsl-v1`), under ADR-0356 rule 6's capability gate: the device
descriptor must report the fold's subgroup operations (`:subgroup-ops`
containing `:basic` and `:shuffle-relative`) and a subgroup size
(`:subgroup-size`) that divides `W`. Every other answer -- the MSL route, a
device that confirms no capability, another shape -- is `:baseline`. The
rules of ADR-0356 bind this row unchanged, and ADR-0357's P1 (the `:sum`
association scope) and P2 (subgroup IDs, not `lid` arithmetic) bind the
emission byte-for-byte: this row reuses the existing emission, it emits
nothing new.

## Why the Vulkan route, and not MSL

ADR-0355's api-less Apple default target is `:msl-v1`, but there is no
Metal execution path in this repository: the runtime `:gpu/compute`
(wire 42) route is Vulkan at every layer that ever had one (the removed
loader brokers, and ADR 0371's provider plan), and JUN-58's measurement
path is MoltenVK. The MSL emitter admits `:baseline` only (ADR-0002), so
ADR-0356 rule 3 keeps the MSL route at `:baseline`; a Metal simdgroup row
on the MSL route is NOT designed here and nothing in this ADR should be
read as designing it. The measurement this row waits on runs GLSL ->
SPIR-V through glslang (ADR-0359 decision 2's sealed build step) on
MoltenVK.

## Design facts (vendor documentation, not measurements)

Metal's SIMD-group width is 32 (Apple documentation), and MoltenVK's
subgroup surface follows it: the MoltenVK runtime guide lists
`VK_EXT_shader_subgroup_ballot`, `VK_EXT_shader_subgroup_vote`,
`VK_KHR_shader_subgroup_extended_types` and `VK_EXT_subgroup_size_control`
(requiring Metal 2.1 on Mac), and the MoltenVK 1.4.2 notes describe the
macOS subgroup size as 32-wide SIMD groups. Nothing here has PROBED this
host's MoltenVK for a subgroup size (the probe that could is removed with
the loader); these are documentation facts, and the rule-6 gate consumes
the descriptor's REPORTED facts, not the vendor name -- so the row is
admitted only for a device that says so. The emission queries the width at
runtime (`gl_SubgroupSize`) and bakes nothing, so the same bytes are
correct for any width a device reports. The stage arithmetic of ADR-0356
(W = 128, S = 32: 2 stages against the baseline's 7) applies unchanged and
is stage counting, not a speed claim. The design assumption -- UNMEASURED
-- is the same one the Intel and ARM rows carry: removing most of the
barrier cascade wins. No Apple hardware has run this variant here, and no
report may cite this row as optimization evidence.

## Open contract gap (named, not hidden)

Rule 6 consumes descriptor facts (`:subgroup-size`, `:subgroup-ops`) whose
producer does not exist. The wire-42 answers of the ADR-0371 provider plan
carry no such facts: `INFO` is the four fields `<device>|<api>|<maxWgX>|<unified>`
and `DEVCLASS` is one class word. So this row is selected today only for a
descriptor that a future probe or provider supplies with subgroup facts; a
descriptor that reports none fails closed to `:baseline` (rule 1: the
portable variant runs). Producing the facts -- an extended probe answer or
a provider request -- is a separate design decision and is not made here.

## Measurement contract (JUN-58)

The row flips `:measured?` only on an interleaved baseline-vs-variant
reduce comparison with verified read-back (the protocol the workgroup
sweeps established: fresh-process runs, interleaved samples, verified
read-back words), on a NAMED Apple device, recorded under
`docs/evidence/`. The measurement is keyed to the tested device (name and
its reported subgroup size), not to the vendor row: one Apple generation
measured does not flip `:measured?` for any other (ADR-0356 rule 4's lock
is per sufficient descriptor dimension). It also cannot be taken until a
wire-42 route exists again (ADR-0371 provider; ADR-0355's honest state),
so today the row stays `:measured? false` in every answer, and the
provisional workgroup rows of ADR-0355 are untouched by this ADR.
