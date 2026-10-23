# KIR v2 receipts: the nvgpu-h2 kernels (ADR 0372 step 3, JUN-356)

`tools/gpu_kernels_v2.kotoba` writes the kernels that kotoba-lang/inference's
`nvgpu-h2` decode layout (Xavier) uses. Each comes from inference main's
`verify/native/gpu/`:
* `kir2-kdot-h2-r1 q6`: `kdot_h2_r1.comp` at c21beff, and with q6 1 its
  `-DQ6_HALF` build (the lm_head's `kdot_h2q6_r1`). It is one row a
  workgroup over Q4_K, Q5_K, Q6_K, IQ4_XS, Q8_0, Q4_0 and F16.
* `kir2-kdot-h2-q8 R`: `kdot_h2_r4_q8.comp` (b5f7ca3) and `kdot_h2_r8_q8.comp`
  (b3dfa34), with R rows a workgroup, Q8_0 only.
* `kir2-kdot-h2-qkv`: `kdot_h2_qkv_q8.comp` (ee95e44), the q, k and v matvecs
  in one dispatch.
* `kir2-kdot-h2-qkvr`: `kdot_h2_qkvr_q8.comp` (ee95e44), the same with the
  bias and the NeoX rope in the epilogue.

All of them compute their per-value products in packed f16 (two values an
instruction), sum the four products in f32, and reduce by `subgroupAdd`
with one partial per subgroup. The K-quant headers are staged in shared
memory.

The local inference checkout also holds `kdot_h2_gu_q8.comp` and newer
qkv/qkvr drafts that are not on main. They are not ported.

`tools/gpu_kernel_kir2.kotoba` gained:
* the 16-bit float, which declares `Float16`;
* constant vectors (`OpConstantComposite`) and shuffles;
* `OpFConvert`;
* `subgroupAdd` and `subgroupElect`.

The f16 forms are glslang's: `f16vec2(y.xy)` is a shuffle and one vector
conversion, and the exponent trick's biases are constant vectors. So the
driver is handed the same conversions. The capability lists match glslang's
(Shader, Float16, GroupNonUniform, GroupNonUniformArithmetic).

`tools/gpu_kernel_refs/kdot-h2-*.comp` are those files, as oracle inputs.
`subgroup-probe.comp` is a test probe that reports the subgroups of a
64-invocation workgroup.

## Files

* `aarch64-linux.json`: `scripts/seed/check-gpu-kernel-spirv.py --suite kir2`,
  with the pinned root (`bd025475…`) on arm64 Linux. The refs and oracle
  phases ran on the developer host.
* `x86_64-linux.json`: the same with an x86_64 tool image, under qemu-user
  (`--seccomp-if-available`, recorded).
* `gad-radv.json`: the aarch64 receipt with the `gpu` phase added. It ran on
  gad (x86_64, Radeon 8060S Graphics, RADV GFX1151, Vulkan 1.4.318), confined
  in all three sessions. The provider came from the device-features branch
  (#1534), which enables `shaderFloat16` and `shaderIntegerDotProduct`, so
  the h2 and int8 kernels ran.
* `gad-radv-main-provider.json`: the same phase with this tree's own
  provider (145 rows). The h2 and int8 kernels are recorded as skipped.
* The runs' temporary directories were removed.

## What the receipts show

* **The unit:** 147 Kotoba cases pass, and the control fails exactly once.
  The checker accepts glslang's modules. The 99 earlier modules are
  byte-identical to `gpu-kernel-kir2-var-20261024/`.
* **Oracles:** all 105 modules are valid under `spirv-val --target-env
  vulkan1.1`, and the two tool images write the same bytes.
* **GPU** (226 rows). In 33 h2 cases, every output buffer is byte-identical
  between glslang's module and the KIR v2 module, and finite. The outputs
  start as a sentinel with a 64-byte tail, so a write that a guard should
  have stopped would show.
  * **`kdot_h2_r1`**, every type:
    * the K-quants at 4096 columns (16 blocks, the most the staged headers
      hold);
    * the 32-value types at 4064 (a tail group), at 896, 4832 and 1152.
      4832 and 1152 have an odd group count, so the trailing single group
      runs, masked in part.

    The cases cover 8 rows and a workgroup past them, two positions on
    experts 1 and 0 and a position past them, a prefill MoE and a shared
    input. `-DQ6_HALF` ran Q6_K, Q4_K and Q8_0.
  * **The Q8_0 kernels.** R = 4 and 8 over 22 rows, so the last workgroup is
    partial, at 4864, 4832, 4064, 1152 and 896 columns.
  * **qkv.** Two query heads and one kv head of 64, at 1152 columns, with
    the plain and the prefill-MoE input rows.
  * **qkvr.** It writes `o[row]` with no position term, so it is
    decode-only and runs at one position, from input rows 0 and 1. The
    position came from `ids[0]` and from `RopeP.aux2`, each with and without
    the rope_freqs division.
  * **Two subgroups.** RADV runs a 64-invocation compute workgroup as one
    64-wide subgroup; nvgpu's warps are 32. Every h2 case therefore ran
    again in a third session with `RADV_PERFTEST=cswave32`.
    * The probe reads two subgroups there and one in the default session
      (`gl_SubgroupSize` reads 64 in both).
    * The modules are again byte-identical.
    * The outputs equal the first run's: wave64's add combines its two
      halves in the same order.

**Not run on Xavier itself.** The ADR 0371 provider and this gate run on
x86_64 only, so an nvgpu run waits on the provider for aarch64.

**Review.** Codex was at its usage limit, so an independent agent reviewed
the diff. It found no fidelity bug. It checked every generator line by line:
* the f16 and f32 types of each operation, and the order of float
  operations;
* the constants and masks;
* the guarded loads and the partial layouts.

It also compared disassemblies. Its findings are fixed:
* only one subgroup ran;
* the trailing single group was never masked in part;
* qkvr's position and rope_freqs choices moved together;
* a guard bug could only show as a race;
* the Float16 test could not fail;
* there were stale comments and dead variables.
