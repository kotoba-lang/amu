# ADR 0372: GPU kernels are compiled through Amu selfhost into SPIR-V

Date: 2026-10-22
Status: Proposed. Owner direction 2026-10-22: GPU compilation goes through
selfhost as well. Step 1 (the encoder, the checker and the first kernel)
and most of step 2 (the reductions and the glslang cross-check) are
implemented; the vendor rows of step 2 and steps 3–5 are not.
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
   * **Receipts.** In `docs/evidence/gpu-kernel-spirv-20261022/`:
     * 14 modules, all valid under `spirv-val`;
     * byte-identical from the aarch64 and the x86_64 tool images.
   * **Remaining:**
     * the subgroup reduce;
     * the workgroup-sweep FMA kernel behind ADR 0358.
   * The `accelerator_targets` and `accelerator_variants` rows of Decision 4,
     on the W3 port.
   * Running the Kotoba checker over glslang's modules, as an oracle.
3. **KIR v2 and the inference kernels, B70/ANV first:**
   * the nex_ops decode set;
   * `attn_copy_dense`;
   * `kdot_f32_r1`, `kdot_x8r4`, `kdot_f32_r8` and `kdot_i8_x8r4`;
   * deltanet and embed;
   * then the nvgpu-h2 kernels for Xavier.
4. **Execution.** Through the ADR 0371 provider, with numeric and speed gates
   against the hand-written kernels.
5. **Retirement.** Remove `emit-kernel.cljk`, glslang and the accelerator CLJK
   from the product route. The hand `.comp` files stay as baselines.
