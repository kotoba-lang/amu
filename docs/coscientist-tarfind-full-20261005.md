# Selfhost tarfind: complete repeated headers and carried RNG

Native selfhost Amu now compiles the original active tarfind profile with
35 full 257-byte TAR headers, zero initialization each body, filename lengths
5..39, size/link flags and all five sequential name searches. The BEEBS RNG
starts at zero once per ABI call and carries between bodies. Expected names
or search results are not substituted for execution. C uses its unchanged
benchmark_body(1,n) and original verifier; LOCAL_SCALE_FACTOR=46 is normalized
to one body in this research adapter. This is not an official scoring driver.

Batches 0/1/2/17/32 return 0/1/1/1/1 in both arms. All 8,995 initialized header
bytes, final RNG state and result match at each count. Eight bytes are packed
as base-256 digits for observation: each actual byte is 0..90, so this is an
injective representation below INT64_MAX, not a probabilistic checksum.
The last group is explicitly zero padded. All 5,635 packed/state observations
match, covering 44,975 header bytes. No copied/instrumented C body is needed:
observations read the actual original heap and RNG. ASan/UBSan passes 32
original bodies/verifiers, 296,835 initialized header-byte domain checks and
37,191 packed/state reads across counts 0..32.

Native owns one 8,997-cell i64 workspace reused across bodies. C stores bytes
in its static BEEBS heap, resets allocator pointers and allocates/frees each
body. Native retains all header clearing, name generation, bounds checks and
searches; its i64 storage and allocation/ABI cost remain in future timings.
Zero-body diagnostics clear C storage to match fresh native allocation.
Both arms explicitly reset RNG per measured ABI call; neither resets RNG
between positive bodies. This qualification covers the original sequential
profile, not arbitrary TAR archives, general malloc behavior or aliased APIs.

Bounds index 8,996 succeeds, 8,997 traps and fuel 1 traps. The 32-body call
consumes 665,864 fuel within the unchanged 16,777,216 maximum and fits
the unchanged 65,536-cell arena limit. Source/adapter/profile regenerate
byte-identically. Mutating either upstream tarfind.c or beebsc.c refuses
under Python -O. Product bootstrap inventory stays at 97 entries. Python and
Clang are audit tools; product checking and compilation use native selfhost
Amu without a host compiler fallback. The complete own-source/no-host-process
100% gate remains unmet.

New algorithm/profile/observation authoring has no applicable mechanical Amu
refactor rule. Historical ports and compiler sources are unchanged. No
refactor verify pass is claimed.

The canonical 19-path native matrix now has 16 matched original active
profiles; md5sum, nettle-sha256 and xgboost still need repetition/initialization
alignment. asher remains offline at this snapshot. No elapsed values,
official score, C speedup or formal performance qualification are claimed.

Evidence: [summary](evidence/coscientist-tarfind-full-20261005/summary.json),
[research artifacts](evidence/coscientist-tarfind-full-20261005/research-artifacts.tgz),
[replay inputs](evidence/coscientist-tarfind-full-20261005/queued-native-audit.tgz),
[all-path audit](evidence/coscientist-tarfind-full-20261005/matrix-audit.tgz).
