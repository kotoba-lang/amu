# KIR v2 receipts: deltanet, embed, and the rest of nex_ops (ADR 0372 step 3, JUN-356)

`tools/gpu_kernels_v2.kotoba` writes, from kotoba-lang/inference:
* `kir2-deltanet-step`: `verify/native/gpu/deltanet_step.comp` at 9aab2b1, the
  gated delta-net recurrence for one decode token, all heads.
* `kir2-deltanet-fused`: `verify/native/gpu/deltanet_fused.comp` at ee9ebc5,
  decode variant. One recurrent step of one head per workgroup: gate and beta,
  the conv1d step with silu, the l2 norms, the delta rule in four key
  quarters, and the gated rmsnorm times silu(z). It has 512 invocations and
  13 bindings.
* `kir2-embed kind`: `resources/kotodama/inference/kernels/native/embed_iq4xs.comp`
  at c7ea9a9, in its seven decode variants (IQ4_XS, `-DQ8`,
  `-DB32=2/3/6/7`, `-DPTQ1`).
* `kir2-nex-op` 20..31: the rest of `nex_ops.comp`'s decode ops:
  * quant_q8, pos_incr2, ctl, pos_add, pos_seed and params;
  * the sampler: sample_topp, and the multi-workgroup sample_part,
    sample_probs, sample_bisect_part, sample_bisect_step and sample_final.

`tools/gpu_kernel_refs/deltanet-step.comp`, `deltanet-fused.comp` and
`embed-iq4xs.comp` are those files, as oracle inputs. The refs phase compiles
embed once per variant and nex-ops once per op. The receipts cover the whole
kir2 suite.

## Files

* `aarch64-linux.json`: `scripts/seed/check-gpu-kernel-spirv.py --suite kir2`,
  with the pinned root (`bd025475…`) on arm64 Linux. The
  refs and oracle phases ran on the developer host.
* `x86_64-linux.json`: the same with an x86_64 tool image, under qemu-user
  (`--seccomp-if-available`, recorded).
* `gad-radv.json`: the aarch64 receipt with the `gpu` phase added. It ran on
  gad (x86_64, Radeon 8060S Graphics, RADV GFX1151, Vulkan 1.4.318), confined.
  The provider came from the device-features branch
  (`claude/provider-features` at 47b7fc95), because the suite's int8 kernel
  needs `shaderIntegerDotProduct` (see `gpu-kernel-kir2-x8-20261023/`). The
  run's temporary directory was removed.

## What the receipts show

* **The unit**: 98 Kotoba cases pass, and the control fails
  exactly once. The new modules and glslang's (every variant) pass the
  Kotoba checker.
* **Oracles**: all 57 modules are valid under `spirv-val
  --target-env vulkan1.1`, and the two tool images write the same bytes.
* **GPU** (105 rows). In every case, glslang's module and the KIR v2
  module ran on the same inputs, and every buffer the kernel writes is
  byte-identical:
  * `deltanet_step`: 4 heads on 2 key heads, K = V = 128, values at an
    offset, a workgroup past the heads. The state and the output are within
    4.1e-06 of f64.
  * `deltanet_fused`: at position 0 (no history: the ring and the state read
    as zero) and at position 5 (odd parity, with history). The ring, the
    state and the output are compared.
  * `embed`: every variant over two token rows of a six-token vocabulary,
    the slot from Meta, and IQ4_XS also from `pos[0]`. Q8 is exact against a
    dequant.
  * The resident ops are exact:
    * quant_q8;
    * pos_incr2, pos_add and pos_seed;
    * ctl, with and without the rewind flag;
    * params.
  * The sampler:
    * sample_topp, on 1000 logits, past the prompt;
    * the whole multi-workgroup chain, 63 dispatches over
      n = 10000 (part, probs, 30 bisection rounds, final). The pick
      (2197) lands in `ids[aux]` and in the token buffer.

glslang and the f64 references are test oracles only.
