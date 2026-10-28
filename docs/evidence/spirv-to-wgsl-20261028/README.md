# SPIR-V to WGSL, from the Mac-native compiler (2026-10-28, ADR 0379, JUN-377)

`tools/spirv_to_wgsl.kotoba` translates KIR v2 SPIR-V modules to WGSL. The
files in [`wgsl/`](wgsl/) are its output, byte for byte, for seven kernels of
`tools/gpu_kernels_v2.kotoba`, built and run with the pinned
`seed/bootstrap/aarch64-macos` root and packager on Apple M1 Max
(`run-mac-native.sh` is the compile, extract, package, sign, run sequence).

| kernel | WGSL chars | wgpu validation (Deno WebGPU) |
|---|---|---|
| dot-rows | see file | ok |
| ewise (add, wg 64) | 577 | ok |
| attn-copy-dense | 5419 | ok |
| kdot-f32-r1 | 36782 | ok |
| kdot-f32-r8 (R 4) | 31105 | ok |
| kdot-x8 (R 4) | 33500 | ok |
| kdot-i8-x8 (R 4) | 28438 | ok (needs `requires packed_4x8_integer_dot_product;`) |

Numeric checks, generated WGSL as is, on Apple M1 Max through Deno's WebGPU
(wgpu on Metal):

* `dot-rows` (browser WebGPU, 4096 x 4096 f32): max relative error 1.5e-5
  against an f64 sum; 0.213 ms per dispatch.
* `kdot-f32-r1` on synthetic Q8_0 (`q8parity.js`; f16 scales exactly
  representable, int8 values, f32 activations; the oracle is an f64 sum of the
  dequantised weights):
  * 64 rows x 1024, 3 positions: max relative error 5.2e-6.
  * 4096 x 4096, 1 position: max relative error 1.5e-4, **0.432 ms per
    dispatch, 41 GB/s of Q8_0 weight reads**.

For scale, on the same host the f32 `dot-rows` stream reads 300+ GB/s and
`llama-bench` tg128 on Qwen2.5-0.5B Q8_0 is 236 tok/s (about 125 GB/s of
weights; `verify/evidence/qwen25-0p5b-dense-selfhost-vs-llamacpp-m1max-20261019.json`
in kotoba-lang/inference). The dequantising kdot is the kernel-bandwidth gap
AWAI-6 names; this run shows it in WGSL too, so it is a property of the
kernel layout and not of SPIR-V. It is a kernel microbenchmark, not a decode
rate, and not comparable to `llama-bench` or to vLLM.

`oracle.js` and `q8parity.js` are test-time oracles (Deno's WebGPU); they are
not part of the product route. The product-route gate (headless Chrome with
WebGPU, no Node) is not written yet.

Not shown: the deltanet, embed, nex-op, h2 and subgroup kernels were not
translated; Float16 and subgroup output (`enable f16;`, `enable subgroups;`)
are not implemented; `break` / `continue` branches are refused.
