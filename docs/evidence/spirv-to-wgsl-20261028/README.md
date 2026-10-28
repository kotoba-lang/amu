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

## Layout comparison and two hand-written experiments (same host, 4096 x 4096 Q8_0, one position)

Generated kernels (`q8parity.js <file> 4096 4096 1 <kernel> <R>`; each runs three to
five times, ms and GB/s of Q8_0 weights; parity against the f64 sum 1e-4):

| kernel | GB/s |
|---|---|
| kdot-f32-r1 | 38 to 43 |
| kdot-f32-r8 (R 4) | 31 to 34 |
| kdot-x8 (R 4) | 31 to 34 |

Hand-written WGSL in `experiments/` (not the product route; they only ask
what a layout can reach on this host; parity 1e-5 to 5e-5):

| experiment | GB/s |
|---|---|
| `q8-block-per-thread.js` (one thread per 34-byte block, word loads) | 21 to 32 |
| `q8-coalesced-words.js` (lanes read consecutive words, workgroup 64 / 128 / 256) | 40 to 43 |

**Correction (same day, later).** The reading that "the layout does not decide
it" was wrong: it came from a harness artefact. In this Deno/wgpu harness
(100 dispatches in one compute pass) a dispatch of **one** workgroup already
costs 0.15 to 0.20 ms, so at 4096 rows (0.3 to 0.4 ms) a third to a half of
every number above is that floor, not memory traffic. The floor is the
harness's, not a Metal or Kotoba-native figure; an earlier receipt infers
about 31 us per dispatch in a native command buffer.

Same kernels at 32768 x 4096 (143 MB of Q8_0), where the floor is small, one
run each, so a trend and not a distribution:

| layout | ms | GB/s of Q8_0 payload |
|---|---|---|
| generated `kdot-f32-r1` | 2.111 | 68 |
| `experiments/q8-coalesced-words.js` | 1.458 | 98 |
| `experiments/q8-repacked-vec4.js` (scales in their own f32 array, int8 quants as aligned `vec4<u32>`, one thread per block, `x` as `vec4`) | 0.870 | 164 |

The repacked layout's size sweep shows it too (rows at 4096 columns: 1024 ->
22, 4096 -> 57, 16384 -> 128, 32768 -> 164 GB/s), with a marginal rate of about
227 GB/s between the last two. Parity is 1e-5 to 1e-4 against the f64 sum for
every row of these tables. The repack is a load-time transform of the GGUF
tensor (34-byte blocks into 4-byte scales and 32-byte aligned quants, so 36 B
a block); it is not in `tools/gpu_kernels_v2.kotoba` and no KIR v2 kernel
reads it yet.

What this changes for AWAI-6: two separate levers. (1) The dispatch floor,
which dominates the small matrices of a 0.5B model (hidden 896, FFN 4864: the
same repacked kernel gives 22 GB/s at 4864 x 896 and 72 GB/s at 4864 x 4864),
so fusing dispatches matters more than any single kernel. (2) A load-time
repack for the large matrices, worth about 2.4x on this host in the sweep
above. Neither is a decode rate; the end-to-end test is the 24-layer decode
guest of the 2026-10-19 receipt, which cannot run on main until the GPU route
(ADR 0375 B) exists.
