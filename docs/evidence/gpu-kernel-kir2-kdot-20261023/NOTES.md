# KIR v2 receipts: the dot and kdot kernels (ADR 0372 step 3, JUN-356)

`tools/gpu_kernels_v2.kotoba` writes the kernels of ADR 0371 step 6's dot
and kdot fixtures:
* `kir2-dot-rows`: `dot_rows`, from kotoba-lang/inference
  `verify/native/gpu/dot_rows.comp` at 0f5824c;
* `kir2-kdot-f32-r1`: `kdot_f32_r1`, from
  `resources/kotodama/inference/kernels/native/kdot_f32_r1.comp` at
  c7ea9a9;
* `kir2-kdot-f32-r8`: `kdot_f32_r8`, from `verify/native/gpu/kdot_f32_r8.comp`
  at f57ea5e, with R rows per workgroup.

`tools/gpu_kernel_refs/dot-rows.comp`, `kdot-f32-r1.comp` and
`kdot-f32-r8.comp` are those files, as oracle inputs. The refs phase compiles
r8 twice, by default and with `-DROWS=4`. The receipts cover the whole kir2
suite.

## Files

* `aarch64-linux.json`: `scripts/seed/check-gpu-kernel-spirv.py --suite kir2`.
  * The refs and oracle phases (glslangValidator, spirv-val and spirv-dis)
    ran on the developer host (macOS, arm64).
  * The build phase ran on arm64 Linux (podman machine, native), with the
    pinned root (`bd025475…`) as `--compiler` and an aarch64 tool image.
* `x86_64-linux.json`: the same with an x86_64 tool image, run under
  qemu-user on arm64 Linux (`--seccomp-if-available`, recorded).
* `gad-radv.json`: the aarch64 receipt with the `gpu` phase added. It ran on
  gad (x86_64, Radeon 8060S Graphics, RADV GFX1151, Vulkan 1.4.318), through
  the ADR 0371 provider, confined. libvulkan runs on GPU hosts only (owner
  decision, 2026-10-22); the run's temporary directory was removed.

## What the receipts show

* **The unit**: 66 Kotoba cases pass, and the control fails exactly once. For
  dot and kdot:
  * the modules and glslang's pass the Kotoba checker;
  * dot_rows returns early;
  * kdot has LocalSize 64, eleven `OpDot` (one per tensor-type arm, as in
    glslang's module), fourteen `unpackHalf2x16` and eight
    `bitfieldExtract`;
  * r8 has nine `OpDot` (its arms), the same words twice, and an empty
    module for a row count other than 4, 8, 16 or 32.
* **Oracles**: all 32 modules are valid under `spirv-val --target-env
  vulkan1.1`, and the two tool images write the same bytes. spirv-val
  rejected a first build of kdot: integer subtractions that build `ivec4`s
  were typed u32, which the Kotoba checker does not see.
* **GPU** (`gad-radv.json`):
  * `dot_rows`: 64 rows of 1000, with two workgroups past the rows. The
    output is byte-identical to glslang's module and within 2.4e-6 of f64.
  * `kdot_f32_r1`, all 13 tensor types (Q4_K, Q5_K, Q6_K, IQ4_XS, Q8_0,
    Q4_0, F16, BF16, PQ2_0, PTQ1_0, Q4_1, Q5_0, Q5_1). Each type ran with:
    * 8 rows and two positions, each reading its own input row;
    * experts 0 and 1;
    * a workgroup past the rows;
    * for the 32-value types, 480 columns, so the tail group is skipped.

    The weights are random bytes. Any half whose f16 or bf16 exponent was
    all ones has bit 14 cleared, so the scales stay finite. F16 and BF16 use
    halves of 24-bit values.

    In each type, glslang's module and the KIR v2 module give byte-identical
    outputs, finite and not all zero. F16, BF16 and Q8_0 are also within
    6.3e-7 (relative) of an f64 dequant.
  * `kdot_f32_r8`: byte-identical to glslang's module for each of its ten
    tensor types with 8 rows per workgroup, and for Q4_K and Q8_0 with
    `-DROWS=4`. Each ran with 20 rows (so the last workgroup is partial) and
    one workgroup past them, two positions and experts 0 and 1.

glslang and the f64 references are test oracles only.
