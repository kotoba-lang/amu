# KIR v2 receipts: the BATCH, BPREFILL and BIAS variants (ADR 0372 step 3, JUN-356)

`tools/gpu_kernels_v2.kotoba` writes the preprocessor variants of three
kernels from kotoba-lang/inference, as generator parameters:
* `kir2-nex-variant op v`: `nex_ops.comp` (at 971376a) under `-DBATCH` (v 1),
  `-DBPREFILL` (2), `-DBIAS` (4) and `-DBATCH -DBIAS` (5). These are the 20
  op and define pairs whose module differs from decode:
  * copy_at, attn_decode and ctl in BATCH and BPREFILL;
  * pos_incr, argmax_partial, argmax_final and params in BATCH;
  * pos_add and pos_seed in BPREFILL;
  * rope_neox in BATCH, BIAS and BATCH BIAS;
  * sample_part, sample_probs, sample_bisect_part, sample_bisect_step and
    sample_final in BATCH.

  Any other pair gives an empty module; its GLSL is the decode one, so use
  v 0 for it.
* `kir2-deltanet-fused-variant v`: `deltanet_fused.comp` (at ee9ebc5) in
  BATCH and BPREFILL. In BATCH, the row is the sequence (`WorkGroupID.y`) at
  `pos[row]`. In BPREFILL, the stepbuf is `[position, row, sequence]`. The
  ring and the state of sequence `seq` sit at `seq 6 n` and `seq heads K V`.
* `kir2-embed-variant kind v`: `embed_iq4xs.comp` (at c7ea9a9) in BATCH and
  BPREFILL, for each of its seven kinds. The token is `ids[row pad1 +
  pos[row]]` in BATCH and `ids[pos[1] pad1 + pos[0] + row]` in BPREFILL.

`kir2-nex-op`, `kir2-deltanet-fused` and `kir2-embed` are the decode
variants, and all 63 decode modules are byte-identical to
`gpu-kernel-kir2-dn-20261023/`.

The refs phase compiles each variant with its defines. Two more things
changed:
* The unit kept about 165 builders of 2.2M words each and trapped out of
  memory. The builder's reserve is now 591632 words. The body section still
  holds many times the largest kernel, and a full section still traps.
* One provider session holds 127 pipelines, and no verb frees one, so the
  gpu phase runs the variants in a second session.

## Files

* `aarch64-linux.json`: `scripts/seed/check-gpu-kernel-spirv.py --suite kir2`,
  with the pinned root (`bd025475…`) on arm64 Linux. The refs and oracle
  phases ran on the developer host.
* `x86_64-linux.json`: the same with an x86_64 tool image, under qemu-user
  (`--seccomp-if-available`, recorded).
* `gad-radv.json`: the aarch64 receipt with the `gpu` phase added. It ran on
  gad (x86_64, Radeon 8060S Graphics, RADV GFX1151, Vulkan 1.4.318), confined
  in both sessions. The provider came from the device-features branch
  (#1534), so the suite's int8 kernel ran as well.
* `gad-radv-main-provider.json`: the same phase with this tree's own provider.
  Every case but int8 passes; int8 is recorded as skipped.
* The runs' temporary directories were removed.

## What the receipts show

* **The unit:** 134 Kotoba cases pass, and the control fails exactly once.
  The checker accepts glslang's module of every variant.
* **Oracles:** all 99 modules are valid under `spirv-val --target-env
  vulkan1.1`, and the two tool images write the same bytes.
* **GPU** (156 rows, 35 of them the variants). Every buffer each variant
  writes is byte-identical to glslang's module of the same defines, and
  every case must write something. The inputs are chosen so that a port
  mixing up two strides or two indices would give other bytes:
  * **copy_at.** BATCH with `aux2 != n`. BPREFILL into sequence 1's slice
    at base 5.
  * **rope_neox.**
    * BATCH: two heads a token, at positions 7 and 12.
    * BIAS: at the dynamic position.
    * BATCH BIAS: NORMAL pairs, rope_freqs and a tail.

    Within 8.9e-7 of f64.
  * **attn_decode.** 4 heads on 2 kv heads.
    * BATCH: two sequences at positions 5 and 9, each over its own slice,
      with the interleaved gate.
    * BPREFILL: two query rows of sequence 1 from base 4, with the plain
      gate.

    Within 5e-8 of f64.
  * **argmax.**
    * argmax_partial BATCH: two rows of 5000, with a tie across one row's
      partials and a tie inside the other's.
    * argmax_final BATCH: two rows with p1 == 0, and one row with p1 != 0,
      whose token-buffer write the BATCH GLSL keeps.

    All exact.
  * **The resident ops.** All exact:
    * ctl BATCH, with one row rewound;
    * ctl BPREFILL into sequence 2, whose base is `ids[2]`, not `ids[1]`,
      with and without the flag;
    * pos_incr BATCH, pos_add and pos_seed BPREFILL, and params BATCH.
  * **The BATCH sampler chain.** Three rows of 5000, with different T, top_p,
    seed and position, over 63 dispatches. Row 1 has T = 0, so every kernel
    skips it and its slots keep their bytes. Rows 0 and 2 pick 1098 and
    4183. The params buffer is never written.
  * **deltanet_fused.** The ring, the state and the output are compared.
    * BATCH: three sequences at positions 0, 5 and 6.
    * BPREFILL: row 1 of sequence 2 at position 7, and row 0 of sequence 1
      at 0.
  * **embed**, all seven kinds:
    * BATCH: rows at positions 2 and 1 of a two-sequence token buffer;
    * BPREFILL: two positions of sequence 1 from base 0, where base and
      sequence swapped would give other tokens.

    Q8 is exact against a dequant.

**Review.** Codex was at its usage limit, so an independent agent reviewed
the diff. It found no fidelity bug, and checked every variant line by line
against the GLSL, including which loads are guarded. Its findings are
fixed:
* five cases had inputs a wrong port would also pass:
  * copy_at's two strides were equal;
  * attn_decode had one kv head;
  * embed BPREFILL's base equalled its sequence;
  * ctl BPREFILL used sequence 1;
  * argmax_final BATCH's token-buffer write never ran;
* sample_bisect_step's top_p load sat outside `t == 0`;
* the f64 check could miss a NaN.
