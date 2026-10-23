# KIR v2 receipts: the x8 kdot kernels (ADR 0372 step 3, JUN-356)

`tools/gpu_kernels_v2.kotoba` writes the kdot kernels of the x8 thread
mapping (256 invocations as 8 block slots of 32 lanes, a lane owning eight
consecutive values), from kotoba-lang/inference at b1e85d0:
* `kir2-kdot-x8 R`: `verify/native/gpu/kdot_x8r8.comp` (R = 8), and its
  `-DROWS=4` build `kdot_x8r4`, the decode path's wide kernel. The f32
  activations come from a vec4 binding.
* `kir2-kdot-i8-x8 R`: `verify/native/gpu/kdot_i8_x8r4.comp` (R = 4 by
  default). It takes int8 activations (quant_q8's packed words and one scale
  per 32) and uses the packed 4x8 integer dot product: glslang's SPIR-V 1.3
  form, with `SPV_KHR_integer_dot_product`, `DotProduct`,
  `DotProductInput4x8BitPacked` and `OpSDot` `PackedVectorFormat4x8Bit`.

`tools/gpu_kernel_refs/kdot-x8r8.comp` and `kdot-i8-x8r4.comp` are those files,
as oracle inputs. The refs phase compiles each twice: x8r8 by default and with
`-DROWS=4`, and i8 by default and with `-DROWS=8`. The receipts cover the
whole kir2 suite.

## Files

* `aarch64-linux.json`: `scripts/seed/check-gpu-kernel-spirv.py --suite kir2`.
  * The refs and oracle phases ran on the developer host (macOS, arm64).
  * The build phase ran on arm64 Linux (podman machine, native), with the
    pinned root (`bd025475…`) as `--compiler` and an
    aarch64 tool image.
* `x86_64-linux.json`: the same with an x86_64 tool image, run under
  qemu-user on arm64 Linux (`--seccomp-if-available`, recorded).
* `gad-radv.json`: the aarch64 receipt with the `gpu` phase added. It ran on
  gad (x86_64, Radeon 8060S Graphics, RADV GFX1151, Vulkan 1.4.318), confined.
  * **The provider came from the device-features branch**
    (`claude/provider-features` at 47b7fc95, built by that branch's root). The
    int8 kernel needs `shaderIntegerDotProduct` enabled, and no provider on
    main enables it yet (ADR 0372 Decision 5).
  * The provider reported `:features #{:storage-buffer-16bit :storage-buffer-8bit :shader-float16 :shader-int8 :synchronization2 :shader-integer-dot-product :subgroup-size-control :compute-full-subgroups}`.
    The gate requires `:shader-integer-dot-product` among them.
  * libvulkan runs on GPU hosts only (owner decision, 2026-10-22). The run's
    temporary directory was removed.

## What the receipts show

* **The unit**: 85 Kotoba cases pass, and the control fails
  exactly once. For x8 and i8:
  * the modules and glslang's (both builds of each) pass the Kotoba checker;
  * LocalSize is 256;
  * x8 has twelve `OpDot` (two in each of the six arms; Q4_K and Q5_K share
    one), as glslang's module does;
  * i8 has twelve `OpSDot` (ysum's two, and two in each of the five integer
    arms), three capabilities and the extension;
  * a row count other than 4, 8, 16 or 32 gives an empty module.
* **Oracles**: all 36 modules are valid under `spirv-val
  --target-env vulkan1.1`, and the two tool images write the same bytes.
* **GPU**: each case ran with 20 rows (the last workgroup partial) and one
  workgroup past them, two positions, and experts 0 and 1. The weights are
  random bytes with the f16/bf16 inf/NaN patterns defused.
  * `kdot_x8r8`: all seven tensor types (Q4_K, Q5_K, Q6_K, IQ4_XS, Q8_0,
    Q4_0, F16) with 8 rows per workgroup, and Q5_K and Q4_0 with 4. All are
    byte-identical to glslang's modules.
  * `kdot_i8_x8r4`: all seven types with 4 rows per workgroup, and Q6_K and
    IQ4_XS with 8. The activations are random packed int8 with positive
    scales. All are byte-identical to glslang's modules.

glslang is a test oracle only.
