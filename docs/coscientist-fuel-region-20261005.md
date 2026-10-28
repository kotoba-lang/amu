# Sufficient-fuel region experiment: negative result

Follow-up: [cold fuel failure layout](coscientist-cold-fuel-20261005.md) qualifies
eleven improvements across all19 workloads but regresses EDN. Global promotion
is rejected; a generic multiple-site profitability threshold is registered next.

The [fuel-cost diagnostic](coscientist-fuel-cost-20261005.md) separated a20.75%
counterfactual sensitivity to omitted checks. This next registered experiment
keeps the original workload and observable fuel semantics. It proves bounded
straight-line SIR regions, guards sufficient fuel once, and omits only redundant
exhaustion branches on the fast path. **Reject product promotion:** none of the
seven changed workloads qualifies, and Wikisort has a separated regression.
The qualified scalar-tree product and integrated image remain unchanged.

## Native lowering and admission

A region starts at a charged operation. Admission requires at least3 charges,
fewer than128 SIR instructions, and only constants, local loads/stores, scalar
arithmetic/unary operations, FUEL, exact previously admitted inline wrappers,
and already inlined vector/pair operations. Control transfer, labels, comparisons,
returns, unknown calls, handlers and allocation are boundaries. Hitting the cap
refuses the region. Proof uses structure, not function names or benchmark names.

An unsigned pre-entry fuel guard selects either a fast copy or the original
region. Both retain every original decrement, nonleaf context store, leaf commit
and ordinary bounds/division trap. Insufficient fuel enters the original copy
before any charge or mutation. There is no batching or early publication. A
private reusable generator-state snapshot restores metadata/temp descriptors
before lowering the slow copy; local register assignment and labels cannot change
within admission. The compiler workspace grows by65,664 bytes for that snapshot.
This is new compiler algorithm authoring, not a mechanical refactor.

The native seed is built from current product producer SHA-256
`98905d4a7c3da0d94465d99f4b32ae195c2e7972d1b995a3744a0d588595635d`.
Generations2/3/4 match at837,648 bytes, SHA-256
`c7b884a9c7fac37442577c6c052588778966c2a79e9e1684ba16ca29f8bdc602`.
This prototype remains separate from product source.

## Correctness evidence

All19 canonical original workloads match product results and exact consumed fuel
at n0/1/2/17/32, including exhaustion behavior. All8,192 Picojpeg workspace cells
after one/two full bodies match. Seven machine-code binaries change and twelve
are byte identical.

Native test-layout and real-layout emitters agree. The existing1,979 executions
pass; the expanded emitter contains258 fixtures. Audits independently locate34
sufficient-fuel guards, check their exact costs and all fast decrements, and verify
four refused control/unknown-call/allocation/cap neighborhoods. Comparisons cover
leaf/nonleaf contexts, context restoration after a call, charged/uncharged inline
writers, deep/live temporaries, division by zero/overflow, invalid reads/writes,
signed extremes and every insufficient positive budget through each region cost.
All2,776 full supervisor reports and owned partial vector arenas match.

Supplementary proof legally reaches zero fuel at the region entrance by consuming
initial budget1 in a caller. All five caller/callee boundary comparisons match;
the zero-entry guard takes the original exhaustion path. Initial fuel0 itself is
refused by the supervisor and is not counted as an executed test. Supplementary
proof is separate from the already pinned measurement admission files; native
candidate code and timing were not repeated.

The first instruction audit assumed a next-function offset existed for the final
fixture, raising KeyError259 after canonical/native layout checks had passed. The
audit's end bound now uses the exact printed code-word count. The original native
emitters were reused to finish auditing; compiler/candidate code was unchanged.
The failed-audit note and subsequent proof are retained.

## Fresh measurement of every changed workload

All seven changed workloads are measured on zebulun Apple M4 against the exact
current product code and original pinned C binary/runner/matrix. Each gets30
accepted rotating triples, 300ms target, 50ms minimum, load<=4, estimated background
idle>=90%, RSD<=10%, fixed90-attempt cap. All calibration/accepted/rejected rows
and projected baseline lineage are saved. Across7 workloads,210 triples are
accepted from217 attempts. All accepted quiet-host conditions, means and SDs are
independently rechecked from raw rows. No unchanged-code retiming seeks a pass.

| Workload | Product us/body | Candidate us/body | C us/body | Product/candidate |
| --- | ---: | ---: | ---: | ---: |
| Picojpeg | 235.717 | 236.380 | 10.794 | 0.99720x |
| MD5 | 13.815 | 13.896 | 2.494 | 0.99416x |
| QR | 273.736 | 277.169 | 21.605 | 0.98761x |
| sglib | 41.070 | 40.798 | 5.806 | 1.00669x |
| slre | 7.898 | 7.793 | 1.036 | 1.01356x |
| tarfind | 14.256 | 14.202 | 1.006 | 1.00385x |
| Wikisort | 210.740 | 236.428 | 15.173 | 0.89135x |

No workload meets >=1.05 improvement plus a gap larger than summed SDs. Wikisort
is12.19% slower:25.688us gap versus summed SDs14.825us. Other differences do not
clear the separation rule. Picojpeg candidate/C is21.8996x. C-or-better remains
unachieved; these are aligned complete original workload timings, not official
Embench scores, formal perfgate qualification or a new full-suite aggregate.
Correctness parity and fixed points do not substitute for performance acceptance.

## Next registered experiment

Use the qualified product as baseline. Keep every fuel checkpoint, decrement and
context/leaf publication point; test a fall-through success path with B.LO into
cold failure code, replacing taken B.HS over inline trap instructions. Share cold
failure code only where branch distance and context/register contracts are proved.
Do not duplicate the computation body or precharge/defer any consumption. Unknown
layouts retain original emission. Require native fixed point, all19 canonical
checks, full state/trap proofs and fresh timing for every changed workload before
promotion. This hypothesis is registered, not implemented or qualified here.

Evidence: [summary](evidence/coscientist-fuel-region-20261005/summary.json),
[prototype diff](evidence/coscientist-fuel-region-20261005/prototype.diff),
[native proof and failures](evidence/coscientist-fuel-region-20261005/native-proof.tgz),
[all seven comparisons](evidence/coscientist-fuel-region-20261005/timing.tgz),
[independent row audit](evidence/coscientist-fuel-region-20261005/timing-audit.json),
[next hypothesis](evidence/coscientist-fuel-region-20261005/next-hypothesis.json).
