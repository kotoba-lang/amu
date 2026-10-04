# Picojpeg: complete original active profile through native selfhost

The original Embench JPEG now runs its full active decoding path in Kotoba,
compiled by the native selfhost-built Amu. All IDCT intermediate values,
all 56 MCU RGB outputs and repeated terminal states match the original C.
This completes correctness for the original successful input, not a general
JPEG decoder API. There is no new timing or C performance win in this wave.

The original fixture is 570 bytes, 51×64, three components, YH1V1, 8×8 MCUs,
three blocks per MCU, 7 columns × 8 rows = 56 MCUs. The implementation reads
those bytes, constructs quantization/canonical Huffman tables at runtime,
decodes all 168 DC/AC coefficient blocks, executes the original Winograd
IDCT row and column operations, and converts Y/Cb/Cr to RGB. Signed extension,
zigzag, predictor updates, dequantization, intermediate i16 narrowing,
rounded arithmetic shifts, DC shortcuts and clamping follow the pinned C.
The original successful input has no restart interval and no reduced mode.
Other sampling modes, arbitrary inputs and error-path APIs are unqualified.

C observations copy the original decode/transform routines, inserting
snapshots after idctRows, idctCols and the original color switch. The entire
original switch and unused branches remain in the C observation copy.
Native code implements the actual YH1V1 branch used by this input.
Observation selfchecks compare all terminal entropy/predictor/IDCT state,
all three 256-byte RGB buffers and the original verifier with unchanged
benchmark_body at 1, 2, 17 and 32 iterations. The full comparator calls the
unchanged original benchmark_body(1,n), then its original verifier.

All 37,756 native/C observations match:

- IDCT rows and columns: 168 blocks × 64 values × 2 phases = 21,504.
- RGB after each complete MCU: 56 × 64 pixels × 3 channels = 10,752.
- Terminal reader/predictor/counter/status/IDCT/RGB storage: 1,100.
- Reused full decoder states at 1, 2, 17 and 32 bodies: 4 × 1,100 = 4,400.

This includes all 56 padded 8×8 MCUs, not just the original verifier's final
64 pixels per channel. Terminal/repeated comparisons include all 256-byte
buffers per channel, including unused storage. The native verifier uses the
same 192 literal expected pixels as original verify_benchmark; those literals
are used only after decoding. They do not replace any computed output.
Zero bodies return zero; 1, 2, 17 and 32 full bodies all return one in both
arms. Original decode termination is PJPG_NO_MORE_BLOCKS, remaining zero.

The full native call allocates one owned 4,096-cell workspace and reuses it
between bodies. Init resets the original reader/callback/image/scan/valid
fields while retaining the same tables/buffers as C; parsing overwrites the
active tables and decoding overwrites active coefficients/RGB. Each body's
initScan resets DC predictors. The shared arena limit remains 65,536 cells.
32 bodies need minimum passing fuel 7,102,019, established by bounded native
probes, within the unchanged 16,777,216 maximum. Index 4,095 passes, 4,096
traps, and fuel 1 traps. ABI and all runtime safeguards remain unchanged.

Representation and measurement boundary: native storage is i64 cells with
explicit narrow arithmetic, C uses original globals/i16/u8 storage and pointer
based image-info fields. Native header metadata represents the original
image information, without a separate external pInfo pointer struct.
Native allocation, reset, runtime guards and native pixel-verifier traversal
are retained; C's comparator includes its original init/decode/verifier.
These costs must remain disclosed in subsequent paired timings. This is a
complete original-input comparison, not an official full-suite score.

Independent ASan/UBSan runs pass all original C full bodies 1..32,
33,356 initialized transform observations and 35,200 initialized repeated
state reads. The first transform harness draft had an artifact filename
mismatch and refused native check before execution; it is retained as failed
evidence. A missing parenthesis during initial source generation was corrected
before native acceptance. A sanitizer wrapper name collision was corrected
before compilation succeeded. Neither was a semantic mismatch. The earlier
coefficient adapter's null-pointer failure and correction remain in the
previous coefficient evidence; the transform adapter explicitly initializes
image-info pointers before invoking the original verifier.

The coefficient component remains unchanged. New transform functions are
AST-composed with it, then the complete repeated-body wrapper is AST-composed
with the unchanged transform component. This is new algorithm authoring,
not a mechanical edit covered by an Amu refactor rule; no refactor verify pass
is claimed. Both sources, C adapters and profiles regenerate byte-identically.
Six altered-source-pin tests refuse under Python -O, covering all three pinned
picojpeg source files for both generators. All 97 PRODUCT inventory entries
remain unchanged. Python/Clang are bootstrap preparation/oracle tools only.

Check, compile and extraction use native compiler SHA-256
`abcc1318957af7d3a09cfd66c06d17821b5cf47f4c47d02b5620e9e92a24f02e`,
the byte-identical three-generation selfhost build. These benchmark results
do not establish the own-source check/refactor/compile plus exec-trace 100%
selfhost gate. Formal performance qualification remains false.

Evidence: `docs/evidence/coscientist-picojpeg-full-20261004/` stores original
pins, composition inputs, native/C artifacts, complete comparisons, guards,
resource probes, sanitizer receipts, failed harness draft and fresh replay.
Unpack replay beside pinned upstream, runner and images/r6m:

```sh
python3 audit-picojpeg-transform.py coscientist-picojpeg-transform-replay
python3 audit-picojpeg-full.py coscientist-picojpeg-full-replay
```

Reports are never replaced, check acceptance is required, and failures are
persisted. The full report qualifies the complete original active workload;
performance/official-score/formal flags remain false and timing rows empty.
asher is offline, so this wave changes no historical timing, numerical ranking
or compiler optimization promotion. Next audit the complete comparison matrix,
then use quiet asher for repeated paired selfhost/C measurements and rank
compiler hypotheses against the largest verified gap.
