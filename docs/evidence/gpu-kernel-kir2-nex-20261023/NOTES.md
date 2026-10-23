# KIR v2 receipts: the nex_ops decode set (ADR 0372 step 3, JUN-356)

`tools/gpu_kernels_v2.kotoba` `kir2-nex-op` writes 19 ops of
kotoba-lang/inference `nex_ops.comp` at 971376a, in their decode variants
(not BATCH, BPREFILL or BIAS). `tools/gpu_kernel_refs/nex-ops.comp` is that
file, an oracle input. The receipts cover the whole kir2 suite: the ops of
`docs/evidence/gpu-kernel-kir2-20261023/` (ewise, attn_copy_dense) are in
them too.

## Files

* `aarch64-linux.json`: `scripts/seed/check-gpu-kernel-spirv.py --suite kir2`.
  * The refs phase (glslangValidator, once per `-DOP` for nex-ops.comp) and
    the oracle phase (spirv-val and spirv-dis) ran on the developer host
    (macOS, arm64).
  * The build phase ran on arm64 Linux (podman machine, native), with the
    pinned root (`bd025475…`) as `--compiler` and an aarch64 tool image.
* `x86_64-linux.json`: the same with an x86_64 tool image, run under
  qemu-user on arm64 Linux (`--seccomp-if-available`, recorded).
* `gad-radv.json`: the aarch64 receipt with the `gpu` phase added.
  * It ran on gad: x86_64, Radeon 8060S Graphics (RADV GFX1151), Vulkan
    1.4.318, through the ADR 0371 provider (the provider-vulkan image of a
    `check-gpu-provider.py` build from the same tree), confined (Landlock and
    the seal).
  * By the owner's decision of 2026-10-22, libvulkan runs on GPU hosts only.
    The run used a temporary directory that was removed afterwards.

## What the receipts show

* **The unit**: 45 Kotoba cases pass, and the control fails exactly once.
  * Every op's module passes the Kotoba checker and is written; so does
    glslang's module of the same `-DOP`.
  * Shapes: loops, early returns, selections, the `GLSL.std.450` calls,
    `memoryBarrierBuffer`, the bit casts, the variables; an unknown op gives
    an empty module.
* **Oracles**: all 28 modules are valid under `spirv-val --target-env
  vulkan1.1`; the aarch64 and the x86_64 tool images write the same bytes.
* **GPU** (`gad-radv.json`): 24 nex cases. In each, glslang's module and the
  KIR v2 module ran on the same inputs (24-bit values from a fixed LCG, exact
  in f32; the receipt records the digests of the inputs and outputs), and
  every writable binding (B, O, S, I) is byte-identical. The cases:
  * rmsnorm (a row stride, and contiguous), l2norm (scale 0 and 0.5),
    gated_rmsnorm, add_rmsnorm;
  * silu_mul, conv1d_step (the state shift), gate_decay and gate_decay2
    (softplus on both arms), copy_at (dynamic and static position),
    weighted_sum, add, add_bias, pos_incr;
  * f32_matvec (64 rows x 1024, two input rows);
  * rope_neox (NEOX pairs at the dynamic position with a copied tail; NORMAL
    pairs at P.aux2, two heads per token, with rope_freqs);
  * attn_decode (the interleaved output gate at the dynamic position with
    GQA; dense with P.aux and two rows, where the gate's buffer is a stub);
  * softmax_topk (two tokens over 128 experts, top 8);
  * argmax_partial and argmax_final (ties at the maximum inside a workgroup,
    across workgroups and between partials; the token-buffer write).

  Beyond the byte identity:
  * copy_at, add, add_bias, pos_incr and both argmax stages are exact;
  * softmax_topk picks the same experts as an f64 reference;
  * rmsnorm, f32_matvec and the top-k weights are within 3e-6 of f64.

glslang and the f64 references are test oracles only; neither is in the
product route.
