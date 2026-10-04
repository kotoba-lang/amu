# Picojpeg: native selfhost DC/AC coefficient fragment

This wave implements coefficient decoding for the original Embench JPEG in
Kotoba compiled by the native, selfhost-built Amu. It remains an untimed
fragment: IDCT, color conversion and reused full native decoder bodies are
not yet qualified. No C performance win or official Embench score is claimed.

The pinned 570-byte fixture is 51×64, three components, YH1V1, three blocks
per MCU and 56 MCUs. The implementation parses its headers and tables at
runtime, then decodes all 168 blocks using canonical Huffman codes, signed
extension, DC predictors, AC run/size, EOB/ZRL, zigzag and dequantization.
Explicit u8/u16/i16 narrowing preserves the original C state transitions.
The JPEG bytes and zigzag constants are inputs, not precomputed output.
The qualified domain is this original successful fixture: restart interval
and reduced mode are zero. Other JPEG formats/error paths are not qualified.

The C observation adapter captures each block immediately before the original
transformBlock, then still executes the original IDCT/color functions. Its
entropy state, terminal reader/predictor state and all three 256-byte RGB
buffers agree with unchanged benchmark_body at 1, 2, 17 and 32 iterations.
The original verifier also passes. These are C adapter checks; native RGB
output is not claimed. The native fragment deliberately stops at raw,
dequantized coefficients. Terminal comparisons exclude the IDCT-mutated
coefficient buffer.

All 14,740 native/C observations match:

- 168 blocks × 77 coefficient/predictor/reader/remaining/status fields: 12,936.
- Six block prefixes × 256 reader bytes: 1,536.
- 268 terminal reader/predictor/remaining/status fields: 268.

The remaining-MCU counter is observed before each block's transform and MCU
completion; terminal remaining is zero with PJPG_NO_MORE_BLOCKS. A private
current-block diagnostic is mapped explicitly, rather than treated as an
original global. Each native observation allocates one fresh 2,048-cell owned
workspace. This does not qualify reused native 32-body arena/fuel behavior.
Index 2,047 succeeds, index 2,048 traps, and fuel 1 traps without loosening
runtime bounds, fuel or ABI.

Independent ASan/UBSan checks pass for every original decoder iteration count
1..32 and all 14,740 initialized observation reads. An initial standalone
sanitizer check exposed null image-info RGB pointers in the C observation
adapter: preceding API checks had initialized them in the unsanitized run.
The corrected adapter explicitly initializes those pointers before invoking
the original verifier. The failed adapter/log are retained, and the complete
native differential was rerun against the corrected adapter. Native source
and coefficient outputs did not change.

The header component is AST-composed unchanged, with new coefficient
functions added. New algorithm authoring and the one-off C adapter pointer
fix have no applicable Amu mechanical refactor rule; no refactor verify
success is claimed. Source, C adapter and profile regenerate byte-identically.
All three altered picojpeg source pins fail closed under Python -O.

Native compiler SHA-256 is
`abcc1318957af7d3a09cfd66c06d17821b5cf47f4c47d02b5620e9e92a24f02e`,
the byte-identical three-generation selfhost compiler used for check, compile
and extraction. Python and Clang are bootstrap comparison tools under bench
and scripts. All 97 PRODUCT inventory entries are unchanged. This fragment
does not establish the full own-source check/refactor/compile plus exec-trace
100% selfhost gate.

Evidence is saved under
`docs/evidence/coscientist-picojpeg-coefficients-20261004/`, including native/C
artifacts, all observations, guards, sanitizers, failed draft, composition
inputs and fresh replay. Unpack the replay beside pinned upstream, runner
and images/r6m:

```sh
python3 audit-picojpeg-coefficients.py coscientist-picojpeg-coefficients-fragment
```

The harness requires native check acceptance, refuses report replacement and
persists failures. Complete-workload, performance, official-score and formal
qualification flags remain false; timing rows are empty. Next implement and
compare IDCT/YH1V1 RGB output for all 56 MCUs, qualify reused full bodies, then
measure unchanged C against native selfhost Kotoba on quiet asher. Historical
ratios and optimization ranking remain unchanged.
