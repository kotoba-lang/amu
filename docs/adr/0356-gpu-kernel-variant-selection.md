# ADR-0356 -- Per-vendor kernel variant selection for the accelerator KIR

- Status: accepted as design. Row states are tracked individually below;
  only `:baseline` is implemented on main at this date.
- Date: 2026-10-18
- Tracking: JUN-55 (parent); the NVIDIA row is JUN-57, the Intel row is
  JUN-59. ARM (JUN-60) is deliberately not designed in this ADR.

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

The accelerator pipeline gains one total, deterministic variant table,
`kotoba.compiler.accelerator-variants`: `select-variant` answers
`(vendor, kir, target) -> {:variant :measured? :basis}`. The emission target
is part of the key: a descriptor may name `:cuda` or `:metal` for a
vendor-classified Intel device (`accelerator_targets.cljk:80-90`), and a
variant the target's emitter does not admit is never selected (rule 3)
-- selection consults the selected target's emitter admission, never vendor
identity alone. This is the design home of
that table; the NVIDIA row lands through it (PR #1331) and the Intel row is
specified here ahead of its implementation.

Relationship to the existing decisions: ADR-0355 decides vendor -> emission
target -> workgroup size; this ADR decides (vendor, kernel shape) -> emitted
code variant. ADR-0002 defines the KIR and the three emitters. A variant
replaces no ADR-0355 workgroup row -- the two axes stay independent.

Rules (all of them inherited from the table's first implementation, PR #1331,
and binding on every future row):

1. **Totality.** A vendor or kernel shape outside the table answers
   `:baseline`, never a throw. Selection time is where a refusal costs the
   most, and a portable kernel that runs is worth more than an error.
2. **Semantics preservation.** A variant groups the same admitted elements in
   a different order: f32 `:sum` may differ in the low bits across variants;
   `:max`/`:min` are order-independent and must agree bit-for-bit **within the
   ordinary-value domain: non-NaN payloads and no negative zeros**. Floating-point
   `max`/`min` are not bitwise order-independent over NaN payloads or signed
   zeros -- regrouping may select a different NaN payload or zero sign -- so this
   rule is claimed only for admitted inputs that exclude both (normative for
   `:max`/`:min` kernels: f32 buffer values must be non-NaN and not -0.0), unless
   an implementation canonicalizes (NaN -> one canonical qNaN, -0.0 -> +0.0
   before the reduce) and tests the canonicalized regime. Until either exclusion
   or canonicalization is implemented and tested, bit-for-bit agreement is scoped
   to the ordinary domain and the exceptional-value behavior is UNMEASURED.
3. **Emission admission first.** A variant is selected only for a target the
   emitter admits it for. A variant that cannot be emitted is never selected;
   implementing a row means adding its emission before (or together with) its
   selection predicate.
4. **The UNMEASURED lock.** Every non-baseline answer carries
   `:measured? false` and a `:basis` text. The flag flips only when a
   hardware measurement replaces the basis text of that row. Nothing in this
   table is optimization evidence until then.
5. **Determinism.** Same (vendor, kir) in, same map out, forever -- the table
   adds no nondeterminism to ADR-0002's byte-identical artifact regime. With
   variant selection, the regeneration input of the sealed artifact is
   `(kir, target, variant)`: the selected variant is recorded in the seal, and
   the verifier at `accelerator.cljk:117-135` regenerates with it. Artifacts
   sealed before this rule are verifiable only in the baseline regime (their
   code was generated without a variant choice). A variant-dependent artifact
   whose seal lacks the variant fails verification -- the variant is never
   inferred from the code.
6. **Device capability, not vendor identity.** A vendor row's predicate holds
   only on a device that exposes the subgroup capability the variant needs:
   the Vulkan path queries the subgroup properties (subgroup size and the
   supported stages/operations for the reduce) and requires a subgroup size
   that divides `W`; the WGSL path treats subgroups as the optional feature
   they are. Vendor identity and `W >= 32` alone never establish this -- a
   device without the feature, or with a subgroup larger than `W`, answers
   `:baseline` (rule 1: total, no throw).

## Rows

| variant | vendor | shape | state | measurement |
|---------|--------|-------|-------|-------------|
| `:baseline` | all | all | implemented (main; ADR-0002 emitters) | the only variant with an execution path today |
| `:warp-shuffle-reduce` | nvidia | reduce, W >= 32 | implemented in flight (PR #1331, open and unmerged at this date); CUDA emission only | UNMEASURED: no NVIDIA hardware, and the CUDA emitter has no execution path in this repo |
| `:subgroup-reduce` | intel | reduce, W >= 32 | **accepted design only (this ADR)**; nothing implemented | UNMEASURED: no Intel hardware |
| (ARM row) | arm | -- | **proposed**: neither designed nor implemented here | -- |

## Intel `:subgroup-reduce` (JUN-59) -- the design

**Rationale (a design assumption, not a measurement).** The baseline tree
reduce pays `log2(W)` barrier stages in its cascade -- 7 at W = 128, 8 with
the initial load barrier (mechanically checked for this ADR). Intel subgroups
(8/16/32, device-chosen) support subgroup arithmetic (Vulkan
`VK_KHR_shader_subgroup` arithmetic; WGSL subgroups extension). Folding
within a subgroup needs no barriers and no shared memory, leaving one write
barrier plus a short cross-subgroup tree over the `W/S` partials: at W = 128
that is 4 / 3 / 2 stages for S = 8 / 16 / 32 (vs the baseline's 7). The
design assumption -- UNMEASURED -- is that removing most of the barrier
cascade wins on Intel hardware.

**Safety condition: `S` divides `W`.** The KIR admits workgroup sizes that
are powers of two <= 1024 (ADR-0002 / `accelerator/validate!`). Every
admissible `W >= 32` is a multiple of 32, hence of 8, 16 and 32 alike
(mechanically checked across all eleven admissible sizes: every one with
`W >= 32` is divisible by 8, 16 and 32). So the
selection predicate is: vendor `:intel`, op `:reduce`, operator in
`{:sum :max :min}`, `W >= 32`; smaller workgroups answer `:baseline`.

**The emitted code must be subgroup-size-parametric.** It queries the
subgroup size at runtime (`gl_SubgroupSize` / the WGSL subgroup builtin) and
never bakes 32 into the fold. This is the structural difference from the
NVIDIA row, whose `__shfl_down_sync` loop bakes warp width 32 into the
emission because a CUDA warp is fixed. Intel's subgroup size is a device
choice; an emission that assumes 32 would be wrong on most Intel devices.

**Execution-path honesty (rule 3).** The runtime `:gpu/compute` (wire 42)
executes through Vulkan only (`tools/kexe_gpu_vulkan.c`). The in-flight
emitters admit `:baseline` for WGSL/MSL and `:warp-shuffle-reduce` for CUDA
only. Note the compile-step gap precisely: `kgpu_new_pipeline`
(`tools/kexe_gpu_vulkan.c:397-418`) opens an ALREADY COMPILED SPIR-V file
and passes it to `vkCreateShaderModule`; the repository contains no
`glslangValidator` invocation. Implementing this row therefore needs (a) a
Vulkan-side emission admitted for `:subgroup-reduce` -- and a specified
GLSL/WGSL -> SPIR-V compilation step (a `glslangValidator` invocation in the
pipeline, or a build step whose compiled artifact is the file the loader
opens) that the current wire-42 path lacks -- before
`select-variant` may ever
answer it, and (b) an Intel device to run it. Until (a) lands the selection
row must not exist; until (b) lands the row stays UNMEASURED.

**Measurement contract (JUN-59).** The row flips `:measured?` only on an
interleaved baseline-vs-variant reduce comparison on an Intel device, with
read-back verification (the protocol the workgroup sweeps established:
fresh-process runs, interleaved samples, verified read-back words), recorded
under `docs/evidence/`. The measurement is keyed to the TESTED DEVICE CLASS
-- at minimum the device name and its subgroup size -- not to the vendor
row: a result on one Intel generation or subgroup width does not flip
`:measured?` for other Intel devices, which keep their own
`:measured? false` answers until measured (rule 4's lock is per sufficient
descriptor dimension, not per vendor).
Until then no report may cite this row as
optimization evidence, and `:measured? false` is part of every answer.

## Consequences

- PR #1331's namespace docstring citation "(ADR-0356)" resolves to this
  file; the NVIDIA row is citable as *implemented in flight, UNMEASURED*.
- JUN-59 has a concrete, mechanically checkable row: implement the emission,
  then the predicate, then measure on hardware. The three states stay
  distinguishable at every step.
- ARM (JUN-60) remains proposed. Its row is a separate design decision --
  one vendor per decision -- and nothing here should be read as having
  designed it.
- The provisional workgroup rows of ADR-0355 are untouched by this ADR and
  remain `:measured? false` on their own axis.
