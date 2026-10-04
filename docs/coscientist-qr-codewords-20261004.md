# Selfhost QR codewords: checked fragment, complete workload still open

The historical QR port computes parity for an unrelated 17-byte prefix and
omits framing/masking. The new `bench/embench/fragments/qr-codewords.kotoba`
implements the actual benchmark's byte-mode codeword pipeline. It is a
fragment, not a complete QR benchmark replacement or performance result.
Three workloads still need complete alternatives: qrduino, picojpeg and
wikisort. C-or-better remains unachieved; asher is unreachable.

For the original `initeccsize(1,22)` call, upstream selects version 2, level L,
width 25, row width 4, one block of 34 data bytes and 10 ECC bytes. The oracle
access/profile check verifies that actual size-selection call. The payload
is the original 21-byte `http://www.mageec.com` plus its terminator. Native
code implements byte-mode shifting, length/mode fields, the original paired
0xec/0x11 padding writes (including the extra write later cleared by ECC),
generator polynomial construction, log conversion, Reed–Solomon feedback,
the zero-feedback memmove path, and this profile's single-block interleave/
copy-back. It preserves byte truncation after stores and upstream `modnn`.
GF log/exp tables are extracted from pinned upstream, not replaced by a
separate parity formula or a precomputed answer.

Native selfhost Amu check/compile accept the fragment. Compiler SHA-256 is
`abcc1318957af7d3a09cfd66c06d17821b5cf47f4c47d02b5620e9e92a24f02e`,
from the byte-identical three-generation Amu build. Checking, compilation,
extraction and raw execution use no Node/nbb/JVM fallback. Python generates
benchmark source and snapshots; Clang builds the C oracle outside the product
path. All 97 PRODUCT inventory entries remain unchanged.

Correctness evidence compares four initialized profiles: original payload,
32 bytes at the capacity boundary, empty input, and a 38-byte payload clipped
to 32 bytes. Each has five stages (raw input, padding, polynomial, ECC,
interleave/copy-back). All 20,480 workspace values agree with C, including
initialized padding/inactive slots; these counts are not operation counts
or timing evidence. Each final data buffer and all 44 interleaved codewords
also agree with unchanged `stringtoqr`. All 512 log/exp table values match.
Index 1023 succeeds, index 1024 traps, and fuel 1 traps.

The C observation adapter includes `qrencode.c` unchanged and copies the
exact `stringtoqr` body with four snapshots. Other QR source and BEEBS
allocator files are linked separately, preserving their macro contexts.
Buffers are initialized explicitly for this diagnostic; it does not prove
arbitrary reused heap contents or repeated full QR bodies. The captured
11 polynomial logs are retained as an observation after the original QR
scratch buffer is overwritten by interleaving. This is not extra production
work or a different C timing body. AddressSanitizer/UndefinedBehaviorSanitizer
pass the original profile choice, four unchanged-function selfchecks and
20,480 observation reads. Regeneration is byte-identical; modified qrencode,
qrframe, qrtest and ECC table files are refused even under Python -O.

The generator and source are new fragment/algorithm authoring, not a
mechanical product refactor covered by existing AST rules. The scoped source
name, namespace, report and directory all mark the fragment boundary.
No product source is edited and no historical comparison is replaced.

The research archive in `docs/evidence/coscientist-qr-codewords-20261004/`
contains source/native/C artifacts, provenance, every comparison, guards,
profile/access checks, regeneration and source-pin receipts. A fresh replay
bundle can be unpacked beside pinned `upstream`, `runner`, and `images/r6m`:

```sh
python3 audit-qr-codewords.py coscientist-qr-codewords-fragment
```

This is an untimed fragment replay. It refuses replacement of reports and
records differential failures. Performance rows are empty, full-workload
and official-score flags are false, and there is no optimization promotion.

Next implement frame base/reservation bits and alignment, data placement,
all eight masks and their penalty calculations, best-mask selection and
final format bits. Then check full output and repeated bodies against C,
measure the complete selfhost workload on asher, and rank improvements from
separated measurements. These remaining steps are required before QR can
count as a complete alternative or support the C-or-better goal.
