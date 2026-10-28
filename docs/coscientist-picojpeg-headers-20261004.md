# Selfhost picojpeg header and table fragment

`bench/embench/fragments/picojpeg-headers.kotoba` connects the accepted reader
to SOI/marker scanning, variable-marker skips, DQT/Winograd quantization,
DHT canonical tables, SOF components, MCU geometry, SOS selectors and scan
validation/bit fixup. Native selfhost Amu check/compile pass. All 4,712 reader,
table and header observations match unchanged C. Original full-init API and
C decoder/verifier selfchecks, ASan/UBSan and native bounds/fuel pass. This
is still a fragment: MCU coefficient decoding, IDCT and color output remain.
Picojpeg stays the last incomplete alternative. C-or-better remains unachieved;
asher is offline and no timing or official score is added.

Upstream is `09c2ed8c3b7008c95d08b038de4a3f6dc103ed70`. The runtime parses
all markers/tables from the original 570-byte JPEG through the native reader,
not from captured header snapshots. Literal Winograd scale factors are the
original library's table. DQT values are read in zigzag order and scaled at
runtime, preserving signed 16-bit conversion and arithmetic-right-shift
rounding. DHT constructs 16 min/max-code and value-pointer entries per table,
including the original 0/65535/0 empty-code sentinel, uint16 code shifts and
uint8 cumulative value offsets. Table-validity masks and scan selectors
retain their original roles. Marker processing preserves the upstream
behavior of discarding DQT/DHT/DRI/skip helper return codes inside its loop;
no parser semantics are silently repaired to match a test.

The original input initializes width 51, height 64, three components, both
quantization tables, all four Huffman tables, YH1V1, 8×8 MCU with three blocks,
7 MCU columns and 8 MCU rows (56 remaining MCUs). Native and C agree on
component identities/sampling/quantization choices, scan component order,
DC/AC table selection, spectral/successive fields, restart state, last-DC
zeros and the entropy bit reservoir after fixInBuffer. Sampling/error branches
are authored, but only the original fixture's actual YH1V1 path is qualified;
no arbitrary-JPEG/invalid-stream or alternate-sampling API is claimed.

Composition parses the reader's checked forms, keeps their addresses, renames
its initializer in the new namespace and adds the new table/header functions.
The existing reader file is unchanged and content-hashed. The 2,048-cell
owned workspace holds reader bytes/state, 128 quant values, 192 canonical
Huffman fields, 544 symbol slots, count scratch and header/component/geometry
fields. One-off new C-to-Kotoba algorithm/observation and AST composition
are outside existing native refactor rules; no product refactoring or
refactor-verify success is claimed.

Four boundaries are reader init, locateSOF/readSOF, initFrame and initScan.
Each has 1,178 defined values: 263 reader values, 128 quant fields, 736 Huffman
fields/symbol slots, 16 scalar header fields, 21 component fields, six MCU
organization bytes, four spectral fields, three last-DC values and status.
The private marker/count scratch and reader's diagnostic last-return slot
are excluded from the oracle rather than inventing upstream global fields.
Fresh buffers/tables are zeroed in both observation paths to match initial
BSS/native allocation. This does not qualify reused full native decoder state.

The C adapter calls original functions directly. Its final staged state agrees
with unchanged `pjpeg_decode_init` after 1/2/17/32 invocations, comparing all
1,178 globals and selected numeric image-info fields. Independently,
unchanged C benchmark_body/verify runs 1/2/17/32 complete decodes and validates
original RGB output. ASan/UBSan pass all counts 1 through 32 for both selfchecks
and all 4,712 initialized header reads. These C repeats are not evidence of
32 native JPEG bodies. Native index 2047 succeeds, 2048 traps, and fuel 1
traps final header preparation; guards/ABI are unchanged.

Compiler SHA-256 is
`abcc1318957af7d3a09cfd66c06d17821b5cf47f4c47d02b5620e9e92a24f02e`,
from the three-generation byte-identical native Amu build. Native check,
compile, extraction and runtime use that path. Python/Clang are bootstrap
comparison tools outside the product. All 97 PRODUCT inventory entries are
unchanged; 100% own-source selfhost/exec-tracer qualification is not claimed.
Source/adapter/profile regenerate byte-identically; three altered original
source pins are refused under Python -O and the reader hash remains unchanged.

Evidence is under `docs/evidence/coscientist-picojpeg-headers-20261004/`:
source/native/C artifacts, provenance, all comparisons, original API/decoder
selfchecks, sanitizer receipts, guards, composition inputs and a fresh replay.
Unpack replay beside pinned `upstream`, `runner` and `images/r6m`:

```sh
python3 audit-picojpeg-headers.py coscientist-picojpeg-headers-fragment
```

The harness requires native check acceptance, refuses report replacement
and persists failures. Complete-workload, performance, official-score and
formal-qualification flags remain false; timing rows are empty. Next decode
DC/AC coefficients from these tables for all 56 MCUs, compare IDCT/color
output and the original verifier, qualify reused native bodies/resources,
then measure against unchanged C on quiet asher. Historical timings and
optimization ranking are unchanged.
