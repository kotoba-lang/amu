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
    (`claude/provider-features`, #1534). It enables
    `shaderIntegerDotProduct`; no provider on main does yet (ADR 0372
    Decision 5).
  * A session that serves nothing reads the provider's features first. The
    int8 pipelines are created and dispatched only when
    `:shader-integer-dot-product` is among them (`"int8": "ran"`).
* `gad-radv-main-provider.json`: the same `gpu` phase with the provider this
  tree builds, which does not enable the feature. Every other case passes,
  and the receipt records `"int8": "skipped: …"`.
* libvulkan runs on GPU hosts only (owner decision, 2026-10-22). The runs'
  temporary directories were removed.

## What the receipts show

* **The unit**: 97 Kotoba cases pass, and the control fails
  exactly once. For x8 and i8:
  * the modules pass the Kotoba checker, and so do glslang's, with
    `-DROWS` at 4, 8, 16 and 32;
  * LocalSize is 256;
  * x8 has twelve `OpDot` (two in each of the six arms; Q4_K and Q5_K share
    one), as glslang's module does;
  * i8 has twelve `OpSDot` (ysum's two, and two in each of the five integer
    arms), three capabilities and the extension;
  * R = 16 and 32 are written (and spirv-val checked), and a row count other
    than 4, 8, 16 or 32 gives an empty module.
* **Oracles**: all 42 modules are valid under `spirv-val
  --target-env vulkan1.1`, and the two tool images write the same bytes.
* **GPU**:
  * **The shape.** Each case ran with 4096 columns (4064 for the 32-value
    types, a tail in the last block), so 16 blocks and two for each of the
    eight block slots. The rows were 22, so the last workgroup is partial for
    R = 4, 8 and 16, with one workgroup past them.
  * **Positions.** Two positions ran on experts 1 and 0, so expert and
    position differ, plus one position past them.
  * **Weights.** Random bytes with the f16/bf16 inf/NaN patterns defused.
  * **`kdot_x8r8`.** All seven tensor types (Q4_K, Q5_K, Q6_K, IQ4_XS,
    Q8_0, Q4_0, F16) with 8 rows per workgroup; Q5_K and Q4_0 with 4; Q6_K
    with 16. Also a prefill MoE (`pad0 = 2`, `pad1 = 1`) and a shared
    input (`input_per_expert = 0`). All are byte-identical to glslang's
    modules.
  * **`kdot_i8_x8r4`.** All seven types with 4 rows per workgroup; Q6_K and
    IQ4_XS with 8; Q4_K with 16; and the prefill-MoE and shared-input
    shapes. The activations are random packed int8, negative values
    included, with positive scales. All are byte-identical to glslang's
    modules.
  * **R = 32 was not dispatched.** Its shared array is 32 KiB, above the
    16 KiB Vulkan guarantees (the GLSL has the same limit); it is built and
    validated.

glslang is a test oracle only.
