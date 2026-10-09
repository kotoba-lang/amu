# Bounded scatter-zero loop specialization

The preceding [scalar-tree optimization](coscientist-scalar-tree-20261005.md)
qualified a Picojpeg improvement and passed integrated fixed-point/corpus proof.
This next hypothesis fuses a whole scatter-zero recurrence with its immutable
threshold-tree mapping dependency and exact in-place writer. It tests repeated
call/descriptor/bounds overhead on the complete original workload; the source is
unchanged. This is new compiler algorithm authoring, not mechanical refactoring.
There is no DefCID integration or result memoization.

## Proof and lowering

The prototype verifies every SIR operation, operand, label, parameter update,
entry charge, backedge and RET/END of the three-argument recurrence. The offset
base must be a constant in 0..4095. The mapping function must be a whole pure
one-argument integer threshold tree, literal leaves, comparisons against 1..63,
depth <=7 and more than 128 SIR instructions. Its labels are resolved inside
its own bounded SIR span, independent of function traversal order. Every value
at 0..63 must be in 0..63; those bounds cover the full signed domain because of
the threshold contract. The writer must be the exact natural-parameter in-place
store, with at most its original optional entry FUEL. Unknown shapes, callbacks,
effects, allocations, nonliteral leaves and values outside the proved range are
not admitted. Function names do not select an optimization.

Runtime guards prove `0 <= k <= end <= 64`, a valid vector handle, and
`length >= base+64` before any charge or mutation. The descriptor/data base is
computed once; a private PC-relative 64-entry table drives scalar zero stores.
Every guard failure enters the original loop before its original entry charge.
The loop's entry and every backedge charge remain, including the last iteration.
An optional mapper charge retains its original x8 leaf transaction: load/check,
pure lookup, then commit, followed by the writer's original charge and write.
There is no fuel batching or deferral across iterations. No new allocation or
callback occurs; immutable descriptors remain valid throughout the fast region.

## Native semantic evidence

Generations 2/3/4 match, 839,080 bytes, SHA-256
`b9607b54e520b8dc06c6a1b3d18b87bd0413e552d7b4ed8bd004642d150c6dee`.
Every canonical workload retains representative results, exact consumed fuel
and exhaustion exits; only Picojpeg's machine code changes. The other 18 binaries
are identical to the qualified scalar-tree product. All 8,192 owned workspace
cells after one/two complete Picojpeg bodies match.

All 3,392 native SIR runs pass (291 fixtures). Test/real emitted layouts agree.
Four independent audits decode the table and check exact values, native indexed
load/zero-store instructions, no direct/indirect calls in the fast region, and a
mapping call retained in each fallback. The forward-dependency fixture verifies
proof does not rely on previous function prescanning. Charged mapper audits also
check the actual load/lookup/commit/write order.

All 2,720 signed source and 3,256 handwritten comparisons match full supervisor
reports, result, fuel, resource counts, trap kinds and complete owned small vector
arenas after success or failure. Test arenas are initialized with nonzero/signed
values so omitted writes cannot hide behind zero initialization. All eight
loop/map/writer charge combinations and every insufficient positive budget through
196 are covered for full fills. Other cases include partial/terminal ranges,
invalid handles, invalid bounds, negative/past-terminal counters, duplicate mapping
values and conservative guard fallbacks. Nearby copy allocation, changed value,
step2, invalid mapping range and out-of-domain thresholds retain their original
behavior and resources.

The first short-valid oracle was arithmetically wrong: `17*i mod64` reaches 63
at i=15, so length79/base16/start0/end63 traps. Both compilers agreed. The corrected
valid fallback starts16 and ends64, excluding i15; genuine out-of-range cases
remain traps. The initial unrolled test setup exceeded compiler region1 capacity
before execution. Shared bounded native SIR setup/checksum loops fit the harness
without removing target cases or altering expected target fuel. Original failed
sources/logs are retained. A later proof audit refined the optional mapper fuel
publication boundary before timing; its preceding passing evidence is also saved.
Final fixed-point/source/SIR/state proofs were rerun. The canonical benchmark bytes
are identical across this refinement because its mapping has no entry fuel.

## Quiet-host measurement and decision

The exact current scalar-tree product is the baseline, verified by binary hash.
All three arms are freshly sampled on zebulun Apple M4 against the pinned original
C binary and canonical source: 30 rotating accepted triples, 90-attempt cap,
300 ms target, 50 ms minimum, load <=4, background idle >=90%, RSD <=10%.
The promotion rule is prospective: speedup >=1.05 and mean separation larger
than summed SDs. Keep all attempted/calibration rows; do not repeat identical
code to seek a pass.

| Picojpeg arm | Mean us/body | RSD |
| --- | ---: | ---: |
| Current native selfhost scalar-tree product | 237.829 | 2.24% |
| Scatter-zero prototype | 233.448 | 2.09% |
| C, unchanged | 10.775 | 1.24% |

Speedup 1.01877x, about 1.84% shorter elapsed time, fails the 5% threshold.
The mean gap 4.382 us is below summed SDs 10.221 us. Reject product promotion.
Candidate/C is 21.6663x; C-or-better remains unachieved. Code grows
43,084 ->43,796 bytes. These are aligned original whole-body times, not official
Embench scores, formal perfgate qualification or a new suite mean. Product source,
fixture goldens, rung pins, `bin/amu` and the qualified integrated image remain
unchanged. No integrated image is rebuilt from this rejected candidate.

## Next registered diagnostic

Dynamic successful-charge counts are not exclusive execution times. After the
small call/bounds hypotheses repeatedly failed performance acceptance, quantify
the fuel lowering contribution with an explicitly non-product diagnostic backend
that emits no OP-FUEL code. Build it natively with the qualified current compiler,
keep every other lowering decision, and use only the known bounded original
Picojpeg body at n0/1/2/17/32. Preserve independent result/arena validation, original
wall/CPU supervision and report the intentional exact fuel difference.

Thirty quiet rotating product/diagnostic/C triples can establish an upper bound
on avoidable fuel code cost. The diagnostic changes observable language behavior
and is unimplemented here: it cannot be promoted, counted as a product speedup,
called an official Embench score or used as C-or-better evidence. A separated
elapsed gap would justify a subsequent register/region fuel design preserving
original exhaustion, trap, partial-state and commit boundaries. Otherwise choose
another cost from measured evidence. No claim that fuel dominates is made yet.

Evidence: [summary](evidence/coscientist-scatter-zero-20261005/summary.json),
[prototype](evidence/coscientist-scatter-zero-20261005/prototype.diff),
[native proof, failures and refinement](evidence/coscientist-scatter-zero-20261005/native-proof.tgz),
[all timing and baseline lineage](evidence/coscientist-scatter-zero-20261005/timing.tgz),
[next diagnostic contract](evidence/coscientist-scatter-zero-20261005/next-hypothesis.json).
