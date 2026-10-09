# Selfhost QR codeword placement: active v2 profile, fragment

The new `bench/embench/fragments/qr-placement.kotoba` connects the checked
byte-mode/Reed–Solomon and frame fragments and implements the original QR
zigzag bit placement. Native selfhost Amu check/compile pass. All 7,144
observations match C, including four complete unmasked images and every
post-bit cursor position for the original input. This remains an incomplete
qrduino workload: eight masks, penalty scoring, best-mask selection and final
format bits are still required. Three full alternatives remain outstanding
(qrduino, picojpeg, wikisort). C-or-better performance remains unachieved;
asher is offline and no timing or official Embench score is added.

The original `initeccsize(1,22)` selects version 2/L, width 25, row stride 4,
34 data bytes and 10 parity bytes. Placement consumes all 352 codeword bits,
including the original advance/skip after the last bit. It preserves paired
columns, direction changes, the timing-column detour, triangular reservation
lookup and unsigned-byte cursor storage. The four inputs are the original
21-byte URL plus NUL, 32 ASCII A bytes, empty, and a 38-digit string clipped
by the original encoder to 32 bytes. This is a fixed profile, not a claim for
arbitrary versions or a general QR API.

The new bootstrap generator reads the two checked Kotoba components as forms
and composes them without changing their files. Contextual relocation moves
interleaved codewords and the image to offset 768, the base frame to 1536,
reservations to 1664, and four cursor values to 1760 in a 2,048-cell workspace.
The polynomial shares the original image scratch; the earlier diagnostic
polynomial copy is omitted. Both components retain their accepted hashes.
Initialization builds the frame before encoding and explicitly writes the
input's terminating NUL. The generator relocates only selected functions;
the bit weight 128 is not mistaken for an address. This is new algorithm and
AST composition authoring, a one-off outside existing native refactor rules.
No product source or dependency changes, nor refactor-verify success, follow.

The C observation adapter snapshots a copy of the pinned original `fillframe`
body at zero and after each bit. Each of four final images also agrees with
an independently invoked, unchanged `fillframe`. `qrencode.c` is included
unchanged, while `qrframe.c` is a separate translation unit to preserve the
original bit macros. An initial adapter build lacked the allocator header;
adding `beebsc.h` fixed that compile error before differential execution.
No native semantic mismatch was observed.

The 7,144 comparisons consist of 4,992 image/cursor values at 12 prefixes
(0, 1, 2, 7, 8, 17, 63, 64, 127, 255, 351, 352 bits) for four inputs,
1,412 cursor values at all 353 prefixes for the original input, and 740
final data/base/reservation bytes across four inputs. Cursor observations at
the selected prefixes overlap deliberately; these are diagnostic counts,
not independent workloads. Intermediate images are sampled at those 12
prefixes, not claimed exhaustively checked at every prefix. C ASan/UBSan
pass four unchanged-function selfchecks and 6,048 initialized accesses.
Native index 2047 succeeds, 2048 traps; fuel 1 traps the original final
placement. Fresh allocation per observation does not establish a 32-body
whole-QR resource bound.

Compiler SHA-256 is
`abcc1318957af7d3a09cfd66c06d17821b5cf47f4c47d02b5620e9e92a24f02e`.
It is the byte-identical three-generation native Amu build. Check, compile,
extraction and execution use this native path; Python and Clang prepare
bootstrap diagnostics outside the product path. All 97 PRODUCT entries are
unchanged. Regeneration is byte-identical and all three changed source pins
are refused under Python -O.

Evidence is under `docs/evidence/coscientist-qr-placement-20261004/`, including
source/native/C artifacts, provenance, every comparison, guards, sanitizers,
component/source hashes and replay inputs. Unpack the fresh fragment bundle
beside pinned `upstream`, `runner` and `images/r6m` and run:

```sh
python3 audit-qr-placement.py coscientist-qr-placement-fragment
```

The harness requires native check acceptance, refuses report replacement and
persists differential failures. Complete-workload, performance-measured,
official-score and formal-performance qualification flags remain false;
timing rows are empty. Historical simplified ports and timing tables are
unchanged. Next implement all mask penalties/selection and final format,
then qualify complete output and repeated whole bodies before measuring
selfhost versus unchanged C on quiet asher.
