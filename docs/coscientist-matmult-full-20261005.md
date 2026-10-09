# Selfhost matmult-int: complete initialized and repeated 20x20 body

Native selfhost Amu compiles a matched complete matrix benchmark. It generates
all 800 reference inputs using the original modulo-8095 RNG, copies all 800
active input cells each body, computes all 400 output cells using all 8,000
multiply-adds, then verifies the original 400 expected values once after the
batch. No expected output is used during multiplication. C calls unchanged
initialise_benchmark, benchmark_body(1,n) and verify_benchmark. Its original
LOCAL_SCALE_FACTOR=39 is normalized to one body for this n-body research
adapter, not an official scoring driver.

All 0/1/2/17/32 batches return 0/1/1/1/1 in both arms. After initialization and
1/2/17/32 bodies, all 2,001 state cells match C: 800 reference inputs, 800
active inputs, 400 outputs and final RNG state. That is 10,005 comparisons.
The zero-body diagnostic explicitly starts active/result C arrays at zero,
matching fresh native allocation; zero-body benchmark itself is a no-op.
Independent ASan/UBSan passes all original C bodies/verifiers 1..32 and
66,033 initialized observations (all state cells at counts 0..32).

Native allocates one owned 2,001-cell i64 workspace and reuses it across
all 32 bodies. This call consumes 347,702 fuel within the unchanged maximum
16,777,216 and arena maximum 65,536. Index 2,000 passes; 2,001 traps. Fuel 1
traps. ABI, bounds, handle and ownership checks remain enabled.

C uses original global long matrices and memcpy, native uses a flat i64 owned
workspace with explicit copy loops. Native accumulates each dot product in a
scalar before storing its final cell; C source updates the result during each
MAC. Actual distinct input/output regions and all sequential final states
are qualified; arbitrary overlapping/aliased matrix APIs are not. Original
input values keep sums within range. Native allocation/init/copies, bounds,
flattened index operations, verifier traversal and ABI costs remain included
in future paired timings. This is an original-input comparison, not a generic
matrix API or a pure compiler-only estimate.

The first source draft used unknown vector-set! and was refused by native
check before execution. New authoring was corrected to the existing owned
vector-assoc! operation. Failed source/check evidence is retained; no checker
or runtime rule was altered. New full-body/profile/diagnostic authoring has
no applicable Amu mechanical refactor rule, no historical/compiler source
was rewritten and no refactor verify pass is claimed.

Source, C adapter and profile regenerate byte-identically. Changed upstream
input refuses under Python -O. All 97 PRODUCT inventory entries are unchanged.
Python/Clang are bootstrap preparation/oracle tools only. Check, compile and
extraction use source-built three-generation native compiler SHA-256
abcc1318957af7d3a09cfd66c06d17821b5cf47f4c47d02b5620e9e92a24f02e.
The own-source check/refactor/compile plus process-trace 100% gate is not
established by these benchmark checks.

Evidence: docs/evidence/coscientist-matmult-full-20261005 includes all state
comparisons, full native/C artifacts, original pins, guards/resource proof,
sanitizer receipts, refused draft and fresh replay. Unpack beside pinned
upstream, runner and images/r6m:

```sh
python3 audit-matmult-full.py coscientist-matmult-full-replay
```

The harness refuses replacement, requires native acceptance and saves
failures. Performance/official-score/formal flags stay false; timing rows
are empty. asher is offline, so no speed/ranking/promotion is claimed. Matrix
coverage becomes 14 matched original-active profiles / five pending paths:
md5sum, nettle-sha256, tarfind, ud and xgboost. Historical timings are unchanged.
Next finish those contracts and collect quiet-asher paired measurements.
C-or-better remains unachieved.
