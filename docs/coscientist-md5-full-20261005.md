# Selfhost MD5: complete initialized and repeated original body

Native selfhost Amu compiles the original 1,000-byte MD5 profile. Each body
writes all input bytes, clears all 1,080 padded allocation bytes, copies the
input, writes the original padding/bit length and runs all 16 blocks of 64
rounds. Hash state resets each body; the original XOR verifier runs once after
the batch. No expected digest is used during compression. C calls unchanged
benchmark_body(1,n,MSG_SIZE) and verify_benchmark; LOCAL_SCALE_FACTOR=66 is
normalized to one body in this research adapter, not an official scoring driver.

Batches 0/1/2/17/32 return 0/1/1/1/1 in both arms. All input/padding bytes,
four final digest words and 64 post-block state words match: 2,940 packed/state
observations covering 10,400 byte values and 340 state words. Four bytes are
packed injectively as base-256 digits within UINT32_MAX; no checksum/collision
assumption is used. The diagnostic C copy only captures state after each
block. Its final digest, return value and 2,080 heap bytes agree with the
unchanged body. ASan/UBSan passes original bodies/verifiers 1..32 and 19,404
initialized packed/state observations across counts 0..32.

Native reuses one owned 2,084-cell workspace in the benchmark. Diagnostic
execution uses 2,148 cells to capture all block states. The first complete
prototype wrote diagnostic snapshots on the benchmark path; the accepted
version excludes those stores and was revalidated against all observations.
Arithmetic helpers are AST-composed unchanged from the historical port;
the historical source itself is untouched. Immutable shift/constant tables
are retained separately. C has byte arrays and uint32 state, native has i64
storage with explicit 32-bit masking, bounds and ownership checks. Allocation,
input generation, clearing, copies, compression and final verifier remain
included in future timings. This qualifies the original sequential input,
not a generic MD5 API, arbitrary message lengths or aliasing behavior.

Bounds index 2,147 succeeds, 2,148 traps and fuel 1 traps. The benchmark fits
the unchanged fuel and arena limits (298,915 fuel for 32 bodies within
the 16,777,216 maximum; arena maximum 65,536). Zero-body diagnostic C storage is cleared
to match fresh native allocation. Source/adapter/profile regenerate identically;
changed C inputs or helper source refuse under Python -O. Product bootstrap
inventory stays at 97 entries. Python/Clang serve as bootstrap audit tools;
checking/compiling the product uses native selfhost Amu. Full own-source and
no-host-process 100% qualification remains unmet.

The first bootstrap generator draft missed its regex import and was corrected
before native checking; its draft is retained. New owned-body/profile and
observation authoring has no applicable mechanical Amu refactor rule. Existing
helpers are composed using the AST reader/writer, not rewritten. No refactor
verify pass is claimed.

The canonical 19-path native matrix now has 17 matched original active profiles;
nettle-sha256 and xgboost still need repetition/initialization alignment.
asher is offline at this snapshot, so there are no new elapsed measurements,
official scores, C speedup claims or formal performance qualifications.
Removing diagnostic stores is an unmeasured hypothesis, not a promoted speedup.

Evidence: [summary](evidence/coscientist-md5-full-20261005/summary.json),
[research artifacts](evidence/coscientist-md5-full-20261005/research-artifacts.tgz),
[replay inputs](evidence/coscientist-md5-full-20261005/queued-native-audit.tgz),
[all-path audit](evidence/coscientist-md5-full-20261005/matrix-audit.tgz).
