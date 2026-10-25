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

## The gates (`gad-radv.json`, `b70-anv.json`)

Two hosts ran:
* gad: x86_64, Radeon 8060S Graphics, RADV GFX1151. It ran with
  `--max-workgroups 4294967295`, so `output_wide` ran too.
* the B70: x86_64, Intel BMG G31, ANV. It ran with Vulkan's guaranteed 65535,
  which is ANV's limit, so `output_wide` (one workgroup per row, 248320 of
  them) is recorded as skipped.

Every guest's provider was confined (Landlock ABI 8 and the seal).

* **Identical to glslang:** every layout of every guest, and both argmax
  chains. Before each layout the guest fills both output buffers with NaN,
  and every output must be finite, so a row a module leaves unwritten fails.
* **Against f64:**
  * The f32 layouts (r1, r8, x8r4, dot) use kdot_check's metric, max |got -
    ref| / max(|ref|, 1e-2), which must be at most 1e-3. The worst is
    5.4e-05 on gad and 5.4e-05 on the B70.
  * The h2 layouts compute their products in f16, where that metric's 1e-2
    floor magnifies near-zero rows. Their gate is max |got - ref| /
    rms(ref), which must be at most 1e-2. The worst is
    5.3e-03, a margin of about 2x.
* **The argmax chain.** It ran on x8r4's logits (`output`, both hosts) and on
  r1's (`output_wide`, gad). Both modules' chains agree in all 61 partials,
  and every dispatch's answer is checked. Each partial is its segment's
  maximum of the logits, at the lowest index. The pick is the lowest index
  of the overall maximum, 66749, which is the f64 argmax.
* **Speed.** Each module ran one warm-up dispatch, then seven rounds of a
  10-dispatch command buffer, KIR v2 and glslang alternating. The gate
  compares the medians, KIR v2's within 1.25 times glslang's.
  * The gate applies where glslang's median buffer takes at least 0.5 ms.
    Shorter buffers are launch-bound, so their ratio is noise; they are
    recorded but not gated.
  * Gated ratios: 0.93-1.03 on gad and 0.95-1.07 on the B70.
    Ungated: 0.96-1.05 and 0.95-1.01.
  * On ANV this gate found a real gap. KIR v2's x8r4 took 1.37 times
    glslang's time, because its SIMD32 build failed register allocation.
    That is fixed in `kd-q4-scale` and `kd-q4-min`; see
    `gpu-kernel-kir2-h2-20261024/`.

### gad

| guest | layout | kdot_check rel | err / rms | KIR v2 us | glslang us | ratio | gated |
|---|---|---|---|---|---|---|---|
| attn_qkv | r1 | 2.2e-05 | 3.5e-06 | 695.2 | 695.6 | 1.00 | yes |
| attn_qkv | r8 | 2.2e-05 | 3.5e-06 | 694.6 | 699.8 | 0.99 | yes |
| attn_qkv | x8r4 | 5.4e-05 | 1.9e-06 | 564.7 | 568.3 | 0.99 | yes |
| attn_qkv | h2r1 | 6.7e-02 | 5.3e-03 | 562.5 | 561.5 | 1.00 | yes |
| attn_gate | r1 | 8.2e-06 | 6.3e-07 | 356.6 | 370.2 | 0.96 | no |
| attn_gate | r8 | 8.2e-06 | 6.3e-07 | 412.7 | 393.4 | 1.05 | no |
| attn_gate | x8r4 | 1.1e-05 | 4.8e-07 | 362.0 | 369.5 | 0.98 | no |
| attn_gate | h2r1 | 3.3e-02 | 1.6e-03 | 318.9 | 325.6 | 0.98 | no |
| ffn_gate_exp0 | r1 | 3.5e-06 | 4.1e-07 | 110.8 | 107.7 | 1.03 | no |
| ffn_gate_exp0 | r8 | 3.5e-06 | 4.1e-07 | 278.1 | 279.3 | 1.00 | no |
| ffn_gate_exp0 | x8r4 | 3.2e-06 | 7.0e-07 | 201.9 | 191.8 | 1.05 | no |
| ffn_gate_exp0 | h2r1 | 9.5e-03 | 1.4e-03 | 126.8 | 124.3 | 1.02 | no |
| attn_gate_q4k | r1 | 2.0e-05 | 1.0e-06 | 401.8 | 396.9 | 1.01 | no |
| attn_gate_q4k | r8 | 2.0e-05 | 1.0e-06 | 752.3 | 736.2 | 1.02 | yes |
| attn_gate_q4k | x8r4 | 2.1e-05 | 1.2e-06 | 303.8 | 307.5 | 0.99 | no |
| attn_gate_q4k | h2r1 | 4.8e-02 | 2.8e-03 | 326.5 | 323.3 | 1.01 | no |
| output | x8r4 | 2.3e-05 | 5.5e-07 | 22232.0 | 23801.2 | 0.93 | yes |
| output | r8 | 1.6e-05 | 5.8e-07 | 25854.6 | 26595.0 | 0.97 | yes |
| output_wide | r1 | 1.6e-05 | 5.8e-07 | 24309.2 | 23757.1 | 1.02 | yes |
| output_wide | h2q6r1 | 5.5e-02 | 1.5e-03 | 25196.0 | 24561.9 | 1.03 | yes |
| ffn_gate_inp | dot | 7.6e-06 | 3.4e-07 | 98.1 | 94.6 | 1.04 | no |

### The B70

| guest | layout | kdot_check rel | err / rms | KIR v2 us | glslang us | ratio | gated |
|---|---|---|---|---|---|---|---|
| attn_qkv | r1 | 2.2e-05 | 3.5e-06 | 1211.6 | 1265.7 | 0.96 | yes |
| attn_qkv | r8 | 2.2e-05 | 3.5e-06 | 772.6 | 762.9 | 1.01 | yes |
| attn_qkv | x8r4 | 5.4e-05 | 1.9e-06 | 898.2 | 941.0 | 0.95 | yes |
| attn_qkv | h2r1 | 6.7e-02 | 5.3e-03 | 1764.1 | 1743.8 | 1.01 | yes |
| attn_gate | r1 | 8.2e-06 | 6.3e-07 | 2606.1 | 2557.6 | 1.02 | yes |
| attn_gate | r8 | 8.2e-06 | 6.3e-07 | 747.2 | 761.1 | 0.98 | yes |
| attn_gate | x8r4 | 1.1e-05 | 4.8e-07 | 696.5 | 727.0 | 0.96 | yes |
| attn_gate | h2r1 | 3.3e-02 | 1.6e-03 | 1089.9 | 1115.3 | 0.98 | yes |
| ffn_gate_exp0 | r1 | 3.5e-06 | 4.1e-07 | 246.0 | 244.4 | 1.01 | no |
| ffn_gate_exp0 | r8 | 3.5e-06 | 4.1e-07 | 999.4 | 934.6 | 1.07 | yes |
| ffn_gate_exp0 | x8r4 | 3.2e-06 | 7.0e-07 | 366.1 | 386.9 | 0.95 | no |
| ffn_gate_exp0 | h2r1 | 9.5e-03 | 1.4e-03 | 393.8 | 394.4 | 1.00 | no |
| attn_gate_q4k | r1 | 2.0e-05 | 1.0e-06 | 2846.0 | 2779.3 | 1.02 | yes |
| attn_gate_q4k | r8 | 2.0e-05 | 1.0e-06 | 758.6 | 752.0 | 1.01 | yes |
| attn_gate_q4k | x8r4 | 2.1e-05 | 1.2e-06 | 614.4 | 643.1 | 0.95 | yes |
| attn_gate_q4k | h2r1 | 4.8e-02 | 2.8e-03 | 1265.8 | 1258.2 | 1.01 | yes |
| output | x8r4 | 2.3e-05 | 5.5e-07 | 18859.0 | 18745.6 | 1.01 | yes |
| output | r8 | 1.6e-05 | 5.8e-07 | 29145.0 | 30822.9 | 0.95 | yes |
| ffn_gate_inp | dot | 7.6e-06 | 3.4e-07 | 617.3 | 604.0 | 1.02 | yes |

The times are each module's median 10-dispatch command buffer.

## Files

* `fixtures.json`, `ref.json`: the fixtures and the oracle's summary (the f64
  vectors themselves are in the run's workspace, pinned by SHA-256 here).
* `exec-build.json`: the guests (source and image digests), the kernels, and
  the launcher and provider images.
* `gad-radv.json`, `b70-anv.json`: the runs, with each guest's launcher
  receipt.

The fixtures, the guests' stdout (the outputs as hex) and the f64 vectors
stayed in the run's workspace. gad's temporary directory was removed.

**Not covered here:** the whole decode guest (every layer, through tokens),
and Xavier (the provider is x86_64-only).
