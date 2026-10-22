# ADR-0356 -- Per-vendor kernel variant selection for the accelerator KIR

- Status: accepted as design. Row states are tracked individually below;
  only `:baseline` is implemented on main at this date.
- Date: 2026-10-18
- Tracking: JUN-55 (parent); the NVIDIA row is JUN-57, the Intel row is
  JUN-59. ARM (JUN-60) is deliberately not designed in this ADR.

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
| `:subgroup-reduce` | intel | reduce, W >= 32 | **implemented** 2026-10-22 (this ADR's design, on ADR-0359's admitted emission and sealed build step; selection row in `kotoba.compiler.accelerator-variants` under rules 3 + 6) | UNMEASURED: no Intel hardware |
| `:subgroup-reduce` | arm | reduce, W >= 32 | **implemented** 2026-10-22 (the row is DESIGNED in ADR-0357, the ARM decision of record; same emission and selection row as the Intel row) | UNMEASURED: no Mali hardware |
| `:subgroup-reduce` | apple | reduce, W >= 32 | **implemented** 2026-10-23 (the row is DESIGNED in ADR-0360, the Apple decision of record; same emission and selection row as the Intel row, Vulkan route only) | UNMEASURED: no Apple device has run the variant |
| `:subgroup-reduce` | nvidia (Vulkan route) | reduce, W >= 32 | **implemented** 2026-10-23 (the row is DESIGNED in ADR-0361, the NVIDIA decision of record; same emission and selection row as the Intel row, Vulkan route only, plus the sm_70+ floor fail-closed on a reported compute capability) | UNMEASURED: no NVIDIA device has run the variant |

**Amendment (2026-10-22, the JUN-59/JUN-60 selection rows land).** The
execution-path honesty condition (a) below has landed in full: the
Vulkan-side emission is admitted for `:subgroup-reduce` (ADR-0359 decision
1) and the GLSL -> SPIR-V compilation step exists as the sealed build step
(ADR-0359 decision 2, `kotoba.compiler.accelerator-spirv-compile`). The
selection rows therefore exist in code now: `select-variant` answers
`:subgroup-reduce` for `:intel` and `:arm` under rule 3 and rule 6 -- the
device descriptor must report the fold's subgroup operations
(`:subgroup-ops` containing `:basic` and `:shuffle-relative`, the two
extensions the emission names) and a subgroup size (`:subgroup-size`) that
divides `W`; every other answer, including a descriptor that reports no
capability at all, fails closed to `:baseline`. (b) is unchanged: no Intel
or Mali device has run the variant, both rows stay UNMEASURED, and their
measurement contracts stand as written. The NVIDIA row is selected under
either of its route's names (`:cuda`, `:cuda-v1`), the same one-route rule
ADR-0359 decision 3 established for `:vulkan` / `:glsl-v1`.

**Amendment (2026-10-22, one reduce identity across every arm).** The
review-P2 identity fix had landed on the GLSL arm only: the WGSL, MSL and
CUDA reduce emissions (CUDA baseline and :warp-shuffle-reduce alike) still
folded the finite +-3.402823466e+38 bound as the extrema identity. A finite
bound is corrupted by a legitimate +-Inf input in the padded lanes -- an
all-(-Inf) :max reduction answered -FLT_MAX -- and +-Inf is inside rule 2's
ordinary-value domain, so the same KIR answered different reduces in the
GLSL arms than in the other three. All four arms now carry the IEEE-754
infinite neutral, each spelled in its own exact bit-reinterpretation
intrinsic (uintBitsToFloat / bitcast<f32> / __uint_as_float /
as_type<float>), pinned by `every-arm-shares-one-operator-meaning` in
accelerator-test (which also asserts the finite bound appears in no arm's
bytes). The NaN / negative-zero regime is UNCHANGED: still excluded from
rule 2's claim and still UNMEASURED.

**Amendment (2026-10-23, the JUN-58 selection row lands).** ADR-0360 adds
the Apple row: the same `:subgroup-reduce` emission and the same selection
gate (rules 3 + 6), on the Vulkan route only -- the MSL emitter admits
`:baseline`, so rule 3 keeps `:msl-v1` at `:baseline` and a Metal simdgroup
row on the MSL route is not designed here. The row is implemented; it is
UNMEASURED and its measurement contract is ADR-0360's. ADR-0360 also names
the open contract gap the rule-6 rows share: the descriptor facts
(`:subgroup-size`, `:subgroup-ops`) have no producer in the wire-42 plan
(`INFO` is four fields, `DEVCLASS` one class word), so every rule-6 row
today selects only for a descriptor a future probe or provider fills in,
and fails closed to `:baseline` without them.

**Amendment (2026-10-23, the JUN-57 Vulkan-route row lands).** ADR-0361
adds the NVIDIA row on the Vulkan route: the same `:subgroup-reduce`
emission and the same selection gate (rules 3 + 6) that ADR-0357/0360
bound to ARM and Apple, plus one NVIDIA-specific condition -- whenever the
descriptor reports a compute capability, the CUDA row's sm_70+ floor binds
this row too (a reported capability below 7.0, or a malformed one, answers
`:baseline`, fail closed; an absent capability is not a refusal). The CUDA
row (`:warp-shuffle-reduce`, `__shfl_down_sync`, warp width baked in) is
unchanged and stays CUDA-route only. The motivation is the execution
record: CUDA has never executed anything in this repository and Vulkan is
the only route that ever has, so before this amendment `:nvidia` answered
`:baseline` on the one route that runs. All four rows share one emission
and one shape predicate now; every row stays UNMEASURED as a variant row
(the measured workgroup rows of ADR-0358 are a different axis and
untouched), and every row still fails closed to `:baseline` on a
descriptor without the rule-6 facts.

**Amendment (2026-10-23, the fact producer is designed).** ADR-0362 makes
the separate design decision ADR-0360/0361 left open: the rule-6 facts
ride one additive wire-42 request `SUBGROUP` answering `<size>|<ops>`
(compute-stage subgroup width; the Vulkan 1.1 core
`VkSubgroupFeatureFlagBits` tokens, `basic` and `shuffle-relative` being
the two the fold needs), with the named refusal `gpu/no-compute-subgroups`
treated exactly like an absent fact. The protocol-table entries landed
2026-10-23 (verb SUBGROUP = 18, answer fields = 2, refusal index 35;
ADR-0362's amendment); the producer's answer and the consumer parser
remain unimplemented slices, and every row here keeps failing closed to
`:baseline` without the facts.

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
