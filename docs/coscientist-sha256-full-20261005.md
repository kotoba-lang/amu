# Selfhost SHA-256: full context lifecycle and repeated original body

Native selfhost Amu compiles the original 56-byte SHA-256 profile: output
buffer clearing, context initialization, update copying, two padding
compressions, big-endian digest serialization and post-digest context reset.
All 64 rounds run for each block, with explicit modulo-32-bit state updates.
The original message and arithmetic helpers are retained; expected bytes
are used only for verification. C executes its unchanged benchmark_body(1,n)
and verifier, with LOCAL_SCALE_FACTOR normalized to one body in this research
adapter. This is not an official scoring driver or a generic SHA API.

Batches 0/1/2/17/32 return 0/1/1/1/1 in both arms. All 1,510 packed/state
observations match across context initialization, the 56-byte update, both
compression inputs/states and post-digest reset. All 32 digest bytes are
compared, packed four at a time as injective base-256 digits within UINT32_MAX.
Uninitialized context block tails at init/update and C struct padding are
never observed. The diagnostic C copy only captures initialized fields;
its full digest agrees with the unchanged original body.

The original C verifier checks eight bytes because its loop uses
_SHA256_DIGEST_LENGTH=8. The timed native verifier mirrors this traversal;
qualification separately compares all 32 output bytes to the complete pinned
original hash golden for all positive native batches. ASan/UBSan validates
32 original bodies/verifiers, their complete 32-byte golden digests and
9,966 initialized packed/state observations across counts 0..32. Existing
historical full-digest checks remain unchanged.

Native reuses one owned 170-cell benchmark workspace: block buffer, expanded
64-word schedule, state, digest buffer and count/index. Diagnostics allocate
464 cells to capture the phases; their stores are excluded from the benchmark
path. The 32-body call uses 79,084 fuel within the unchanged 16,777,216 maximum;
arena maximum is 65,536. Diagnostic index 463 succeeds, 464 traps, fuel 1
traps. Bounds, ownership, handle and ABI checks remain enabled.

C uses byte buffers, uint32 state and a 16-word rolling schedule; native uses
i64 storage with explicit masking and an expanded 64-word schedule. Native
immutable input/constant tables are separate. Initialization, buffer clearing,
copying, padding, schedule expansion, compression, serialization, reset and
verification all remain included in future timings. This qualification covers
the original sequential input and lifecycle, not arbitrary lengths, partial
updates, aliasing or uninitialized padding.

Source/adapter/profile regenerate byte-identically. Changed upstream source
or helper source refuses under Python -O. Product bootstrap inventory stays
at 97. Python/Clang are bootstrap audit tools; checking and compilation use
native selfhost Amu. Full own-source/no-host-process 100% qualification remains
unmet. New owned-body/profile/diagnostic authoring has no applicable mechanical
Amu refactor rule; existing helpers are AST-composed unchanged. Historical
ports and compiler sources are untouched; no refactor verify pass is claimed.

The canonical native audit rebuilds/runs all 19 paths with exact qualified
machine-byte identity. Eighteen have matched original active profiles;
xgboost still needs repetition/initialization alignment. asher remains offline.
No new elapsed times, official score, C speedup or formal performance
qualification is claimed. Workspace reuse is an unmeasured hypothesis.

Evidence: [summary](evidence/coscientist-sha256-full-20261005/summary.json),
[research artifacts](evidence/coscientist-sha256-full-20261005/research-artifacts.tgz),
[replay inputs](evidence/coscientist-sha256-full-20261005/queued-native-audit.tgz),
[all-path audit](evidence/coscientist-sha256-full-20261005/matrix-audit.tgz).
