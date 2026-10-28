# Selfhost QR frame construction: active v2 profile, fragment

The new `bench/embench/fragments/qr-frame.kotoba` constructs the original
benchmark's base frame and triangular reservation mask. Native selfhost Amu
check/compile pass. All 1,269 byte comparisons across nine boundaries agree
with C. This complements the earlier byte-mode/Reed–Solomon fragment;
qrduino is still incomplete and no performance ratio follows. asher remains
unreachable. Three complete alternatives remain outstanding: qrduino,
picojpeg and wikisort. C-or-better remains the goal.

The actual upstream `initeccsize(1,22)` selects version 2, width 25, row width
4, and alignment delta 15. The C oracle checks that selection before observing
anything. The native fragment implements three finder borders/interiors,
white reservations, alignment construction and its active loop, the fixed
black module, timing gaps, format reservations, timing pattern, and reservation
of black modules over the lower triangle. The upstream version-information
function returns immediately for version 2; that phase is retained as an
unchanged boundary rather than inventing a version pattern. Arbitrary versions
and image widths are not claimed.

The 256-cell owned workspace holds 100 base-frame bytes and 41 reservation
bytes. Triangular indexing uses the same x/y ordering and bit positions as C.
Only those 141 defined bytes are compared at each boundary: no uninitialized
run-length buffer or padding is counted. The stages are allocation/zeroing,
finders, alignment, fixed black module, gaps, format reservations, timing,
version-information no-op, and final black-module reservation.

The oracle includes upstream `qrframe.c` unchanged and extracts the exact
`initframe` body with snapshots. `qrencode.c` and the BEEBS allocator are linked
as separate translation units so their bit macros preserve their meanings.
Snapshots agree with the unmodified `initframe` after 1/2/17/32 calls, each
with the original heap/size setup. AddressSanitizer and
UndefinedBehaviorSanitizer pass selfchecks 1 through 32 and all 2,304 initialized
snapshot reads. The native final phase passes fuel-1 trapping; workspace
index 255 succeeds and 256 traps. These are correctness diagnostics, not a
32-body whole-QR resource or timing qualification.

Compiler SHA-256 is
`abcc1318957af7d3a09cfd66c06d17821b5cf47f4c47d02b5620e9e92a24f02e`,
from the byte-identical three-generation native Amu build. Check, compile,
extraction and execution use no Node/nbb/JVM fallback. Python prepares the
observation adapter and Clang builds C outside the product path. All 97
PRODUCT inventory entries are unchanged. The generator enforces pinned
qrencode, qrframe and ECC-table hashes even under Python -O; regeneration is
byte-identical. This is new algorithm/fragment authoring, which existing
Kotoba AST refactor rules do not cover. Product sources are unchanged.

Evidence is under `docs/evidence/coscientist-qr-frame-20261004/`, including
source/native/C artifacts, provenance, every byte comparison, guards, original
API selfchecks, sanitizer/profile receipts and generation/pin checks. Unpack
the fresh fragment replay beside pinned `upstream`, `runner`, and `images/r6m`:

```sh
python3 audit-qr-frame.py coscientist-qr-frame-fragment
```

The harness requires native check acceptance, refuses replacement of a report,
and persists differential failures. Complete-workload, official-score and
formal performance qualification flags are false; timing rows are empty.
No historical simplified port, timing table or compiler optimization is
replaced/promoted by these results.

Next connect the two fragments to the original data-placement path, all eight
masks and penalties, best-mask selection and format bits. Verify full output,
repeated whole bodies and resources before counting QR as complete. Then
measure the selfhost path against unchanged C on asher and rank optimization
hypotheses from separated measurements. C-or-better remains unachieved.
