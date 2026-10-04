# Selfhost picojpeg input and bit-reader fragment

`bench/embench/fragments/picojpeg-reader.kotoba` implements the original
fixture's callback refill, getChar/stuffChar, FF-aware getOctet, getBits1/2,
getBit, initial bit priming and fixInBuffer. Native selfhost check/compile
pass. All 9,504 buffer/state/return comparisons match unchanged C primitives.
Native bounds/fuel and original C ASan/UBSan pass. This is a fragment:
marker parsing, quantization/Huffman tables, coefficient decoding, IDCT and
color output remain open. Picojpeg is still the one incomplete alternative;
C-or-better remains unachieved and no performance or official score follows.
asher remains offline.

Pinned upstream `09c2ed8c3b7008c95d08b038de4a3f6dc103ed70` supplies all 570
original JPEG bytes. The generator creates a literal balanced lookup of
those input bytes, not decoded pixels or precomputed native results. C's
original decoder reports width 51, height 64, three components, scan 1
(YH1V1), 8×8 MCU, three blocks/MCU and 56 MCUs. It decodes all 56, returns
PJPG_NO_MORE_BLOCKS=1 and passes the original RGB verifier. This establishes
the next implementation's actual profile; none of those full-decoder
behaviors is yet attributed to the native fragment.

The native owned 512-cell workspace holds 256 input bytes plus eight fields:
input offset/count, EOF toggle, 16-bit reservoir, remaining bits, callback
fixture offset, callback status, and diagnostic return. Buffer refill reserves
four prefix bytes and requests 252 fixture bytes, capped at remaining input.
Unsigned 8/16-bit stores reproduce C truncation. Exhausted input alternates
synthetic FF/EOI without advancing the fixture offset. FF-aware reads retain
nonzero marker followers through two-byte pushback; bit reads preserve the
original return-before-refill behavior. The fixed callback succeeds, as the
original fixture does; arbitrary callbacks/errors are not an API claim.

Four scripted modes exercise raw characters, widths 1–16 without/with FF
checking, and mixed getBits/getBit/getChar/getOctet/fixInBuffer. Eight operation
prefixes per mode (0,1,2,7,16,252,253,1024) and four extra raw prefixes around
the actual 570-byte endpoint yield 36 × 264 = 9,504 comparisons. Every buffer
byte, state field and last return agrees. fixInBuffer's void return has an
explicit diagnostic sentinel -1 in both adapters. These are controlled
primitive sequences, not a recorded real-decoder trace, nor whole native
JPEG execution. C's fresh diagnostic buffer is explicitly zeroed, matching
native allocation; reused full-decoder buffers remain a future qualification.

The C oracle directly invokes the original functions, includes the original
callback and JPEG fixture unchanged, and independently runs unchanged
benchmark_body/verify after 1/2/17/32 complete C bodies. ASan/UBSan also pass
all repeat counts 1 through 32 and all 9,504 initialized reader accesses.
Native workspace index 511 succeeds and 512 traps; fuel 1 traps the 1024-read
prefix. These checks do not establish a 32-body native decoder resource bound.

Compiler SHA-256 is
`abcc1318957af7d3a09cfd66c06d17821b5cf47f4c47d02b5620e9e92a24f02e`,
the three-generation byte-identical native Amu build. Check, compile, extraction
and runtime use this compiler/runner. Python/Clang prepare bootstrap tools
outside the product; all 97 PRODUCT entries are unchanged. This is one-off
new algorithm/observation authoring outside native refactor rules, without
editing the historical simplified kernel or claiming refactor-verify/100%
own-source selfhost. Three altered source pins are refused under Python -O;
source/adapter/profile regeneration is byte-identical.

Evidence is under `docs/evidence/coscientist-picojpeg-reader-20261004/` with
source/native/C artifacts, exact comparisons, provenance, guards, sanitizer
receipt, original decoder-profile probe, pins and fresh replay. Unpack replay
beside pinned `upstream`, `runner` and `images/r6m`:

```sh
python3 audit-picojpeg-reader.py coscientist-picojpeg-reader-fragment
```

The harness requires native check acceptance, refuses report replacement and
persists failures. Complete-workload, performance, official-score and formal
qualification flags stay false; timing rows are empty. Next implement marker
and table parsing against this reader, then all 56 MCUs, exact RGB output,
reused whole-body resources and the original verifier before paired C timing
on quiet asher. Historical timing ratios and ranking are unchanged.
