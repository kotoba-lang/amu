# Exact index-write fusion: preserved trap fuel, rejected timing

Native dynamic attribution found 43,008 successful charges in the scalar-index
vector-write wrapper at n=1, versus 2,640 in the previous multiply target.
This prospective hypothesis fuses an exact generic five-parameter chain:
`base + stride*k` with wrapped i64 arithmetic, signed-16 value narrowing, and
a proved in-place vector-write wrapper. It removes call/frame overhead while
keeping the existing handle and unsigned index checks. Names never enter admission.
This is one-off new compiler algorithm authoring, not mechanical refactoring.
The proved original path emits two charges per successful invocation (its own and
the inline writer), so 43,008 checks represent 21,504 calls, versus 2,640 calls
to multiply-idct. The earlier conversational "about 16x more executions" was a
charge-count ratio, not a call-count ratio; actual calls differ by about 8.15x.
The bounded fill loop has nine loop charges per k=0 invocation: 19,440/9=2,160
invocations, each making eight set-lane calls. Thus 17,280 of those 21,504 calls
come from the short fill loop. This derivation is specific to these proved bodies
and the complete successful canonical run, not a general interpretation of the
profiler counters.

Admission checks the complete compound body and both dependency bodies, all
opcodes/A/B/C operands, labels, natural parameter loads, RET/END and optional
entry FUEL. Restrict caller temp base t<=4 for the existing checked-store emitter.
Changed index operation, narrowing width, copying writer, unknown shape/effect,
RES2 or higher argument homes keep the previous call path. Internal arithmetic
results cannot coalesce with the caller's following LSET. High value homes,
constant folding, zero stores and lower live temporaries remain supported.

## Failures that changed the design

The first candidate committed all original charges before the checked write.
At an empty-vector boundary and fuel=3, baseline reports SIGILL while the candidate
also reports budget/fuel. That candidate was rejected before performance timing.
Delaying only the final writer charge repaired this trap kind but still changed
exact reported fuel: at full budget the original boundary trap consumes one
context-visible charge, the candidate two.

The whole original compound function is a leaf: its narrowing and simple writer
calls already inline. All its own/helper charges live in x8 and commit at return.
The surrounding caller is nonleaf because it calls this five-parameter compound.
Inlining changes both classifications unless the optimizer explicitly preserves
this boundary. The final candidate keeps the caller nonleaf, loads reserved x8
for the compound's zero-through-three original charges, performs each original
subs/check/zero-on-exhaustion sequence, and commits x8 only after a successful
checked store. No charge is deleted, no expected trap is loosened, and no resource
or fuel report difference is ignored. Wrapped arithmetic/narrowing is total;
moving its private calculations across these checks introduces no external effect
or possible trap. Failed checked stores leave the original context-visible fuel.

The corrected proof compares the native loader's complete structured supervisor
report, including exact context fuel, resource counts, result/trap status, plus
stderr trap kinds. Earlier source-probe adapters did not enable this report;
the loader itself does support it through KEXE_STRUCTURED_REPORT. Their historical
lack of a consumed counter describes the adapter mode, not a missing loader
capability. Do not upgrade old coverage claims without actually rerunning them.

Two harness failures are also retained: recompile refused an existing output
directory; preserving old results allowed a fresh rerun. An instruction audit
initially expected four UDF bounds traps in a t=5 fallback caller, but that caller
retains only its checked read; the delegated writer contains the other two.
The corrected audit checks the retained direct callee branch plus two caller
checks. This does not relax product behavior; all 2,358 result/trap runs had passed.
Both incorrect compiler candidates and their original evidence are archived.

## Native qualification

Four native generations match at 828,592 bytes, SHA-256
`610935e9f7ef0949da6ad1f44d4c47f1f04120e10eac7b6a4d6b0d273f5431e0`.
All 19 canonical workloads retain representative results, exact consumed fuel
and exhaustion exits. Only Picojpeg code changes; the other 18 are byte-identical.
All 8,192 workspace cells after one/two bodies match. Canonical source, product
compiler and golden fixtures remain unchanged; this is a prototype.

Independent handwritten SIR execution passes 2,358 runs over 257 fixtures, with
identical real/test layouts. All eight combinations of compound/narrowing/writer
entry charges, positive/negative/wrapped indices, signed boundaries, constants,
empty/out-of-range vectors, t=4 admitted high values and t=5 fallback are covered.
Three admitted caller audits retain checked read/write UDFs and no direct callee
branch; the only indirect call is allocation. The t=5 fallback keeps its call.

Signed source probes execute 3,920 actual baseline/candidate comparisons over
20 exports, 28 full-i64 inputs and seven positive budgets. Full-budget success
values are independently calculated; invalid cases require SIGILL. Results,
exact fuel, complete resource reports and trap kinds match. Deliberate wrong
index/narrowing/writer dependencies retain their distinct results. An additional
288 handwritten baseline/candidate supervisor comparisons cover every charge
combination, insufficient fuel, successful/empty/bad writes, constants and high
homes. Setup failures never count as guest traps. This stronger comparison caught
both initial compiler defects that exit-code-only parity would have missed.

## Prospective timing decision

All arms are freshly measured on quiet zebulun Apple M4, unchanged canonical
source, pinned runner and original C: 30 accepted rotating triples, maximum 90
attempts, target 300 ms, minimum 50 ms, load<=4, estimated background idle>=90%,
RSD<=10%. Require >=5% speedup and mean separation above summed SD. All calibration
and measurement rows, rejected rows and baseline lineage are retained.

| Picojpeg | Mean us/body | RSD |
| --- | ---: | ---: |
| Promoted native baseline | 261.042 | 2.23% |
| Exact index-write candidate | 251.358 | 1.95% |
| Original C | 10.760 | 0.76% |

Speedup 1.03853x is about 3.71% less time. The 9.684 us gap is below 10.724 us summed
SD and below the 5% threshold. Reject promotion; do not retime identical code to
seek acceptance. Code grows 45,092->45,884 bytes. Candidate/C time 23.36062x;
C-or-better is unachieved. This is an aligned whole-body comparison, not an official
Embench score, formal perfgate qualification, new suite mean or cached computation.

## Next hypothesis: a bounded checked-write loop

Short fill loops repeatedly call this compound and repeat the same handle/index
validation. Prove the complete loop/backedge/parallel-parameter SIR and its
immutable descriptor/dependencies. Runtime guards should prove all remaining
indices valid before taking a fast path; otherwise enter the original loop
before any mutation or charge. A conservative initial domain is bound 8,
0<=k<=8, valid handle, 0<=base<len, stride>=0 and
`stride <= (len-1-base)>>3`. This stronger condition ensures even base+8*stride
fits, so every used base+0..7*stride is valid without wrapped overflow.

Retain each original loop-entry/backedge charge, including the terminal iteration,
and every helper charge/commit after each successful write. Do not batch or defer
context-visible fuel across iterations. Remove repeated descriptor/bounds loads
and call frames only under the proved guard. No allocator, callback or unknown
effect is admitted in the fast region. This larger-loop candidate is unimplemented;
it needs the same native semantic gates and fresh full-body performance comparison.

Evidence: [summary](evidence/coscientist-index-write-20261005/summary.json),
[prototype](evidence/coscientist-index-write-20261005/prototype.diff),
[native source, failed candidates, fixtures and exact reports](evidence/coscientist-index-write-20261005/native-proof.tgz),
[all timing](evidence/coscientist-index-write-20261005/timing.tgz),
[next registered hypothesis](evidence/coscientist-index-write-20261005/next-hypothesis.json).
