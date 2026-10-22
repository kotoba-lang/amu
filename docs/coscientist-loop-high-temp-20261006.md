# Qualified loop-contained high-depth vector reads

Original matmult time is15.32% shorter with a general loop-contained high-depth
read optimization. Its emitted machine exactly equals the pinned qualifying
30-triple target from the preceding no-spill experiment; the other18 original
benchmark guests are byte-identical to previous product. Native semantic proofs,
permanent regression, gates and committed-source integrated rebuilding/corpus
verification pass. Source commit: `affb9855665f6cb0cbe1d97a5803ac6efdb50b65`.
Matmult remains19.98x C execution time. **C-or-better across all19 originals is
unachieved. These are not official Embench scores.**

[Summary](evidence/coscientist-loop-high-temp-20261006/summary.json),
[exact timing lineage](evidence/coscientist-loop-high-temp-20261006/timing-lineage.json),
[checksums](evidence/coscientist-loop-high-temp-20261006/checksums.sha256).
Archives preserve native proofs, timed predecessor machines/rows/pins, committed
sources, integrated input contents/hashes, final image, object hashes and actual
per-case outputs.

## Evidence-led implementation

The [unrestricted no-spill prototype](coscientist-high-temp-no-spill-20261006.md)
qualifies on matmult but not SHA-256. Actual SIR shows matmult's high-temp read
inside a repeated backward-branch region; SHA's five high-depth reads are setup
outside loops. Restricting the algorithm to exact loop containment is a general
profitability policy, with no workload/source names. It changes the compiler's
admission, not the benchmark bodies or full19-workload objective.

`gn-high-start` finds the enclosing function within8192 records; a forward scan
looks for a backward branch whose label encloses the original access. It stops
at END or the8192 budget. Label position must be inside the same function, name
must match the branch and the pointed record must be LABEL. Unknown/budget-limited
cases keep the original C path. Prescan/leafness/frame/local allocation remain
original; every admitted access is nonleaf.

The inline sequence stages vector/index in x0/x1, restores x7, executes the original
ordered unsigned handle/index checks and fresh item load, then original result
alias protection. Live prefix x9..x15 and callee-saved locals are disjoint from
x0/x1/x7/x16/x17, so the removed call does not require their call spills. All fuel,
trap ordering and resource/effect behavior remains observable. No checks are
hoisted and no item/result/descriptor cache is introduced. Definition identity
remains content addressing; native DefCID/result-cache integration is separate.

Four native seed generations are byte-identical,812128B with SHA-256
`ae53ccd651e60a4b8489f13efbc06187a21469e3048a97b0876f54a12a673e39`.
Actual observer admits1 original site: matmult SIR3306, temp6. Its guest hash is
`35b9ce6fa5071911882bb3f405ff6da1c16ef79afa75925d4f98ade86bc48abe`.
The observation-only and quiet emitters produce identical guests for all19.
The independent machine audit verifies the complete ordered15-word check/load
sequence at that site and in all33 admitted hand callers.

## Semantic and product qualification

Before product edits,17337 fresh full-state comparisons pass:15840 high-depth
loop-scaffold hand cases,1152 raw-read/nonleaf/deferred-local-alias/join cases,
96 real allocating open imports,40 partial resource writes and209 observations
of all19 original workloads at full/partial fuel. Newly authored enclosing loops
charge their extra backedge fuel in the independent oracle. Calls/aliases/invalid
signed handles and indices/skipped accesses/loops/resources retain exact state.
The raw function has no allocation or call: its high read alone makes it nonleaf,
and its original prologue is verified. The initial fixture author unpacked four
fields; the table has five including depth. Repair preserves depth and all original
expectations. Initial scripts/logs are archived.

Fresh342-fixture/4196-run original regression passes. Permanent authoring appends
60 functions and3793 runs, for402/7989. Every original table entry and expectation
is unchanged. All7989 native result/trap runs pass; real/test code/literal bytes
and function offsets match with2 test-only zero padding bytes. The reviewed
machine golden matches native test output plus `exit=0`, and a normal unit run
passes. Unit guards cover actual loop, cold refusal, scan limits, wrong label
record and foreign target. New Kotoba algorithm and hand-fixture authoring is a
one-off exception to mechanical AST refactoring.

ERR and G1–G5 pass. Gate seed0/1/2 are explicitly mapped to current-source native
fixed generations2/3/4, not mislabeled as stage-0 builds. G2 retains65 equal and
1 known refusal; G3 retains300 cases/233 refusals/67 accepts. G5's interposer
canary catches spawn/fork/exec, loads in60 seed commands and records no guest
program starts. Final bootstrap inventory is byte-identical to before the change;
only a newly generated task Python cache needed removal.

Committed-source integrated generations1/2/3 have162 equal objects,117 frontend
objects and byte-identical command/container/native code. The final command is
6092664B, SHA-256
`91183541af8c28227b23e1105c28dc7b9d06c51d3d97870794eccc115b0b2227`.
All19 source check/compile paths emit exactly the proven guest hashes/offsets.
Against the previous qualified affine-reader image, all391 check,391 compile and
891 export classifications/exits/outcomes match. Additionally, full normalized
check messages and1780 actual native export output/status files match;1 existing
missing export remains. Normalization only sorts unordered checker sets and
substitutes the temporary parity directory prefix. Existing15 closure-handle
host differences remain; no new timeout or difference. External input bytes are
snapshotted and checked, not inferred merely from repository HEADs.

No launcher switch, rung-record update, wire20 grant or100% selfhost claim occurs.

## Immutable machine timing lineage

Apple M4 zebulun, original workloads and pinned C/runner/spec. The preceding
no-spill candidate was measured prospectively after native preflight:30 accepted
rotating product/candidate/C triples,30 attempts for matmult. The unchanged rule
requires load<=4, idle>=90%, adequate interval, relative SD<=10%, ratio>=1.05 and
mean gap>summed SD. It qualifies: gap3339.22ns >2190.38ns summed SD.

| Workload | Previous product ns/body | New product ns/body | C ns/body | Shorter time |
|---|---:|---:|---:|---:|
|matmult-int|21789.78|18450.55|923.36|15.32%|

The restricted compiler emits the same complete guest bytes, offset and source
hash as that measured candidate. The receipt keeps its actual timed compiler
identity; it is not rewritten to claim the later compiler was timed. A separate
lineage proof pins both compiler generations and exact guest equality. Identical
machines are not retimed to seek a pass. Other18 guests equal previous product;
no fresh all19 aggregate score or compile-time improvement is claimed.

## Next registered hypothesis

Actual native census finds high expression temps with unused callee registers in
huffbench/matmult/md5/SHA/slre/UD. Test using those registers while saving them in
the original high-temp home slots, keeping original frame size/local allocation.
This needs independent disjoint-storage/callee/tailcall/RET2/call/alias/branch/
resource/fuel proofs and fresh timing of every changed original guest. Static
counts do not measure time. The full19-workload C-or-better goal remains active.

[Next hypothesis](evidence/coscientist-loop-high-temp-20261006/next-hypothesis.json).
