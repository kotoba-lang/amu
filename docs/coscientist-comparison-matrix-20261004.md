# Embench comparison matrix: current canonical native paths

The current 19 canonical comparison inputs all pass check, compile, extraction
and execution with the byte-identical three-generation native selfhost Amu.
Every extracted native image matches the exact saved qualified machine bytes.
This is a fresh artifact/resource audit, not a new timing study or a re-run of
all earlier C differentials. It establishes which current sources correspond
to which previously verified comparisons. No performance improvement follows.

The matrix has 11 matched original-active-profile alternatives (including the
replacement depthconv path) and 8 historical single-body correctness paths
that still need timing/initialization/repetition alignment. Completing ten
formerly adapted algorithms did not automatically align the other eight.
The historical nine-port ratios and geometric mean remain historical.

| Workload | Qualified comparison scope | Fresh native inputs |
|---|---|---|
| aha-mont64 | single-body correctness; timing alignment pending | one test export |
| crc32 | single-body correctness; timing alignment pending | one test export |
| depthconv | matched original active profile | 0, 1, 2, 17, 2000 |
| edn | matched original active profile | 0, 1, 2, 17, 32 |
| huffbench | matched original active profile | 0, 1, 2, 17, 32 |
| matmult-int | single-body correctness; timing alignment pending | one test export |
| md5sum | single-body correctness; timing alignment pending | one test export |
| nettle-aes | matched original active profile | 0, 1, 2, 17, 32 |
| nettle-sha256 | single-body correctness; timing alignment pending | one test export |
| nsichneu | matched original active profile | 0, 1, 2, 17, 32 |
| picojpeg | matched original active profile | 0, 1, 2, 17, 32 |
| qrduino | matched original active profile | 0, 1, 2, 17, 32 |
| sglib-combined | matched original active profile | 0, 1, 2, 17, 32 |
| slre | matched original active profile | 0, 1, 2, 17, 32 |
| statemate | matched original active profile | 0, 1, 2, 17, 32 |
| tarfind | single-body correctness; timing alignment pending | one test export |
| ud | single-body correctness; timing alignment pending | one test export |
| wikisort | matched original active profile | 0, 1, 2, 17, 32 |
| xgboost | single-body correctness; timing alignment pending | one test export |

Each positive matched batch returns one; its zero batch returns zero. Each
historical zero-argument test export returns one for one complete input/output
check. All fuel-1 calls trap. 32-body full paths retain the 16,777,216 fuel
maximum; depthconv retains its separately qualified 2,000-body contract.
No input was reduced, and no fuel/bounds/ABI limit was loosened to pass.
The audit records fuel consumption rather than elapsed times. In particular,
XGBoost's current single-body path uses 1,587,388 fuel; this does not qualify
32 bodies at the shared maximum. Any future batch must fit the existing
budget and preserve all 400 trees, 128 inputs and their predictions.

The eight pending paths are aha-mont64, crc32, matmult-int, md5sum,
nettle-sha256, tarfind, ud and xgboost. They must receive explicit C/native
adapter contracts covering initialization, iteration count, persistent state
and where verification occurs. For example, tarfind's current correctness
port starts its archive RNG from zero, whereas the original C body carries
its RNG between iterations; copying the single-body test into a loop would
not establish a matched repeated-input comparison. XGBoost's existing port
also reconstructs class offsets repeatedly; the original C carries them
between classes. Normalize and verify these paths before using their old
ratios to rank compiler optimization hypotheses.

Native vectors/i64 storage, C globals/i16/u8 storage, init/reset and verification
costs remain disclosed in individual workload records. NSichneu comparisons
cover sequential transitions and do not establish C volatile-access semantics.
SLRE's short regex buffers use the disclosed padding that makes four-byte
memcmp reads defined. WikiSort's upstream signed overflow remains documented:
plain -O2 is the comparator, plain UBSan fails and labeled -fwrapv sanitization
passes. The matrix does not convert those qualifications into general APIs.

`bench/embench/comparison-matrix.json` pins all 19 canonical source hashes,
the expected qualified native bytes, source-built compiler and runner,
upstream commit and the complete upstream source/support/baseline inventory.
Canonical comment/attribution changes in EDN/Huffbench/AES are not mistaken
for the earlier raw source: freshly compiled machine-byte identity verifies
their correspondence to the already audited execution paths. Refused or
experimental Huffbench initialization variants are not selected by this matrix.

Reproduce beside the recorded compiler/runner/upstream environment:

```sh
python3 scripts/seed/image/audit-embench-comparison-matrix.py \
  /absolute/path/to/amu /absolute/path/to/environment /absolute/path/to/fresh-output
```

The output must not exist. Native check must explicitly accept each source.
Compiler/source/upstream pins and duplicate workload identities fail closed
under Python -O. Runtime/compile failures are persisted; a preflight refusal
creates no qualified output. All 97 PRODUCT dependency entries are unchanged.
This new bootstrap audit adds no product dependency and modifies no compiler
or canonical workload. No Amu refactor rule covers new audit/spec authoring;
no refactor verify success is claimed.

Evidence: `docs/evidence/coscientist-comparison-matrix-20261004/` contains all
fresh native artifacts, inputs/provenance/check/compile/extraction logs, raw
resource/result records, manifest, pin-refusal proof and restartable audit.
Performance, official score, formal perfgate and full own-source 100% selfhost
flags remain false. The full-suite timing flag remains false by construction.
asher is offline and no live measurement job is claimed. Next align the eight
remaining paths, then collect rotated paired measurements on quiet asher and
rank hypotheses against a verified, comparable gap. C-or-better is unachieved.


Follow-up: [CRC32 matched repeated bodies](coscientist-crc32-full-20261004.md)
replaces its historical single-body matrix entry with the verified chunked
32-body path. The updated canonical spec and fresh all-19 audit now record
12 matched original-active profiles / seven pending alignments. The table
above retains the initial audit snapshot. New evidence is in the CRC32
`matrix-audit.tgz`; timing/score/formal flags remain false.


Montgomery follow-up: `coscientist-mont64-full-20261004.md` qualifies the
original full repeated aha-mont64 body and final verifier. Updated canonical
spec and all-19 re-audit now record 13 matched profiles / six pending paths;
full timing/official-score/formal flags remain false. Snapshot evidence is
saved in the Montgomery `matrix-audit.tgz`.


Matmult follow-up (2026-10-05): `coscientist-matmult-full-20261005.md`
qualifies the original init/copy/20x20 repeated body and final verifier.
Updated spec and fresh all-19 audit now record 14 matched profiles / five
pending paths; no full-suite timing/score/formal claim. Matrix evidence is
saved in the matmult `matrix-audit.tgz`.

### 2026-10-05: UD repeated original profile

[UD full qualification](coscientist-ud-full-20261005.md) adds original
initialization, LU, forward/backward substitution and final verification for
0/1/2/17/32 bodies. All 2,235 initialized native/C observations match; C
ASan/UBSan passes 1..32 bodies and 14,751 initialized reads. One owned
541-cell workspace uses 16,280 fuel for 32 bodies, with guards intact.
The canonical native matrix has 15 matched profiles and four paths pending
alignment (md5sum, nettle-sha256, tarfind, xgboost). asher is still offline;
this changes correctness coverage, not historical timings or official scores.
