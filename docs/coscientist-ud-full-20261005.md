# Selfhost UD: original LU and repeated substitutions

Native selfhost Amu compiles the complete original UD active profile: six
equations in 20x20 storage, initialization each body, lower/upper elimination,
forward substitution and backward substitution. All 20 expected x values and
the return marker are verified once after the batch. Expected values are
used only in verification. The original C body and verifier are unchanged;
LOCAL_SCALE_FACTOR=1785 is normalized to one body in this research adapter.
This is not an official scoring driver or a general linear-system API.

All batches 0/1/2/17/32 return 0/1/1/1/1 in both arms. All 400 matrix cells,
20 b cells, 20 x cells, six initialized y cells and the return marker match
C for each batch: 2,235 observations. The diagnostic C copy captures y[0..5]
before returning; unused uninitialized y[6..99] is never read. Its complete
matrix/b/x and result are checked against the unchanged original body.
Independent ASan/UBSan passes original bodies/verifiers 1..32 and 14,751
initialized observations at counts 0..32.

Native uses one owned 541-cell i64 workspace per call, reused across 32
bodies. It consumes 16,280 fuel within the unchanged maximum 16,777,216.
Index 540 succeeds, 541 traps, and fuel 1 traps. Arena, bounds, ownership,
handle and ABI checks remain enabled. Source, C adapter and profile regenerate
byte-identically; a changed upstream source refuses under Python -O. Product
bootstrap inventory is unchanged at 97 entries.

C uses global long arrays, a stack y array and volatile chkerr. Native uses
flat owned i64 storage, integer division truncating toward zero and an i64
return marker. Only this original sequential profile is qualified; arbitrary
inputs, singular systems, aliasing and volatile synchronization semantics are
not. Native allocation, flattened indices, checks and verifier traversal
remain included in future paired timings. Zero-body diagnostics explicitly
clear C storage to match fresh native allocation. Positive bodies preserve
the original initialization and carry behavior.

New full-body/profile/diagnostic authoring has no applicable mechanical Amu
refactor rule. Historical ports and compiler sources are unchanged; no
refactor verify pass is claimed. Python and Clang are bootstrap audit tools;
the Kotoba product is checked and compiled by the native selfhost compiler.
The full own-source/no-host-process 100% gate remains unmet.

The canonical 19-path native matrix now has 15 matched original active
profiles. md5sum, nettle-sha256, tarfind and xgboost still need repetition and
initialization alignment. asher remains offline at this snapshot. No elapsed
values, official score, C speedup or formal performance qualification are
claimed. Correctness and fuel consumption do not establish C-or-better speed.

Evidence: [summary](evidence/coscientist-ud-full-20261005/summary.json),
[research artifacts](evidence/coscientist-ud-full-20261005/research-artifacts.tgz),
[replay inputs](evidence/coscientist-ud-full-20261005/queued-native-audit.tgz),
[all-path audit](evidence/coscientist-ud-full-20261005/matrix-audit.tgz).
