# Selfhost qrduino: complete original active-profile alternative

`bench/embench/qr-full.kotoba` now implements the original qrduino benchmark's
version-2/L byte-mode encoder, Reed–Solomon codewords, base frame, zigzag
placement, all eight masks, penalty scoring, strict minimum selection and
format bits. Native selfhost Amu check/compile pass. All 8,640 staged values
and 1,408 repeated-body values match C. Original C benchmark/verification
selfchecks, native bounds/fuel and C sanitizers pass. This replaces the
historical unrelated-prefix parity kernel as a complete alternative for
future measurement, without overwriting that kernel or its timing table.
Two adapted workloads still need complete alternatives: picojpeg and wikisort.
C-or-better remains unachieved; asher is offline and no timing/official score
or compiler optimization promotion follows.

The C source is upstream Embench commit
`09c2ed8c3b7008c95d08b038de4a3f6dc103ed70`. The reviewed input's
`initeccsize(1,22)` selects v2/L, width 25, stride 4, 34 data codewords and
10 parity bytes. The original 21-byte URL plus NUL is the benchmark body.
Three initialized diagnostics exercise 32 A bytes, empty, and a 38-digit
string clipped to 32 by the original encoder. Arbitrary versions, encodings,
unbounded batches and input-validation APIs are outside this profile.

Composition reads accepted placement functions as forms; that component
and its earlier codeword/frame files remain unchanged. New Kotoba functions
implement each upstream mask predicate and reservation check, 2×2 block
penalties, horizontal/vertical run accumulation, long-run/finder penalties,
black/white imbalance using the original strict `big > 625`, eight scores,
strict `<` minimum updates, resetting the filled image after a candidate,
mask reapplication and format bits. The `#if 0` early-accept heuristic stays
disabled. This is new algorithm/AST-composition authoring outside existing
native refactor rules, not a claim of successful refactor verification.
Initial authoring needed a missing delimiter, typed owned-vector write
helper and binary bit-and arity correction before native check acceptance.
The C adapter needed its scale definition and a newline before its closing
brace to prevent the trailing source comment swallowing it. No differential
semantic mismatch was observed after acceptance.

The original input has equal penalties 1208 for masks 1 and 6; strict `<`
keeps mask 1. The long diagnostic chooses mask 7 and exercises the original
last-candidate break (`i == 7`). Both selection paths match C. Format bits
are applied after scoring, as upstream does. Critically, original
`verify_benchmark` checks 22 bytes of the *unmasked* filled image retained in
`strinbuf`, plus the allocator bound; it does not validate the final masked
image. The native batch preserves that verifier. Stronger diagnostics also
compare all 100 unmasked bytes, all 100 final bytes, base/reservations,
all eight penalties and chosen mask/minimum/stopping index.

Four inputs across ten stages give 8,640 matches: 200 filled-image values,
201 values for each of eight masks (image plus score), and 352 final values
per input. Final values include 100 unmasked bytes, 100 masked/formatted
bytes, 100 base bytes, 41 reservations and 11 score/selection fields.
The same 352 fields match after 1/2/17/32 original-input bodies, giving
1,408 more comparisons. C snapshots agree with unchanged `qrencode` for
all four inputs and unchanged `benchmark_body(1,n)` plus `verify_benchmark`
for all four repeated counts. The C batch directly invokes those original
functions, preserving heap reset, allocations, frame/ECC frees and verifier.
Its definition `GLOBAL_SCALE_FACTOR=1` keeps the otherwise unused upstream
`benchmark()` buildable. Paired research calls normalize to n complete
bodies instead of the official local factor 5; this is not an official score.

The native batch owns one 2,048-cell i64 workspace and reuses it for every
body. Base/reservation regions and run scratch are reset; input/NUL and the
encoder overwrite their active buffers. It stores bytes as i64 values and
retains score metadata, unlike C's byte arrays/local scalars. These costs
remain inside timing; no speedup is inferred from representation changes.
Thirty-two bodies consume 2,711,481 fuel, below the unchanged 16,777,216
runner limit, and return the original verifier result 1. Zero bodies return
0 by the research wrapper contract. Index 2047 succeeds, 2048 traps; fuel 1
traps a body. C ASan/UBSan pass four unchanged QR selfchecks, all repeat
counts 1 through 32 with the original verifier, and 8,032 initialized
image/score reads. Fresh and reused native paths are both checked.

The compiler is the byte-identical three-generation native Amu build,
SHA-256 `abcc1318957af7d3a09cfd66c06d17821b5cf47f4c47d02b5620e9e92a24f02e`.
Check, compile, extract and runtime use that path. Python/Clang are bootstrap
comparison tooling outside the product. All 97 PRODUCT inventory entries
remain unchanged; this does not establish 100% own-source selfhost or its
exec-tracer gate. Source/native/C artifacts, provenance and each comparison
are saved in `docs/evidence/coscientist-qr-full-20261004/`. Regeneration is
byte-identical; five modified source pins are refused even under Python -O.

Unpack the fresh replay beside pinned `upstream`, `runner` and `images/r6m`:

```sh
python3 measure-qr-full.py coscientist-qr-full-replay --correctness-only
```

Omit `--correctness-only` on asher when quiet to run the research comparator:
32 bodies per call, untimed warmup, calibrated call counts, 30 rotating
paired samples, and load at most 4 before/after every sample. Record the
additional host qualification required by the existing formal contract;
load alone does not establish that gate. The harness refuses existing
reports, requires native check acceptance, persists failures and retains
raw samples. Current timing rows are empty; performance-measured, official
score and formal qualification flags are false. No new ratio is published.

Next measure the complete paths on quiet asher, identify the largest gap,
reflect with a cheap artifact experiment, and rank only separated gains
before compiler changes. Complete picojpeg/wikisort alternatives in parallel
with host availability, preserving the full C-or-better objective.
