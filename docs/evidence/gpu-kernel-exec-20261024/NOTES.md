# KIR v2 kernels on real tensors through the provider (ADR 0372 step 4, ADR 0371 step 6; JUN-356)

`scripts/seed/check-gpu-kernel-exec.py` runs the KIR v2 kernels on real model
tensors along the product route:
1. a static guest (wire 42), compiled by the pinned root (`bd025475…`);
2. the static launcher;
3. the Vulkan provider, confined.

Each guest maps its fixture and runs, for every layout, both KIR v2's module
and glslang's module of the hand-written kernel on the same tensor:
* one dispatch of each to warm up;
* then five rounds of a 10-dispatch command buffer, KIR v2 then glslang, so
  neither takes the GPU's clock ramp alone;
* then it reads both outputs back.

The outputs are checked three ways: byte for byte, against an f64 dequant
oracle, and for speed. For the lm_head, the guest also runs the decode argmax
chain (argmax_partial over 61 workgroups, then argmax_final), once with KIR
v2's modules and once with glslang's.

The kernels are part 7's suite build (`gpu-kernel-kir2-h2-20261024/`), and the
provider is the device-features one (#1534), which the h2 layouts need for
`shaderFloat16`.

## The fixtures (`fixtures.json`)

| fixture | type | rows x cols | source |
|---|---|---|---|
| attn_qkv | Q5_K | 8192 x 2048 | `/root/kdot/attn_qkv.q5k.bin` on gad |
| attn_gate | IQ4_XS | 4096 x 2048 | `/root/kdot/attn_gate.iq4xs.bin` |
| ffn_gate_exp0 | IQ4_XS | 512 x 2048 | expert 0 of `/root/kdot/ffn_gate_exps.iq4xs.bin` |
| output | Q6_K | 248320 x 2048 | `output.weight` of Qwen3.6-35B-A3B-Q4_K_M.gguf |
| attn_gate_q4k | Q4_K | 4096 x 2048 | `blk.0.attn_gate.weight` of the same GGUF |
| ffn_gate_inp | F32 | 256 x 2048 | `blk.0.ffn_gate_inp.weight` (the MoE router): the dot fixture |

kotoba-lang/inference's `kdot_check.py` names the first four by their byte
counts, and all four match. `x` is 2048 values in [-1, 1) from a fixed LCG,
exact in f32. Each fixture's SHA-256 is recorded, along with its source and
offset (and, for the GGUF, its size and its header's SHA-256).

## The oracle (`ref.json`)

The `ref` phase runs on the developer host, in pure Python. It applies ggml's
dequant (as kotoba-lang/inference `kdot_ref.py` does) times x, summed in f64,
for every row of every fixture: 12 s for the 248320-row lm_head.

For the lm_head, the f64 argmax is token 66749. Its logit 2.2252 leads the
runner-up by 0.181.

## The gates (`gpu-kernel-exec.json`, gad)

The run was on gad (x86_64, Radeon 8060S Graphics, RADV GFX1151), and every
guest's provider was confined (Landlock ABI 8 and the seal).

* **Identical to glslang:** every layout of every fixture, and both argmax
  chains.
* **Against f64:**
  * The f32 layouts (r1, r8, x8r4, dot) use kdot_check's metric, max |got -
    ref| / max(|ref|, 1e-2), which must be at most 1e-3. The worst is 5.4e-5.
  * The h2 layouts compute their products in f16, where that metric's 1e-2
    floor magnifies near-zero rows (up to 6.7e-2). Their gate is max |got -
    ref| / rms(ref), which must be at most 1e-2. The worst is 5.3e-3.
* **The argmax chain:** its pick is 66749, the f64 argmax.
* **Speed:** KIR v2's best 10-dispatch command buffer took 0.61-1.19 times
  glslang's (gate 1.25).
  * This gate is coarse. On gad's iGPU the same layout's best-of-five moves
    by up to about ±40% between runs.
  * Both modules compute the same bytes, so a gap would come from the
    driver's code generation, and no layout shows one beyond that noise.

| fixture | layout | kdot_check rel | err / rms | KIR v2 us | glslang us | ratio | GB/s |
|---|---|---|---|---|---|---|---|
| attn_qkv | r1 | 2.2e-05 | 3.5e-06 | 571.0 | 864.6 | 0.66 | 202.0 |
| attn_qkv | r8 | 2.2e-05 | 3.5e-06 | 553.9 | 911.0 | 0.61 | 208.2 |
| attn_qkv | x8r4 | 5.4e-05 | 1.9e-06 | 945.6 | 797.9 | 1.19 | 122.0 |
| attn_qkv | h2r1 | 6.7e-02 | 5.3e-03 | 552.0 | 533.5 | 1.03 | 209.0 |
| attn_gate | r1 | 8.2e-06 | 6.3e-07 | 313.3 | 331.6 | 0.94 | 142.2 |
| attn_gate | r8 | 8.2e-06 | 6.3e-07 | 367.7 | 364.4 | 1.01 | 121.2 |
| attn_gate | x8r4 | 1.1e-05 | 4.8e-07 | 380.0 | 380.2 | 1.00 | 117.3 |
| attn_gate | h2r1 | 3.3e-02 | 1.6e-03 | 385.4 | 388.3 | 0.99 | 115.6 |
| ffn_gate_exp0 | r1 | 3.5e-06 | 4.1e-07 | 150.0 | 151.3 | 0.99 | 37.1 |
| ffn_gate_exp0 | r8 | 3.5e-06 | 4.1e-07 | 299.3 | 287.3 | 1.04 | 18.6 |
| ffn_gate_exp0 | x8r4 | 3.2e-06 | 7.0e-07 | 110.0 | 132.9 | 0.83 | 50.7 |
| ffn_gate_exp0 | h2r1 | 9.5e-03 | 1.4e-03 | 126.0 | 111.3 | 1.13 | 44.2 |
| output | r1 | 1.6e-05 | 5.8e-07 | 24082.4 | 23694.4 | 1.02 | 173.2 |
| output | x8r4 | 2.3e-05 | 5.5e-07 | 21403.7 | 23698.1 | 0.90 | 194.9 |
| output | h2q6r1 | 5.5e-02 | 1.5e-03 | 24430.7 | 24302.4 | 1.00 | 170.8 |
| attn_gate_q4k | r1 | 2.0e-05 | 1.0e-06 | 273.9 | 346.7 | 0.79 | 172.3 |
| attn_gate_q4k | r8 | 2.0e-05 | 1.0e-06 | 364.3 | 485.8 | 0.75 | 129.5 |
| attn_gate_q4k | x8r4 | 2.1e-05 | 1.2e-06 | 312.2 | 309.3 | 1.01 | 151.2 |
| attn_gate_q4k | h2r1 | 4.8e-02 | 2.8e-03 | 294.3 | 368.2 | 0.80 | 160.3 |
| ffn_gate_inp | dot | 7.6e-06 | 3.4e-07 | 94.0 | 95.4 | 0.98 | 223.2 |

The times are each module's best of five 10-dispatch command buffers; GB/s is
ten passes over the tensor in KIR v2's best time.

## Files

* `fixtures.json`, `ref.json`: the fixtures and the oracle's summary (the f64
  vectors themselves are in the run's workspace, pinned by SHA-256 here).
* `exec-build.json`: the guests (source and image digests), the kernels, and
  the launcher and provider images.
* `gpu-kernel-exec.json`: the run, with each guest's launcher receipt.

The fixtures, the guests' stdout (the outputs as hex) and the f64 vectors
stayed in the run's workspace. gad's temporary directory was removed.

**Not covered here:** the whole decode guest (every layer, through tokens),
Xavier (the provider is x86_64-only) and ANV.
