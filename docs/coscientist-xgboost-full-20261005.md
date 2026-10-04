# Selfhost xgboost: complete owned model and repeated inference

Native selfhost Amu compiles all original 400 trees, all 128x64 samples and
labels. All 39,555 upstream bytes remain present. Encoded constants and decoder
helpers are AST-composed unchanged; the native call decodes them once into
owned storage. Inference uses direct owned-vector reads and carries tree/node/
leaf offsets across classes as C does. Each sample clears all ten votes,
traverses every tree and selects the first maximum class. No prediction or
expected correct count is substituted for inference. Correct counts accumulate
across bodies, matching the unchanged original C benchmark_body(1,n).

Raw counts at 0/1/2/17/32 bodies are 0/126/252/2142/4032 in both arms. All
39,555 model/sample/label bytes match through 9,889 injective four-byte groups
(final group zero padded). All 4,227 count/prediction/vote observations at
0/1/32 bodies match C: every sample and every class. The copied C predictor
only captures final votes; its predictions agree with unchanged predict.
ASan/UBSan passes original bodies/counts 1..32, 46,497 initialized snapshot
reads and all 9,889 model groups. This is the complete original fixed model,
not a generic model-loader API or a subset of trees/samples.

Native reuses one owned 39,566-cell benchmark workspace. Diagnostic execution
uses 40,974 cells for all 128 predictions and 1,280 votes, with stores excluded
from the benchmark path. The 32-body call consumes 11,079,189 fuel within the
unchanged 16,777,216 maximum and 65,536-cell arena. Diagnostic index 40,973
succeeds, 40,974 traps and fuel 1 traps. Bounds/ownership/handle/ABI checks
remain enabled. No larger resource limit was introduced to make this pass.

C keeps uint8 model/input arrays static, uses uint16 votes and a volatile sample
index. Native includes per-call base64 decoding, i64 model storage and owned
allocation, uses sequential scalar loop indices and i64 votes. Original votes
stay below 40x255, so uint16 addition has no wrap in this profile. Data decoding,
allocation, full inference, scratch clearing and verifier remain in future
paired timings. Static storage, cache footprint, volatile accesses and memory
representation differ; this is an implementation-level comparison, not a pure
compiler-only estimate. Arbitrary models/aliases/concurrent volatile semantics
are unqualified.

The original C verifier with this GLOBAL_SCALE_FACTOR=1 adapter accepts
nonnegative counts: its integer division by 12 truncates to zero. The timed
native verifier mirrors it; qualification separately requires exact counts,
all predictions and all class votes. Historical stronger port checks remain
unchanged. Zero-body benchmark is an explicit no-op; diagnostic storage starts
fresh while model/input data is initialized.

Source/adapter/profile regenerate identically. Mutating any of the three C
inputs or the encoded data/decoder source refuses under Python -O. PRODUCT
inventory stays at 97. Python/Clang are bootstrap audit tools; checking and
compilation use native selfhost Amu. Full own-source/no-host-process 100%
qualification remains unmet. New owned-model/repetition/profile authoring has
no applicable mechanical Amu refactor rule; existing definitions are composed
through the AST reader/writer. No historical/compiler source is rewritten and
no refactor verify pass is claimed.

The canonical audit rebuilds/runs all 19 native paths with byte identity; all
19 now have matched original active-profile alternatives. Whole-suite timing
and official scoring remain unqualified. asher is offline and direct SSH times
out, so there are no new elapsed measurements, C speedup claims or formal
performance qualifications. Decode-once/direct reads/carried offsets are
unmeasured hypotheses, not promoted speedups or goal completion.

Evidence: [summary](evidence/coscientist-xgboost-full-20261005/summary.json),
[research artifacts](evidence/coscientist-xgboost-full-20261005/research-artifacts.tgz),
[replay inputs](evidence/coscientist-xgboost-full-20261005/queued-native-audit.tgz),
[all-path audit](evidence/coscientist-xgboost-full-20261005/matrix-audit.tgz).
