# Selfhost aha-mont64: complete matched repeated body

Native selfhost Amu now compiles a complete repeated Montgomery benchmark
using the unchanged checked unsigned-64 helper AST from the historical port.
The new body computes the ordinary modular result and the Montgomery result,
checks the original partial inverse identity and accumulates the same error
flag as C. No stored reference value substitutes for either computation.
0/1/2/17/32 native and C batches return 0/1/1/1/1. Four final fields after each
1/2/17/32 batch match C: 16 observed values. C observation copies preserve
all original body operations and volatile inverse variables; its error result
matches unchanged benchmark_body/verify_benchmark.

The timed-comparison entry is prepared, not measured: native performs all
bodies and verifies the last error flag once; C initialise_benchmark sets the
three original input globals once per adapter call, followed by unchanged
benchmark_body(1,n) and verify_benchmark. Native binds the corresponding i64
bit patterns within each body. Normalization uses one body instead of the
original LOCAL_SCALE_FACTOR for the disclosed n-body research adapter.
Unsigned values use two's-complement i64 bits with original unsigned compare,
carry and right-shift logic. Native immutable result vectors and C output
pointers/globals/volatile reads differ in representation/access semantics.
This qualifies the original sequential fixed input, not general volatile or
arbitrary-input modular arithmetic APIs. These costs and differences must
remain explicit in subsequent paired timings.

Native 32 bodies fit the unchanged arena/fuel limits (65,536/16,777,216).
Constant-vector index 3 succeeds and index 4 traps. The first audit draft
incorrectly expected the owned-vector SIGILL code for this constant vector;
constant-vector bounds emit an index-versus-4 comparison and BRK, yielding
SIGTRAP. The failed audit is retained. The corrected expectation requires
that actual trap; generated guards and runtime were not modified. Fuel 1
also traps. A negative-index probe is refused by the runner before native
execution and is not presented as a native bounds test.

Independent ASan/UBSan passes all original C bodies/verifiers 1..32 and
128 initialized observations. Generator source/helper pins refuse under
Python -O. Source/adapter/profile regenerate byte-identically; helper AST is
unchanged. New body/batch/diagnostic authoring has no applicable Amu mechanical
refactor rule; no old workload/compiler source was rewritten and no refactor
verify pass is claimed. All 97 PRODUCT entries remain unchanged. Python and
Clang are bootstrap preparation/oracle tools only.

Check/compile/extraction use the byte-identical three-generation selfhost
compiler SHA-256 abcc1318957af7d3a09cfd66c06d17821b5cf47f4c47d02b5620e9e92a24f02e.
The full own-source check/refactor/compile and process-trace 100% gate is not
established by these benchmark checks.

Evidence: docs/evidence/coscientist-mont64-full-20261004 contains full native/C
artifacts, all observations, original-body selfchecks, bounds/fuel receipts,
failed expectation draft, sanitizer/pin/regeneration proof and fresh replay.
Unpack beside pinned upstream, runner and images/r6m, then run:

```sh
python3 audit-mont64-full.py coscientist-mont64-full-replay
```

The report cannot be replaced; check must accept and failures persist.
Performance/official-score/formal flags remain false and timing rows empty.
asher is offline; no timing/ranking/promotion follows. Matrix coverage is now
13 matched original-active profiles and six remaining single-body alignments:
matmult-int, md5sum, nettle-sha256, tarfind, ud, xgboost. C-or-better remains
unachieved; remaining adapters and quiet-host measurements come next.
