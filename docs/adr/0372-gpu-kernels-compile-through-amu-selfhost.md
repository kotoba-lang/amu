# ADR 0372: GPU kernels are compiled through Amu selfhost into SPIR-V

Date: 2026-10-22
Status: Proposed. Owner direction 2026-10-22: GPU compilation goes through
selfhost as well. Step 1 (the encoder, the checker and the first kernel)
and the kernels of step 2 (the workgroup and subgroup reductions, the
ADR 0358 sweep kernel and the glslang cross-check) are implemented; the
vendor rows of step 2 and steps 3–5 are not.
Tracking: AWAI-79 (parent AWAI-35). Related: ADR 0001 Phase 5, ADR 0002,
ADRs 0355–0358, ADR 0371 (the execution route), AWAI-5 (the inference kernel DSL).

## Context

Three things stand between a GPU kernel and the selfhost product route today:

* **The kernel generators are hosted.**
  * The inference kernel DSL (`verify/native/gpu/kernel-dsl/emit-kernel.cljk`)
    is a kbb script that renders GLSL or MSL text.
  * Most of its "data" is text templates.
  * On main its kdot and qkvr output no longer compiles: a shared `red_sum`
    changed signature in inference #55.
  * Amu's accelerator pipeline (`src/kotoba/compiler/accelerator*.cljk`, ADRs
    0002 and 0355–0358) emits WGSL, CUDA and MSL text on the nbb route.
* **SPIR-V comes from `glslangValidator`,** a C++ tool. Every `.spv` the decode
  guest loads is built that way, ad hoc per box.
* **The vendor tables are CLJK.** That covers vendor → target, the workgroup
  rows and the variant selection. Four of the six workgroup rows are measured
  (NVIDIA, Apple, Intel and AMD); ARM is design-only, and so is every variant
  row.

`docs/selfhost-priority.md` rule 3 forbids keeping CLJK, kbb or a C/C++
compiler in the product route. Rule 6 makes the vendor driver the platform
boundary (ADR 0371). SPIR-V, and MSL on Apple, is therefore the format that
crosses that boundary, and Amu must produce it itself.

What the current kernels need from SPIR-V:

* **Used:**
  * `Shader`;
  * storage buffers (std430, set 0, bindings 0..n-1);
  * workgroup arrays;
  * `GLSL.std.450`;
  * `Float16` arithmetic (unpacked from u32);
  * `GroupNonUniform`, with arithmetic and shuffle;
  * the packed 4x8 integer dot product (core in SPIR-V 1.6).
* **Not used:** push constants, specialization constants, images and atomics.

## Decision

### 1. One typed kernel IR, KIR v2, in Kotoba

A kernel is typed Kotoba data:

* buffers with element types;
* workgroup arrays;
* builtins;
* structured control flow (if and loop, with explicit merges);
* reductions with an explicit fold order;
* `GLSL.std.450` calls, subgroup operations and the integer dot product.

Build-time variants (today's `-D` defines) become generator parameters. KIR
v1 (ADR 0002: f32 elementwise and reduce) is the first subset lowered.

Floating constants are bit patterns, because static Kotoba has no float type
and SPIR-V `OpConstant` takes bits.

### 2. Emitters are Kotoba, built by Amu selfhost

`tools/spirv_encode.kotoba` writes the binary word stream:

* **Header and version.** The magic number, version 1.3 (1.6 only for modules
  that need the integer dot product), generator 0, the id bound and schema 0.
* **Instructions and literals.** Word count and opcode in the first word;
  literal strings are NUL-padded.
* **Output.** The tool writes the `.spv` bytes through
  `:fs/app-data-bytes` WRITE.

Kernel generators such as `tools/gpu_kernel_kir1.kotoba` build modules from
the IR.

The output is deterministic:

* ids are allocated in a fixed order;
* no debug instructions are emitted;
* the same IR always gives the same bytes;
* receipts record each module's digest.

MSL comes from the same IR, for Apple, once ADR 0371 has a macOS route. GLSL
output exists only as an oracle renderer.

### 3. Validation

1. **Structural checker.** `tools/spirv_check.kotoba` is a subset of
   `spirv-val` written in Kotoba. It checks the header, word counts, section
   order, single definition of each id below the bound, function and block
   structure, merge-before-branch, the entry-point function, and the
   capability for the execution model. The provider reuses it for its
   `gpu/not-spirv` refusal (ADR 0371).
2. **Oracles only.** `spirv-val` and `spirv-dis` (SPIRV-Tools) and glslang
   check the produced modules at test time on a developer host, and their
   results go into the receipts. They never run in the product route.
   Byte-for-byte equality with glslang is not a goal: id numbering and
   instruction choice differ.
3. **Execution.** Driver load and numeric gates (the dot and kdot fixtures,
   the decode argmax chain against the f64 oracle) run through the ADR 0371
   provider, once steps 3–6 exist.

### 4. The vendor tables continue on the Kotoba port

The CLJK-to-Kotoba port program already gives
`src/kotoba/compiler/accelerator_targets.cljk` a `:kotoba` reading
(amu #1478, W3). That reading compiles on the seed module route and matches
the host reading byte for byte. This ADR builds on that port, without a
second copy. What remains:

* make the Kotoba reading the canonical source;
* route Vulkan to the SPIR-V target this ADR adds, instead of WGSL;
* read `measured?` per row, instead of only for a device named "m1 max";
* make the docstrings say what is measured;
* port `accelerator_variants` the same way.

### 5. The provider must enable what modules declare

ADR 0371's provider enables `shaderFloat16` and the integer dot product when
a module declares them, and reports subgroup size and operations. Today's
four-field `INFO` cannot carry that, so a protocol v2 verb is needed. That is
a follow-up to ADR 0371.

## Rejected alternatives

* **Keep glslang, or emit GLSL and compile it with glslang.** That keeps C++
  in the product route (`docs/selfhost-priority.md` rule 3).
* **Reuse the inference DSL as it is.** It is text templates rather than a
  typed IR, it runs on kbb, and on main it no longer compiles.
* **naga or wgpu for translation.** That puts a Rust runtime in the route.
* **WGSL as the Vulkan route.** wire 42 runs SPIR-V; WGSL stays the browser
  (WebGPU) target.

## Implementation steps

1. **Encoder, checker and the first kernel.** Done. Added:
   * `tools/spirv_encode.kotoba` and `tools/spirv_check.kotoba`;
   * `tools/gpu_kernel_kir1.kotoba`, the KIR v1 elementwise f32 kernels on
     the wire-42 binding layout (x, y, z and n as storage buffers 0..3);
   * `tools/gpu_kernel_spirv_test.kotoba`.

   `scripts/seed/check-gpu-kernel-spirv.py` builds the test unit with the
   pinned root, runs it as a static image that writes the `.spv` files, and
   then runs `spirv-val` and `spirv-dis` as oracles on the host.
2. **KIR v1 reduce, the vendor rows and the checker against glslang.**
   * **Done: the workgroup reductions** (sum, max and min) on the wire-42
     layout (x, parts and n as bindings 0..2). They use a shared array, an
     `OpPhi` stride loop with a barrier per step, and `GLSL.std.450`
     FMax/FMin. The identities are f32 bit patterns.
   * **Done: the checker against glslang.** It accepts glslang's modules of
     `tools/gpu_kernel_refs/*.comp`. A module written by `spv-write` reads
     back (`spv-read`) word for word.
   * **Done: the workgroup-sweep kernel of ADR 0358** (`kir1-sweep`). It is
     the kernel of `scripts/gpu-workgroup-sweep/gen-wg-shaders.py`: 256
     `GLSL.std.450` Fma per invocation, with LocalSize 32..1024 as the only
     difference between the six modules. The constant 1.0000001 is the f32
     `0x3f800001`, as in glslang's module.
   * **Done: the subgroup reductions** (`kir1-subgroup-reduce`: sum, max and
     min). Each subgroup folds with `OpGroupNonUniformFAdd`, `FMax` or `FMin`
     (Reduce). Its first invocation stores the result per `SubgroupId`. After
     a barrier, invocation 0 folds the `NumSubgroups` partials in order. The
     modules declare `GroupNonUniform` and `GroupNonUniformArithmetic`.
     Running them needs Vulkan 1.1 subgroup arithmetic in compute: a
     provider check, ADR 0371 step 6.
   * **Done: the Kotoba checker accepts glslang's modules** of all four
     references in `tools/gpu_kernel_refs/`. That includes the sweep and the
     subgroup sum, so the checker covers modules that Amu did not write.
   * **Receipts.** In `docs/evidence/gpu-kernel-spirv-20261022/`:
     * 23 modules, all valid under `spirv-val --target-env vulkan1.1`;
     * byte-identical from the aarch64 and the x86_64 tool images;
     * 75 Kotoba cases, plus the control.
   * **Remaining:** the `accelerator_targets` and `accelerator_variants` rows
     of Decision 4, on the W3 port. They wait for the CLJK-to-Kotoba port of
     those files (#1478, #1481), so that the two efforts do not edit the same
     files.
3. **KIR v2 and the inference kernels, B70/ANV first:**
   * **Done: the KIR v2 builder** (`tools/gpu_kernel_kir2.kotoba`). A kernel
     is a Kotoba function of its parameters that calls builder functions:
     * ids are allocated, and types and constants are interned;
     * the module's sections are kept apart and written in the logical
       layout by `kb-module`;
     * buffers, the parameter block, shared arrays and built-ins are globals;
       variables live in Function storage;
     * loops take glslang's four-block form and an if is `OpSelectionMerge`
       before its branch. A guarded load is computed inside an if into a
       variable, never through `OpSelect`;
     * the capabilities follow the features used;
     * an if, loop or break out of place traps, as do an unclosed if or
       loop at `kb-module` and a full section. Nothing is emitted with a
       branch to id 0.
   * **Done: the first two kernels** (`tools/gpu_kernels_v2.kotoba`):
     * KIR v1's elementwise kernel again (4 operators x 2 workgroup sizes),
       as the proof of the lowering;
     * `attn_copy_dense`, statement for statement from kotoba-lang/inference
       at 808e5f0. That revision has one cache writer per kv group, and it
       reads the current position from DK/DV.
   * **Checks.** `scripts/seed/check-gpu-kernel-spirv.py --suite kir2` builds
     `tools/gpu_kernel_kir2_test.kotoba`; it has 29 cases plus the control:
     * the module shapes;
     * one word apart per parameter;
     * the same words twice;
     * the Kotoba checker accepts glslang's module of the same source.

     Results:
     * all 9 modules are valid under `spirv-val`;
     * the modules are byte-identical from the aarch64 and the x86_64 tool
       images.

     Phase `gpu` runs after the oracle phase. It runs every module through
     the ADR 0371 provider, after checking the bytes against the build's.
     Where glslang has a module of the same source, it runs that beside the
     KIR v2 module. On gad (RADV):
     * **The eight ewise modules.** add, sub and mul are exact. div is within
       2 ulp; Vulkan allows `OpFDiv` 2.5. Both workgroup sizes give the same
       bytes, and add gives glslang's bytes.
     * **`attn_copy_dense`, in three shapes.** The outputs are byte-identical
       to glslang's module and within 1e-7 of an f64 reference. The cache rows
       written are exact.

     Receipts: `docs/evidence/gpu-kernel-kir2-20261023/`.
   * **Done: the nex_ops decode set.** 19 ops of kotoba-lang/inference
     `nex_ops.comp` at 971376a. Each is the module that glslang's
     `-DOP=<op>` gives, in its decode variant (not BATCH, BPREFILL or BIAS):
     * rmsnorm, l2norm, gated_rmsnorm and add_rmsnorm;
     * silu_mul, conv1d_step, gate_decay, gate_decay2, copy_at,
       weighted_sum, add, add_bias and pos_incr;
     * f32_matvec;
     * rope_neox (NEOX and NORMAL pairs, rope_freqs);
     * attn_decode (with the output gate);
     * softmax_topk, argmax_partial and argmax_final.

     Every module has nex_ops' seven bindings. The builder gained:
     * conversions and bit casts;
     * more `GLSL.std.450` calls;
     * ordered float comparisons and `OpSelect`;
     * early return and `continue`;
     * `memoryBarrierBuffer`.

     A load that a condition guards stays in an if: `ids[0]` (read only
     when `P.p1 != 0`), the output gate's `s[gi]` and softmax_topk's
     `a[row n + t]`. So does rope's division `h / P.rows`.

     Results:
     * the suite has 45 Kotoba cases;
     * all 28 modules are `spirv-val` valid;
     * the Kotoba checker accepts glslang's 19 modules.

     On gad (RADV), 32 cases ran glslang's module and the KIR v2 module on the
     same inputs, and every writable binding is byte-identical:
     * copy_at, add, add_bias, pos_incr and both argmax stages are exact,
       ties at the maximum included, and the token-buffer write keeps its
       guard (`pos + 1 >= P.aux2`, and only when `P.p1 != 0`);
     * softmax_topk picks the same experts as f64;
     * rmsnorm, f32_matvec and the top-k weights are within 3e-6 of f64.

     Receipts: `docs/evidence/gpu-kernel-kir2-nex-20261023/`.
   * **Done: the rest of nex_ops' decode ops**, with the same seven bindings:
     * the resident-serving ops: quant_q8, pos_incr2, ctl, pos_add, pos_seed
       and params;
     * the sampler: sample_topp on one workgroup, and the multi-workgroup
       chain sample_part, sample_probs, sample_bisect_part,
       sample_bisect_step and sample_final.

     The sampler uses:
     * the mix32 hash;
     * thread 0's serial exclusive prefix;
     * a shared scalar, as a one-element shared array;
     * a descending scan with `break`.

     On gad:
     * every op is byte-identical to glslang's module, including the whole
       63-dispatch chain (n = 10000: part, probs, 30 bisection rounds,
       final), down to the pick and the token-buffer write;
     * the resident ops other than quant_q8 are exact. quant_q8 matches
       glslang's module, but RADV computes its scale as `m * (1/127)`, so it
       is not exact against a correctly rounded division;
     * sample_topp also ran at a static position and inside the prompt,
       where the token buffer stays untouched.

     `c[0]` and embed's `pos[0]` are read only under their guards, as in the
     GLSL. The top-of-range pick (`target >= total`) was checked by reading
     only.
   * **Done: deltanet and embed.**
     * `deltanet_step` (inference at 9aab2b1).
     * `deltanet_fused` (at ee9ebc5), decode variant. It has 512
       invocations and 13 bindings, a conv ring double-buffered by the
       position's parity, and the state's key dimension in four quarters.
     * `embed_iq4xs` (at c7ea9a9), in all seven decode variants: IQ4_XS, and
       `-DQ8`, `-DB32=2/3/6/7` and `-DPTQ1` as generator parameters. The
       B32 variants keep the `+ m` of 0.0, because `-0.0 + 0.0` is `+0.0`.

     On gad each is byte-identical to glslang's module. deltanet_step is
     within 4.1e-6 of f64; deltanet_fused was run at a fresh position, with
     history, and on row 1 (ring, state and output); the Q8 embedding is
     exact.

     Receipts (with the rest of nex_ops' decode ops):
     `docs/evidence/gpu-kernel-kir2-dn-20261023/`.
   * **Done: the BATCH, BPREFILL and BIAS variants of nex_ops, deltanet and
     embed.** Each variant is a generator parameter, and the decode modules
     keep their bytes.
     * nex_ops (`kir2-nex-variant op v`), the 20 that differ from decode:
       * copy_at, attn_decode and ctl in BATCH and BPREFILL;
       * pos_incr, argmax_partial, argmax_final and params in BATCH;
       * pos_add and pos_seed in BPREFILL;
       * rope_neox in BATCH, BIAS and both;
       * the five multi-workgroup sampler kernels in BATCH.
     * `deltanet_fused` in BATCH and BPREFILL: the ring and the state of
       sequence `seq` sit at `seq 6 n` and `seq heads K V`.
     * embed in BATCH and BPREFILL, for each of its seven kinds.

     The unit made about 165 builders and ran out of memory, so the
     builder's reserve shrank from 2.2M to 591632 words. One provider
     session holds 127 pipelines, so the gate runs the variants in a second
     session.

     On gad, in 35 cases, every variant is byte-identical to glslang's
     module of the same defines:
     * rope is within 8.9e-7 of f64 and attn_decode within 5e-8; the rest
       are exact;
     * the inputs separate what a wrong port could mix up: two strides,
       base and sequence, `ids[r]` and `ids[1]`, and two kv heads;
     * the BATCH sampler chain ran over three rows. One row has T = 0, and
       every kernel skips it.

     Receipts: `docs/evidence/gpu-kernel-kir2-var-20261024/`.
   * `attn_copy_dense` on B70/ANV;
   * **Done: the dot and kdot fixtures' kernels.**
     * `dot_rows`, from inference at 0f5824c.
     * `kdot_f32_r1`, from inference at c7ea9a9. This is the ggml quantized
       dot with f32 activations. Every tensor type is in one module, as in
       the GLSL: Q4_K, Q5_K, Q6_K, IQ4_XS, Q8_0, Q4_0, F16, BF16, PQ2_0,
       PTQ1_0, Q4_1, Q5_0 and Q5_1. Each GLSL helper is a Kotoba function
       that writes its code inline.

     The builder gained vectors: construction, `OpDot`, signed conversion,
     `unpackHalf2x16` and `bitfieldExtract`. The second word of
     `weight_u32_at`, and the q4/q5 and pq2/ptq1 picks, are guarded loads,
     so they stay in an if. `spirv-val` caught integer subtractions typed
     u32 that build ivec4s; the Kotoba checker does not check types.

     On gad (RADV), with random weights for every type, glslang's module and
     the KIR v2 module are byte-identical on:
     * two positions on two experts that differ from the positions;
     * a workgroup past the rows and a position past the positions;
     * a tail group for the 32-value types;
     * the prefill-MoE and shared-input rows (`pad0`, `pad1`,
       `input_per_expert`).

     F16, BF16 and Q8_0 are within 2.5e-06 (relative) of an f64 dequant.
     `dot_rows` is byte-identical too, and within 2.4e-6 of f64.

     `kdot_f32_r8`, from inference at f57ea5e, has R rows per workgroup (the
     GLSL's `-DROWS`, a generator parameter), with `acc[R]` and `mins[R]` in
     Function arrays and r8's ten tensor types. It shares r1's helpers
     (a flag drops BF16, PQ2_0 and PTQ1_0). On gad it is byte-identical to
     glslang's module for:
     * every r8 type with 8 rows;
     * two types with `-DROWS=4`;
     * one each with 16 and with 32.

     The rows were 22, or 40 for R = 32, so the last workgroup is partial for
     every R.

     Receipts: `docs/evidence/gpu-kernel-kir2-kdot-20261023/`.
   * **Done: the x8 kdot kernels** (inference at b1e85d0). On the x8
     mapping, 256 invocations are 8 block slots of 32 lanes, and each lane
     owns eight consecutive values.
     * `kdot_x8r8`, and `kdot_x8r4` (its `-DROWS=4` build, the decode path's
       wide kernel): f32 activations from a vec4 binding, two dots per arm.
     * `kdot_i8_x8r4`: int8 activations (quant_q8's packed words and one
       scale per 32) with the packed integer dot product.

     The int8 kernel is glslang's form at SPIR-V 1.3:
     * the `SPV_KHR_integer_dot_product` extension;
     * the `DotProduct` and `DotProductInput4x8BitPacked` capabilities;
     * `OpSDot` with `PackedVectorFormat4x8Bit`.

     The builder's `kb-sdot4x8` marks the module, and `kb-module` declares
     these.

     On gad (RADV), each is byte-identical to glslang's module. The runs
     used 16 blocks, so every block slot takes two, and positions on experts
     that differ from them:
     * x8: every tensor type with 8 rows per workgroup, two with 4 and one
       with 16, plus the prefill-MoE and shared-input rows;
     * int8: every type with 4 rows, two with 8 and one with 16, plus the
       same rows.

     A probe session reads the provider's features first. The int8 kernel
     runs only where `:shader-integer-dot-product` is enabled, and is
     recorded as skipped elsewhere. For these receipts the provider came
     from the device-features branch (#1534), since no provider on main
     enables the feature yet; with this tree's own provider, every other
     case passes. Receipts: `docs/evidence/gpu-kernel-kir2-x8-20261023/`.
   * **Done: the nvgpu-h2 kernels**, which the decode path's `nvgpu-h2`
     layout (Xavier) uses. All are from inference main:
     * `kdot_h2_r1` (at c21beff), plain and `-DQ6_HALF`;
     * `kdot_h2_r4_q8` (b5f7ca3) and `kdot_h2_r8_q8` (b3dfa34);
     * `kdot_h2_qkv_q8` and `kdot_h2_qkvr_q8` (ee95e44).

     They compute their per-value products in packed f16 and reduce by
     `subgroupAdd`. The builder gained the 16-bit float (`Float16`),
     constant vectors, shuffles, `OpFConvert`, and subgroup add and elect.
     The f16 forms are glslang's, so the driver sees the same conversions.

     On gad (RADV), in 33 cases, every kernel is byte-identical to glslang's
     module:
     * every type and odd group counts with a trailing group masked in part;
     * outputs that start as a sentinel;
     * the same cases again with `RADV_PERFTEST=cswave32`, where a probe
       shows two subgroups per workgroup, as nvgpu's 32-wide warps give.

     The gate runs them only where the provider enables `shaderFloat16`.
     `kdot_h2_qkvr_q8` writes its rows with no position term, so it is
     decode-only and runs at one position.

     Not yet run on Xavier itself: the ADR 0371 provider and this gate run on
     x86_64 only, so an nvgpu run waits on the provider for aarch64.
     Receipts: `docs/evidence/gpu-kernel-kir2-h2-20261024/`.
4. **Execution.** Through the ADR 0371 provider, with numeric and speed gates
   against the hand-written kernels.
   * **On gad: the kernels on real tensors.** `scripts/seed/check-gpu-kernel-exec.py`
     takes the product route: a static guest, the static launcher, and the
     confined Vulkan provider. It ran KIR v2's modules and glslang's on six
     fixtures:
     * kotoba-lang/inference's four kdot fixtures (Q5_K, two IQ4_XS, and the
       Q6_K lm_head);
     * a Q4_K tensor;
     * a real F32 matvec for `dot_rows`.

     The layouts were r1, r8, x8r4 and h2r1, the lm_head's r1, x8r4 and
     h2q6r1, and the decode argmax chain.
     * Every output is byte-identical to glslang's. The output buffers start
       as NaN before each layout, so an unwritten row fails.
     * Against an f64 dequant oracle, the f32 layouts are within 5.4e-5
       (kdot_check's metric, gate 1e-3). The h2 layouts compute in f16 and
       are within 5.3e-3 of the output's rms (gate 1e-2).
     * The argmax chain's 61 partials match glslang's and the logits it ran
       on, and its pick is the f64 argmax.
     * Speed: KIR v2's median 10-dispatch command buffer (seven rounds,
       alternating with glslang's) took 0.93-1.07 times glslang's on gad and
       on ANV. The gate is 1.25, where glslang's median buffer takes at least
       0.5 ms; shorter, launch-bound ones are recorded but not gated.

     Receipts: `docs/evidence/gpu-kernel-exec-20261024/`.
   * **ANV (Intel BMG G31, the B70).** The whole kir2 suite is
     byte-identical to glslang's modules there too, including int8 and h2.
     Its subgroups are 32 wide, so the h2 kernels run two per workgroup.

     The exec gate found one speed gap. On attn_qkv, KIR v2's x8r4 took 1.37
     times glslang's time, and the cause was visible in ANV's compile
     statistics:
     * KIR v2's module failed SIMD32 register allocation and fell back to
       SIMD16.
     * Its `q4_scale` and `q4_min` loaded both forms and picked one with
       `OpSelect`, where the GLSL returns early. A driver does not
       speculate a storage load, so the selection's form kept every byte
       load live at once.

     The same rule applies to the h2 kernels' `h_scale` and `h_min`. Written
     as the GLSL's branch, x8r4 compiles to SIMD32 and runs at glslang's
     speed.

     The lm_head's r1 and h2q6r1 dispatch one workgroup per row, 248320 of
     them. That is past Vulkan's guaranteed `maxComputeWorkGroupCount` of
     65535, which is ANV's. So on ANV the lm_head runs x8r4 and r8 (the
     argmax chain on x8r4's logits), as the decode path's ANV table does.
   * Not yet: the whole decode guest through tokens, and Xavier (which needs
     the provider on aarch64).
   * **After #1510.** These GPU runs go through the ADR 0371 provider. Main's
     compiler no longer builds it (`--format platform-linked` is refused),
     and its qualifications are excluded from mandatory native CDCI (main's
     AGENTS.md).
     * The modules, the Kotoba unit and the oracles stand on main's route:
       static images and spirv-val.
     * The GPU receipts above are historical, from providers the earlier
       root built. They are not native gates.
5. **Retirement.** Remove `emit-kernel.cljk`, glslang and the accelerator CLJK
   from the product route. The hand `.comp` files stay as baselines.
