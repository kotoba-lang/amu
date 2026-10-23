# KIR v2 receipts (ADR 0372 step 3, JUN-356)

`tools/gpu_kernel_kir2.kotoba` is the KIR v2 builder; `tools/gpu_kernels_v2.kotoba`
writes two kernels with it: KIR v1's elementwise kernel again, and
`attn_copy_dense` from kotoba-lang/inference at 808e5f0
(`tools/gpu_kernel_refs/attn-copy-dense.comp` is that file, an oracle input).

## Files

* `aarch64-linux.json`: `scripts/seed/check-gpu-kernel-spirv.py --suite kir2`.
  * The refs phase (glslangValidator) and the oracle phase (spirv-val and
    spirv-dis) ran on the developer host (macOS, arm64).
  * The build phase ran on arm64 Linux (podman machine, native), with the
    pinned root (`8385ac69…`, main at 2246f2fb) as `--compiler` and an
    aarch64 tool image.
* `x86_64-linux.json`: the same with an x86_64 tool image, run under
  qemu-user on arm64 Linux (`--seccomp-if-available`, recorded).
* `gad-radv.json`: the aarch64 receipt with the `gpu` phase added.
  * It ran on gad: x86_64, Radeon 8060S Graphics (RADV GFX1151), Vulkan
    1.4.318, through the ADR 0371 provider (the provider-vulkan image of a
    `check-gpu-provider.py` build from the same tree), confined (Landlock and
    the seal).
  * By the owner's decision of 2026-10-22, libvulkan runs on GPU hosts only.
    The run used a temporary directory that was removed afterwards.
* `kir2-attn-copy-dense.spv.dis`: `spirv-dis --raw-id` of the KIR v2 module.

## What the receipts show

* **The unit**: 29 Kotoba cases pass, and the control (one expectation made
  wrong) fails exactly once.
  * The module shapes: loops, selections, barriers, `OpSelect`, the
    `GLSL.std.450` calls, the variables and the interface.
  * Each kernel parameter (workgroup size, operator) changes exactly one
    word; the same parameters give the same words; invalid parameters give
    an empty module, as in KIR v1.
  * The Kotoba checker accepts the 9 modules and glslang's module of the
    same `attn_copy_dense` source.
* **Oracles**: all 9 modules are valid under `spirv-val --target-env
  vulkan1.1`. The aarch64 and the x86_64 tool images write the same bytes.
* **GPU** (`gad-radv.json`): the phase ran after the oracle phase, and it
  checks the bytes it runs against the build's and the refs phase's. Every
  KIR v2 module ran. Where glslang has a module of the same source, it ran
  beside it on the same inputs (24-bit values from a fixed LCG, exact in f32;
  the receipt records their digests).
  * ewise, all eight modules over 1000 values:
    * add, sub and mul are exact;
    * div is within 2 ulp (Vulkan allows `OpFDiv` 2.5);
    * each operator's two workgroup sizes give the same bytes;
    * add/wg256 gives the bytes of glslang's module of
      `tools/gpu_kernel_refs/ewise-add.comp`.
  * `attn_copy_dense`, three shapes:
    * GQA (8 query heads, 2 kv heads, d = 64) at the dynamic position
      (P.p1 != 0, T = 38);
    * no GQA (8 heads, d = 128) with P.aux = 200 and two rows (T = 200, 201);
    * d = 320 (two i per invocation) with T = 256, the kernel's largest.

    In each:
    * the cache rows that phase 1 writes equal the expected copy byte for
      byte;
    * the two modules' outputs are byte-identical (the gate requires it);
    * both are within 1e-7 of an f64 reference of the same math (largest
      7.3e-8, at d = 320; the gate's bound is 1e-5).

The f64 reference and glslang are test oracles only; neither is in the
product route.
