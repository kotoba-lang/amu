# Selfhost CRC32: matched original body and repetition

CRC32 now has a complete matched-batch alternative compiled by native selfhost
Amu. Both table representations pass 2,306 native/C observations and original
body/verifier checks through 32 iterations. This is correctness/resource
qualification, not measured improvement. asher is offline; C-or-better is
unachieved and no new ratio or official Embench score is published.

Each body reseeds the exact beebsc RNG to zero, consumes all 1,024 original
pseudo-random bytes, performs the original 256-entry CRC-table updates and
complements the result. All bodies run; verification of the last result occurs
once after the batch in both arms. The C adapter calls unchanged
benchmark_body(1,n) then verify_benchmark. LOCAL_SCALE_FACTOR=170 is normalized
to one body for the paired adapter; n is the disclosed body count. Neither arm
uses a stored CRC result to bypass the computation. 0/1/2/17/32 batches return
0/1/1/1/1 in both arms.

The canonical `batch-ports/crc32.kotoba` retains the historical chunked table
representation: sixteen 16-item immutable literal vectors. The separate scalar
candidate expresses the same 256 input constants as a balanced branch tree.
Every table entry is independently compared. Both representations execute
all CRC steps and pass 32 bodies within the unchanged arena/fuel budget.
The chunked canonical path uses 65,602 fuel for 32 bodies; the scalar candidate
uses 32,834. Fewer fuel charges do not prove lower execution time: branches,
vector-handle access and machine-code layout must be measured. Scalar is not
promoted as a performance optimization, and the default generator remains
chunked. Historical `ports/crc32.kotoba` and its timings are unchanged.

The untimed C prefix oracle copies original crc32pseudo with only its loop
bound made stoppable. Its full 1,024-byte result and final RNG state match the
unchanged original body for every checked 1/2/17/32 iteration count. Native
observations compare all 256 input table values, all 1,025 prefix CRC values
and all 1,025 prefix RNG states: 2,306 values per representation, 4,612 total.
The original C typedef DWORD is unsigned long, 64 bits on this host; diagnostic
complements are explicitly normalized to low 32 bits. The original body's
modulo-32,768 result/verifier remains unchanged. This normalization is not a
change to the C algorithm or its timed body.

Independent ASan/UBSan passes all original C body/verifier/RNG checks 1..32
and all 2,306 initialized prefix/table observations. Native fuel 1 traps in
both representations. Existing bounds, handle checks, ABI, arena maximum
65,536 and fuel maximum 16,777,216 remain unchanged. Diagnostic domains are
prefixes 0..1,024 and table entries 0..255; arbitrary diagnostic arguments
and generalized CRC input APIs are not qualified.

The generators extract and pin original table/RNG/support inputs and author
new complete-body/batch/diagnostic wrappers. No Amu mechanical refactor rule
covers this new algorithm/profile authoring. No historical or product source
was mechanically rewritten, and no refactor verify pass is claimed. Both
source/adapter/profile variants regenerate byte-identically; altered CRC,
RNG and support-header pins refuse even under Python -O. All 97 PRODUCT
inventory entries remain unchanged; Python/Clang are bootstrap/oracle tools.

Compiler SHA-256:
`abcc1318957af7d3a09cfd66c06d17821b5cf47f4c47d02b5620e9e92a24f02e`,
the recorded byte-identical three-generation selfhost build. It performs
check, compile and native extraction with no Node/JVM/nbb fallback. These
benchmark results do not establish the full own-source check/refactor/compile
plus process-trace 100% selfhost gate.

Evidence: `docs/evidence/coscientist-crc32-full-20261004/` contains both complete
reports, native/C artifacts, original pins, guards, sanitizer receipts,
regeneration/pin-refusal proof and fresh replay. Unpack beside pinned upstream,
runner and images/r6m:

```sh
python3 measure-crc32-full.py coscientist-crc32-chunks-replay
python3 measure-crc32-full.py coscientist-crc32-scalar-replay
# In fresh directories on quiet asher only:
python3 measure-crc32-full.py coscientist-crc32-chunks-replay --measure
```

A report is never replaced, native check must accept the source, and failures
are saved. Optional measurement requires hostname asher, load <=4, 32 bodies
per call, warmup, calibrated intervals and 30 rotated samples per arm. This
load gate is not CPU-idle or formal native perfgate qualification. C/i64-vector/
scalar representations and reset/verification/ABI costs remain included.
Measure candidates against comparable C before ranking or promotion; do not
infer gains from resource counts.

The canonical matrix now has 12 matched original-active-profile paths and
seven single-body paths still requiring initialization/repetition/timing
alignment. All earlier timing/score claims remain unchanged. Remaining paths:
aha-mont64, matmult-int, md5sum, nettle-sha256, tarfind, ud and xgboost.
