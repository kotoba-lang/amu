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
| `:baseline` | all | all | implemented (main; ADR-0002 emitters) | EXECUTION RECORD (reconciled 2026-10-23): no variant has an in-repo execution path today (the wire-42 route died with the C loader; ADR 0371's provider is the replacement track) -- and `:subgroup-reduce` has EXECUTED on Apple M1 Max through measurement harnesses (2026-10-19 wire-42/MoltenVK, 2026-10-23 native Metal), losing to `:baseline` in both |
| `:warp-shuffle-reduce` | nvidia | reduce, W >= 32 | implemented (PR #1331, MERGED 2026-10-20); CUDA emission only | UNMEASURED: no NVIDIA hardware, and the CUDA emitter has no execution path in this repo |
| `:subgroup-reduce` | intel | reduce, W >= 32 | **implemented** 2026-10-22 (this ADR's design, on ADR-0359's admitted emission and sealed build step; selection row in `kotoba.compiler.accelerator-variants` under rules 3 + 6) [ROUTE PROSE WIDENED 2026-10-24 -- the debt the rows-table completion slice named ("widening those cells is NOT taken here -- named, unpaid", docs/evidence/gpu/adr0356-rows-table-completion-20261024.txt): the routes this row rides as IMPLEMENTED are the Vulkan route (`:vulkan` / `:glsl-v1`, ADR-0359's GLSL arm of the shared emission, `kotoba.compiler.accelerator-subgroup-reduce`, commit 53248c112) and the WGSL route (`:webgpu` / `:wgsl-v1`, this ADR's 2026-10-23 ":wgsl-v1 selection question is DECIDED" amendment = ADR-0363, commit 77a772ff5; the WGSL arm `emit-wgsl`, commit 905a15b5a) -- `kotoba.compiler.accelerator-variants-test` pins both routes selecting the row and every off-route target failing closed to `:baseline`. Prose only: the row's implementation (2026-10-22/23, older than this bracket), its measurement cell and every state flag are unchanged] | UNMEASURED: no Intel hardware |
| `:subgroup-reduce` | arm | reduce, W >= 32 | **implemented** 2026-10-22 (the row is DESIGNED in ADR-0357, the ARM decision of record; same emission and selection row as the Intel row) [ROUTE PROSE WIDENED 2026-10-24: the same two routes as the Intel row's bracket above -- Vulkan (`:vulkan` / `:glsl-v1`) and WGSL (`:webgpu` / `:wgsl-v1`) -- one shared emission (its GLSL and WGSL arms) and one shared selection row (the `#{:intel :arm ...}` vendor set) behind both, and ADR-0357's capability precondition binds the row on either route. Prose only, as above] | UNMEASURED: no Mali hardware |
| `:subgroup-reduce` | apple | reduce, W >= 32 | **implemented** 2026-10-23 (the row is DESIGNED in ADR-0360, the Apple decision of record; same emission and selection row as the Intel row; Vulkan route, and the MSL route too since ADR-0360's later 2026-10-23 amendment) | **MEASURED ON APPLE M1 MAX, TWICE, BOTH ROUTES -- THE VARIANT LOST BOTH TIMES** (this cell replaces the false "no Apple device has run the variant"): GLSL arm via wire-42/MoltenVK 2026-10-19 (PR #1347/#1348: ~20-27% slower at W=256, never faster over W=32..256) and MSL arm via a native Metal harness 2026-10-23 (ADR-0360's measurement amendment: ~22% slower at W=256 across :sum/:max/:min). `:measured?` stays `false` -- the contract's flip is blocked on the measurement-contract question (1) that ADR-0360's amendment leaves PROPOSED, and what the row selects given the measured cell is DECIDED (ADR-0360's second decision, 2026-10-23): the row is NARROWED to the measured device -- a descriptor naming the measured device (`m1 max` fragment, uB5G idiom) answers `:baseline`, every other Apple device keeps `:subgroup-reduce` (UNMEASURED); a Metal-native simdgroup row stays NOT designed [MARKED 2026-10-23, ADR-0373's slice, honesty marks only: the "`:measured?` stays `false` / the flip is blocked on question (1) / leaves PROPOSED" clause is SUPERSEDED -- question (1) was DECIDED and the flip landed (the measured M1 Max cells carry `:measured?` true and a `:measured-cell` record in `kotoba.compiler.accelerator-variants`; commit 454d6078 and after); and "a Metal-native simdgroup row stays NOT designed" is SUPERSEDED -- ADR-0373 designs it (design only, not implemented)] [ROUTE PROSE WIDENED 2026-10-24 -- the routes this row rides as IMPLEMENTED are the Vulkan route (`:vulkan` / `:glsl-v1`), the MSL route (`:metal` / `:msl-v1`) and the WGSL route (`:webgpu` / `:wgsl-v1`; the 2026-10-24 Apple WGSL-route decision, JUN-58's own decision, ADR-0360's same-day amendment, docs/evidence/gpu/apple-wgsl-route-decision-20261024.txt -- same rules 3 + 6 gate, the measured-device narrowing riding along on that route, no simdgroup rung there since `:simdgroup-reduce` is MSL emission only). UNCOMPILED on the WGSL arm (no validator on the testing host) and the WGSL arm is UNMEASURED on every device; the measurement cells in the next column speak about the GLSL and MSL arms only. Prose only: the row's implementation (older than this bracket), its measurement cells and every state flag are unchanged] |
| `:subgroup-reduce` | nvidia (Vulkan route) | reduce, W >= 32 | **implemented** 2026-10-23 (the row is DESIGNED in ADR-0361, the NVIDIA decision of record; same emission and selection row as the Intel row, Vulkan route only, plus the sm_70+ floor fail-closed on a reported compute capability) [ROUTE PROSE WIDENED 2026-10-24 -- ADR-0361's 2026-10-24 amendment (the NVIDIA WGSL-route selection question is DECIDED, JUN-57's own decision; the record docs/evidence/gpu/nvidia-wgsl-route-decision-20261024.txt): the routes this row rides as IMPLEMENTED are the Vulkan route (`:vulkan` / `:glsl-v1`) and the WGSL route (`:webgpu` / `:wgsl-v1`) -- the same rules 3 + 6 gate on both, the sm_70+ floor included, and no `:warp-shuffle-reduce` rung on the WGSL route (that variant is CUDA emission only). The CUDA-route ladder rung-2 row below is a separate row and is unchanged. UNCOMPILED on the WGSL arm (no validator on host) and UNMEASURED everywhere] | UNMEASURED: no NVIDIA device has run the variant |
| `:subgroup-reduce` | nvidia (CUDA route, ladder rung 2) | reduce, W >= 32 | **implemented** 2026-10-23 (ADR-0361's amendment: the CUDA ladder's SECOND rung -- `:warp-shuffle-reduce` keeps precedence whenever its gate holds (a CONFIRMED compute capability 7.0+ and `W >= 32`), the parametric fold answers only where the warp row's gate does not reach (rule-6 subgroup facts reported, NO compute capability); ladder `:warp-shuffle-reduce` -> `:subgroup-reduce` -> `:baseline`, total and deterministic; the two rungs spell the same fold, runtime `warpSize` vs the baked 32) [ROW ADDED 2026-10-24, the rows-table completion slice: the row the 2026-10-23 row-prose reconciliation named as missing (docs/evidence/gpu/row-prose-reconciliation-20261023.txt) now exists; the decision and its implementation are unchanged and older than this row -- prose only] | UNCOMPILED (no nvcc on the testing host) and UNMEASURED: nothing has run on NVIDIA hardware, the CUDA emitter has no execution path in this repo, `:measured? false` on every answer |
| `:subgroup-reduce` | amd | reduce, W >= 32 | **implemented** 2026-10-23 (ADR-0364: the shared subgroup-size-parametric fold on the Vulkan route (`:vulkan` / `:glsl-v1`, RADV) and the WGSL route (`:webgpu` / `:wgsl-v1`, the `:amd` vendor-default target), same rules 3 + 6 gate, fail closed included; AMD has no compute-capability contract -- an absent capability is not a refusal; the RDNA wave32/wave64 duality is answered by the emission's runtime width query and rule 6's `S | W` gate, not by selection; no AMD-native arm is designed) [ROW ADDED 2026-10-24, the rows-table completion slice: the 2026-10-23 "the AMD row joins the table" amendment named the row, but the table itself never carried it until now -- prose only] | UNMEASURED: no AMD hardware has run this variant, `:measured? false` on every answer |
| `:simdgroup-reduce` | apple | reduce, W >= 32 | **DESIGNED 2026-10-23 (ADR-0373, the Metal-native SIMD-group row: `simd_sum`/`simd_max`/`simd_min` fold + the shared cross-SIMD-group tree, MSL route only)** [UPDATE 2026-10-23, rule 3 step 1: the MSL emission + `lower` admission + tests are IMPLEMENTED; the selection row is NOT -- `select-variant` answers byte-for-byte what it answered before] [UPDATE 2026-10-23, rule 3 step 2: the SELECTION row is IMPLEMENTED too -- the MSL ladder (this variant first, `:subgroup-reduce` second, `:baseline` last), the measured-cell carve-out (the narrowed M1 Max class never answers it) and the `:simd-reduce` rule-6 gate, with tests; outside the ladder's scope `select-variant` is byte-for-byte unchanged] | UNMEASURED: no hardware has run this variant until 2026-10-23's step-3 slice [MARKED 2026-10-23, rule 3 step 3: **MEASURED ON APPLE M1 MAX AT W = 256 (n = 1000003) -- FASTER THAN `:baseline` THERE**: paired median ratios 0.790/0.800/0.799 (sum/max/min), claim-protocol rule 2 REGIME-INVARIANT FASTER (18/18 per-run ratios), native-Metal channel, docs/evidence/gpu-simdgroup-reduce-m1max-20261023/ -- the OPPOSITE sign to `:subgroup-reduce` at the same cell. NO `:measured?` movement: the flip for this variant's own cells is its own open slice; the measured M1 Max `:subgroup-reduce` cells still speak about `:subgroup-reduce` only. Every other W (32/64/128/512/1024), shape 2, and every other device stay UNMEASURED] |

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
landed later the same day (ADR-0362's slice-3 and slice-2 amendments) --
the provider's Vulkan read and wire reply remain unimplemented (the ADR
0371 track), so no live wire carries the facts and every row here keeps
failing closed to `:baseline` without them.

**Amendment (2026-10-23, the WGSL arm of the shared emission lands).** The
subgroup-size-parametric emission gains its WGSL arm
(`kotoba.compiler.accelerator-subgroup-reduce/emit-wgsl`), and `lower`
admits it for the (:wgsl-v1, :subgroup-reduce) pair in both readings --
rule 3's "emission admission first" now holds on the WGSL path exactly as
the Vulkan-side arm established it for :glsl-v1 on 2026-10-22. The design
basis is this file's Intel-row letter ("It queries the subgroup size at
runtime (`gl_SubgroupSize` / the WGSL subgroup builtin)") and rule 6's own
sentence ("the WGSL path treats subgroups as the optional feature they
are"): the arm queries `subgroup_size` at runtime and bakes no width, and
it depends on the `subgroups` ENABLE extension plus the `subgroup_id`
LANGUAGE extension (`subgroup_id` / `num_subgroups` are not enable-able --
that spelling is a shader-creation error; verified against the W3C WGSL
spec and the merged gpuweb subgroups proposal, fetched 2026-10-23: vendor
documentation, not a measurement). Per ADR-0357 P2's last sentence, a
language surface without those builtins answers `:baseline`. **The
selection rows do NOT move**: `select-variant` still answers
`:subgroup-reduce` only on the Vulkan route (:vulkan / :glsl-v1).
Extending the Intel/ARM rows to :wgsl-v1 (and whether the Apple/NVIDIA
rows follow -- their ADRs scope them to the Vulkan route) is a SEPARATE
design decision, proposed here and decided nowhere: until it lands, a
:wgsl-v1 dispatch answers :baseline from selection even though the
emission can now carry the variant. UNCOMPILED and UNMEASURED: no WGSL
compiler or validator exists on the testing host (the text contracts are
test-pinned -- the same regime as the CUDA arm, which has no nvcc), and
no WebGPU execution path exists. No `:measured?` flag moves and no
workgroup row is touched.

**Amendment (2026-10-23, the :wgsl-v1 selection question is DECIDED).**
ADR-0363 supersedes the "proposed here and decided nowhere" clause above:
the WGSL route (`:webgpu` / `:wgsl-v1`, one route two names) now carries
the Intel and ARM rows under the same rule 3 + rule 6 gate, and the Apple
and NVIDIA rows stay Vulkan-route-only (their ADRs' scope; extending either
is a separate per-vendor decision, undecided). [UPDATE 2026-10-24,
superseded as to NVIDIA: ADR-0361's 2026-10-24 amendment (the NVIDIA
WGSL-route selection question is DECIDED, JUN-57's own decision, one
vendor per decision) extends the NVIDIA row to this route under the same
gate; the Apple row's WGSL question stays UNDECIDED.] [SUPERSEDED 2026-10-24
as to Apple too, same day: ADR-0360's 2026-10-24 amendment (the Apple
WGSL-route selection question is DECIDED -- YES, JUN-58's own decision,
one vendor per decision,
docs/evidence/gpu/apple-wgsl-route-decision-20261024.txt) extends the
Apple row to this route under the same gate, the measured-device
narrowing riding along. After this marker no route question is
UNDECIDED for the five designed rows.] The selection change is
implemented with tests; everything about it stays UNCOMPILED and
UNMEASURED, `:measured? false` on every answer, no workgroup row touched,
and both routes still fail closed to `:baseline` without the rule-6 facts
whose producer (ADR-0362) is still unimplemented.

**Amendment (2026-10-23, the MSL arm of the shared emission lands).** The
subgroup-size-parametric emission gains its MSL arm
(`kotoba.compiler.accelerator-subgroup-reduce/emit-msl`), and `lower`
admits it for the (:msl-v1, :subgroup-reduce) pair in both readings --
rule 3's "emission admission first" now holds on the MSL path too, and
this supersedes the JUN-58 amendment's clause "the MSL emitter admits
`:baseline`, so rule 3 keeps `:msl-v1` at `:baseline`" (and ADR-0360's /
ADR-0363's same-cause clauses): the MSL route keeps answering `:baseline`
NOT because the emitter refuses the variant but because the Apple row's
selection scope is the Vulkan route, and extending it is the separate
per-vendor decision below. The arm is the same fold to its letter in Metal
spellings -- `[[threads_per_simdgroup]]` (the runtime size query; the
spec's alias of `thread_execution_width`),
`[[thread_index_in_simdgroup]]` / `[[simdgroup_index_in_threadgroup]]` /
`[[simdgroups_per_threadgroup]]` (P2's subgroup-ID partials, never lid
arithmetic), `simd_shuffle_down` (the shuffle loop stays the fold; a
`simd_sum`/`simd_max`/`simd_min` rewrite would regroup and is not this
arm), `threadgroup_barrier(mem_flags::mem_threadgroup)`, `as_type<float>`
infinite neutrals (one meaning per operator with the MSL baseline arm's
`msl-identity`). Spellings verified against the Apple Metal Shading
Language Specification and "Porting your Metal code to Apple silicon"
(fetched 2026-10-23): vendor documentation, not a measurement. One
arm-level deviation FORCED by the language and compiler-verified: Metal
refuses a kernel named `main` ("kernel function cannot be called 'main'",
Apple metal 32023.883), so this arm's entry is the kernel's :kernel/name
-- the ADR-0002 MSL family's own entry contract -- and the variant
family's name-free `main` convention does not extend to Metal. The
partials array is an in-kernel `threadgroup float partials[W]` (the WGSL
arm's fixed-array choice), not the MSL baseline's `[[threadgroup(0)]]`
pointer; the buffer bindings (x 0, parts 1, n 2) are the MSL family's,
unchanged.

COMPILED, still UNMEASURED: all eighteen emitted sources (W in
{32,64,128,256,512,1024} x {sum,max,min}, the whole admitted row) compile
to AIR under the Apple Metal compiler (metal 32023.883) on this host --
a TOOLCHAIN fact of what compiles, in
`docs/evidence/gpu-subgroup-reduce-msl-20261023/` (the emitted sources,
the compile transcript, and the scoped/full gate logs). This is the
first arm of the variant with any compiler verification at all (the
GLSL arm has executed, the CUDA/WGSL arms remain uncompiled text
contracts). (A "first" CORRECTED by the 2026-10-23 reconciliation: the
GLSL arm compiled through glslang when it executed on 2026-10-19, so this
arm is not the first with compiler verification -- its own first is the
MSL family and the language's compiler.) No Metal execution path exists in
this repository (the
brokers died with the C loader; ADR 0371's provider is the replacement
track), so nothing has executed this arm (SUPERSEDED later the same day:
the MSL arm DID execute on Apple M1 Max through the native-Metal harness
of ADR-0360's measurement amendment -- a harness path, not this
repository's runtime), no `:measured?` flag moves and
no workgroup row is touched.

The selection rows do NOT move: `select-variant` answers `:subgroup-reduce`
for `:apple` only on the Vulkan route, and a capable Apple device on
`:msl-v1` / `:metal` still answers `:baseline` (the variants tests pin
this). Extending Apple's row to the MSL route (and whether the rule-6
facts there come from the same wire-42 SUBGROUP request ADR-0362
designed, given a Metal-native descriptor would report SIMD-group facts
directly) is a SEPARATE per-vendor design decision (JUN-58's own),
proposed here and decided nowhere.

**Amendment (2026-10-23, the CUDA arm of the shared emission lands).** The
subgroup-size-parametric emission gains its CUDA arm
(`kotoba.compiler.accelerator-subgroup-reduce/emit-cuda`), and `lower`
admits the (:cuda-v1, :subgroup-reduce) pair in both readings -- rule 3's
"emission admission first" now holds on the CUDA path too, and the fold is
covered by all four emitters (GLSL 2026-10-22, WGSL and MSL 2026-10-23,
CUDA 2026-10-23). The fold is the same shuffle loop in CUDA spellings: the
subgroup size is queried at runtime as `warpSize` (the CUDA C++
Programming Guide's built-in device variable, "a run-time value defined as
the number of threads in a warp" -- the width is 32 on every shipping
NVIDIA device and the emission names the spelling, not the number; the
arm claims none of Intel's 8/16/32 variance), the shuffle is
`__shfl_down_sync(mask, v, d, fold)` with the guide's width parameter
carrying the runtime fold width (the guide: an out-of-range source lane
returns the caller's own var, so the guard drops it exactly as in every
arm), the participation mask is `__activemask()` (the runtime active-lane
query -- no 32-lane constant is baked anywhere in the source), the partial
index is `threadIdx.x / warpSize` (CUDA has no subgroup-id builtin; P2
binds unchanged), and the partials array is a fixed
`__shared__ float partials[W]` (the MSL/WGSL arms' fixed-workgroup-array
choice). [UNCOMPILED CLOSED 2026-10-24 as to one real toolchain: the
emitted row compiles clean with the real nvcc 11.4 (V11.4.315) on the
fleet's CUDA host xavier (Jetson AGX, L4T R35.4.1, -arch=sm_72) -- 18
.cubin + 18 .ptx, received bytes sha256-identical to the emitter's,
docs/evidence/gpu/cuda-compile-xavier-20261024/; this host still has no
nvcc, and UNMEASURED is UNCHANGED -- a compile is not a measurement.]
UNCOMPILED and UNMEASURED (as written 2026-10-23): no nvcc exists on the testing host
(the same regime as the WGSL arm -- text contracts test-pinned to the
NVIDIA CUDA C++ Programming Guide, fetched 2026-10-23: vendor
documentation, not a measurement), the CUDA emitter has no execution path
in this repository, and nothing has run on NVIDIA hardware. **The
selection rows do NOT move**: the NVIDIA CUDA-route row keeps
`:warp-shuffle-reduce` (ADR-0361's amendment records the same fact) and
(:cuda-v1, :subgroup-reduce) lowers only when asked for by name; whether
the CUDA-route row should ever answer `:subgroup-reduce` is a separate
per-vendor decision, proposed here and decided nowhere. No `:measured?`
flag moves and no workgroup row is touched.

**Amendment (2026-10-23, the :msl-v1 Apple selection question is DECIDED).**
ADR-0360's same-day amendment supersedes the MSL-arm paragraph's
"proposed here and decided nowhere" clause above: the Apple row now
selects `:subgroup-reduce` on the MSL route (`:metal` / `:msl-v1`) under
the same rules 3 + 6 gate the Vulkan route uses, and the rule-6 facts are
read from the same descriptor keys whatever fills them -- a Metal-native
probe reports SIMD-group facts directly into `:subgroup-size` /
`:subgroup-ops` (the two tokens are this table's capability vocabulary,
not a Vulkan binding), while ADR-0362's wire-42 `SUBGROUP` request stays
the Vulkan route's producer. The NVIDIA CUDA-route question named in the
CUDA-arm paragraph above stays UNDECIDED -- one vendor per decision.
Everything stays UNMEASURED: no `:measured?` flag moves and no workgroup
row is touched.

**Amendment (2026-10-23, the NVIDIA CUDA-route selection question is
DECIDED).** ADR-0361's same-day amendment supersedes the CUDA-arm
paragraph's "proposed here and decided nowhere" clause (and the
Apple-decision amendment's "stays UNDECIDED" sentence above): the CUDA
route (`:cuda` / `:cuda-v1`) now carries NVIDIA's `:subgroup-reduce` row
as the SECOND rung of that route's ladder -- `:warp-shuffle-reduce` (the
CUDA-native row) keeps precedence whenever its gate holds (a CONFIRMED
compute capability 7.0+ and `W >= 32`), and the parametric fold answers
only where the warp row's gate does not reach (rule-6 subgroup facts
reported, NO compute capability). The ladder is total and deterministic:
`:warp-shuffle-reduce` -> `:subgroup-reduce` -> `:baseline`, and the
extension answers exactly one corner the warp row leaves open. The two
rungs spell the same fold (runtime `warpSize` vs the baked 32), so no
reduction semantics change with the choice. Implemented with tests;
UNCOMPILED and UNMEASURED (no nvcc, no NVIDIA execution path, nothing run
on NVIDIA hardware) [UNCOMPILED CLOSED 2026-10-24 as to one real
toolchain: the emitted row compiles clean with the real nvcc 11.4
(V11.4.315) on the fleet's CUDA host xavier, -arch=sm_72 -- 18 .cubin +
18 .ptx, received bytes sha256-identical to the emitter's,
docs/evidence/gpu/cuda-compile-xavier-20261024/; UNMEASURED unchanged and
this host still has no nvcc], `:measured? false` on every answer, no
workgroup row touched.

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
  file; the NVIDIA row is citable as *implemented (PR #1331 merged
  2026-10-20), UNMEASURED*.
- JUN-59 has a concrete, mechanically checkable row: implement the emission,
  then the predicate, then measure on hardware. The three states stay
  distinguishable at every step.
- ARM (JUN-60) remains proposed. Its row is a separate design decision --
  one vendor per decision -- and nothing here should be read as having
  designed it.
- The provisional workgroup rows of ADR-0355 are untouched by this ADR and
  remain `:measured? false` on their own axis. [UPDATE 2026-10-24:
  superseded in part -- ADR-0358 (2026-10-19) measured four of ADR-0355's
  rows; only :arm/:unknown remain `:measured? false` on the workgroup axis.
  "Untouched by this ADR" stands. Census:
  docs/evidence/gpu/workgroup-prose-rootcause-20261024.txt.]

**Amendment (2026-10-23, the AMD row joins the table -- ADR-0364).**
`:amd` (JUN-84 / AWAI-40) is the fifth classified vendor to ride the
shared `:subgroup-reduce` emission, on the Vulkan route (`:vulkan` /
`:glsl-v1`, RADV) and on the WGSL route (`:webgpu` / `:wgsl-v1`, the
`:amd` vendor-default target -- the ADR-0363 rationale applied), under
the same rule 3 + rule 6 gate, fail closed included. This supersedes
"other vendors (including :amd, which has no designed row)" wherever it
stood: `:unknown`, `:qualcomm` and every unclassified name keep answering
`:baseline` everywhere. AMD's wave32/wave64 duality (AWAI-40 scope
item 1) is answered by the emission's runtime width query and rule 6's
`S | W` gate, not by selection; no AMD-native arm is designed (RDNA ISA
instructions are the driver compiler's concern -- ADR-0364 records the
reason). Implemented with tests; UNMEASURED like every other row -- no
AMD hardware has run this variant and `:measured?` stays `false` on every
answer.

**Amendment (2026-10-23, the row prose reconciled to the execution
record).** The correction commit 7f1c7faf named this slice: the row prose
said "no Apple device has run the variant" while the record said
otherwise. The full contradiction set in this file and in the `:basis`
text the answers carry (`kotoba.compiler.accelerator-variants`) is now
reconciled to the merged record -- every claim below is a citation, not a
new measurement:

1. Apple row: "UNMEASURED: no Apple device has run the variant" was FALSE.
   Apple M1 Max ran the variant twice: the GLSL arm via wire-42/MoltenVK
   2026-10-19 (ba1fcced / 677fa1cf, PR #1347/#1348 -- ~20-27% slower at
   W=256, never faster over W=32..256) and the MSL arm via a native Metal
   harness 2026-10-23 (009c86ef, corrected in 7f1c7faf -- ~22% slower at
   W=256 across :sum/:max/:min). The row's measurement cell now carries
   the measured truth and the direction of the result. The row's state
   cell also said "Vulkan route only", superseded by ADR-0360's later
   2026-10-23 amendment (the row rides the MSL route too).
2. `:baseline` row: "the only variant with an execution path today" was
   stale twice over -- no variant has an in-repo execution path since the
   C loader removal (ADR 0371's provider is the replacement track), and
   `:subgroup-reduce` has executed through measurement harnesses. The same
   claim sat in `variant-bases`' `:baseline` basis text (every
   `:baseline` answer carried it); both are corrected.
3. `variant-bases`' `:subgroup-reduce` basis: "no hardware here has said
   so" was FALSE on the same record (see 1); the basis now separates
   UNMEASURED (Intel, Mali, NVIDIA) from MEASURED-CONTRADICTED (Apple) and
   keeps the two design questions PROPOSED (narrow the row, or a
   Metal-native simdgroup row -- decided nowhere). [SUPERSEDED 2026-10-23
   as to both: "narrow the row" was DECIDED in ADR-0360's second decision
   (the row narrows to the measured device); the Metal-native simdgroup
   row was DECIDED in ADR-0373 (designed there, not implemented). The
   clause records the state at the reconciliation date.]
4. The MSL-arm paragraph: "nothing has executed this arm" was SUPERSEDED
   the same day by the 2026-10-23 native-Metal run (marked inline), and
   "the first arm of the variant with any compiler verification at all"
   over-claimed against its own parenthetical (the GLSL arm compiled via
   glslang when it executed on 2026-10-19) -- marked inline.
5. NVIDIA CUDA row and Consequences: "PR #1331, open and unmerged at this
   date" / "implemented in flight" -- PR #1331 MERGED 2026-10-20; the
   table and consequences now say so. (ADR-0357's line "PR #1331 is in
   flight ... at this date" is dated snapshot prose in another ADR and is
   left as written there.)

Vocabulary, settled here so the two facts never merge: UNMEASURED in this
ADR means the `:measured?` lock is in force (no report may cite the row as
optimization evidence). "Has a hardware measurement" is a separate fact:
the Apple row has one (two, in fact) and every other row has none. The
Apple row is therefore *implemented, hardware-measured (refuting),
`:measured? false`* -- all three at once, and each is stated where it
belongs.

Locks unchanged by this reconciliation: NO `:measured?` flag moves (the
Apple flip stays blocked on the per-tested-device scoping and route
clauses ADR-0360's measurement amendment names -- the flag question is
part of the PROPOSED questions that amendment lists), no workgroup row is
touched (a different axis), and no state is upgraded: the Apple row's
measured cell says what the hardware said -- a refutation of the design
assumption on the one device tested, not optimization evidence for or
against any other device, W, n or operator. [MARKED 2026-10-23, ADR-0373's
slice: the "flag question is part of the PROPOSED questions" clause is
SUPERSEDED -- question (1) was decided and the flip landed the same day
(`:measured?` true on the measured cells with `:measured-cell` records;
see ADR-0360's supersession note and commit 454d6078). This clause
records the state at the reconciliation date. The no-workgroup-row and
no-optimization-evidence locks stand unchanged.] Named, not hidden: the rows
table still has no separate table row for the NVIDIA CUDA-ladder second
rung (`:subgroup-reduce` under `:warp-shuffle-reduce`'s precedence); the
rung is recorded in ADR-0361's amendment and in `select-variant`'s
docstring, and adding a table row is not done here.
