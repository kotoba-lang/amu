# Completed element-reuse census: calibrated native evidence

The [fallthrough experiment](coscientist-fallthrough-vector-chain-20261006.md)
yielded no qualified speed improvement. This successor observes the current
qualified static-vector-chain product, source5114721849fbe4dc7d4775f54a00f9a65519b698,
to decide whether value forwarding has enough support to implement. **No new
optimizer or performance measurement is claimed.** The full original19
C-or-better objective remains open.

## What the native execution says

For one original statemate body, closed mode2 paths complete208 reads and272
writes.16 reads (7.6923%) match the handle AND element index of the latest completed
read/store. All16 follow stores across observed closed compatible boundaries;
none is a straight-line same-function pair. The broader observed paths have17
matching reads:1 after a read and16 after a store. These counts scale at1/2/17/32
original bodies. The recorder covers chain-read/store paths; other specialized
vector paths are outside that observation. Counts are not cost shares, savings,
spare-register/alias validity proofs or general effect summaries.

A separate, deliberately limited CONST/LGET/LSET source-fact interpreter erases
facts at labels/branches and unknown arithmetic/results. It independently finds
that every208 read and272 write on the observed closed paths uses a locally
constant index. Each predicted index agrees with the actual runtime record.
Only4 of272 stores have a known literal VALUE (three0, one1) under this limited
analysis. This discourages a latest-element cache and points toward preserving
local index facts for direct constant-offset access. It does not prove that the
compiler may already use those facts or that fewer instructions will be faster.

## Recorder and independent calibration

The diagnostic compiler is produced by the existing qualified native seed;
there is no Node/JVM/Rust compiler fallback. A separate diagnostic supervisor
context extension at400 points to a bounded event arena. Runtime wrappers preserve
x14..17, NZCV and stack balance; before-access capture records the original handle
and index, while append runs AFTER the actual successful load/store. A trapped
access is pending, never counted as completed. Function-entry, genuine terminal
transfer and label events identify observed boundaries. Returning/indirect/cap/
unknown paths do not establish admitted reuse boundaries. No writes are delayed
and no execution results are cached.

The diagnostic has active and disabled variants. Disabled observer statemate
bytes and entry offset are EXACT current product:
SHA256 `5500419beb37f71f0c2ee09c64233170bc853378b082b694025b45ccbe32152d`,
offset85576. Active instrumentation necessarily changes code; its state parity
is checked separately. The compiler-only SIR site cell15 is unused in product
state and overwritten on each instruction. Production ABI/source are untouched.

Independent calibrations cover24 sequential/alias/different-handle/index-change/
invalid-read cases,8 i64 signed-extreme cases,6 partial-valid-then-invalid-write
cases and15 fuel-exhaustion cases. Completion sequences, every owned vector item,
result/trap and remaining fuel agree with independent scalar models. A field
number matching on a different handle is not counted as reuse; failed accesses
stay pending. i64 arithmetic is specified modulo64 before extreme execution.

For30 original conditions (n0/1/2/17/32, six full/partial fuel budgets), product,
disabled observer, active observer and original supervisor all agree in complete
result/trap/fuel/resource reports and partially written items. Clang assembler
independently confirms5,146 balanced register/NZCV wrappers and all internal
conditional/unconditional joins. A supplementary original64-body run exceeds the
65,536-event capacity: counts truncate and report drops, while all original state
still agrees across three arms. Its truncated counts are excluded from reuse
analysis. Total84 comparison groups/282 supervisor executions. This is observer
qualification, not candidate fixed-point/adoption-gate qualification.

The preparation anchor initially also matched the already wrapped read helper;
it was narrowed to the store helper before first build. The report-only C code
has a retained const-pointer qualifier warning. No oracle was weakened after a
failed execution. Full source/seed/guest/loader snapshots, logs, traces, metadata,
independent models and correction boundaries are archived.

## Next registered optimizer

Track numeric local constants through bounded straight-line typed SIR, including
correct invalidation of explicit AND coalesced writes and all control/unknown
boundaries. For a proved nonnegative small constant vector index, use a scaled
offset access without recreating an index register. Keep all original runtime
local assignments, handle validation, unsigned length check, fuel, memory access
and partial arena state. Negative/large/unknown indices retain original lowering.
There is no workload-name or observed-value selection.

Before adoption: independent constant/dynamic/reassigned/coalesced/loop/branch/
alias/cold/private/invalid/signed-boundary cases; current593 fixtures/25,658
expectations; native fixed point; original19 state/machine/mutation proof; one
unchanged-rule fresh product/candidate/C experiment for every changed guest.
Only a qualified gain proceeds to normal unit/gates and committed-source
integrated fixed point/corpus/all19 measured-code qualification. This optimizer
is registered, not implemented here.

Definition identity remains content addressing of checked semantics and
dependencies; native DefCID/artifact/result caches remain unconnected. No new
performance percentage, official Embench score, release, default rung/bin,
wire20 grant or100% own-source claim.

Evidence: [summary](evidence/coscientist-element-reuse-census-20261006/summary.json),
[completed-pair analysis](evidence/coscientist-element-reuse-census-20261006/analysis.json),
[local source facts](evidence/coscientist-element-reuse-census-20261006/local-facts.json),
[observation](evidence/coscientist-element-reuse-census-20261006/native-observation.tgz),
[next hypothesis](evidence/coscientist-element-reuse-census-20261006/next-hypothesis.json),
[checksums](evidence/coscientist-element-reuse-census-20261006/checksums.sha256).
Extract and run replay-analysis.py to independently reconstruct stored state,
completion sequences, calibrated pair counts and source facts. Offline replay
does not execute native guest code again; native receipts are retained separately.
