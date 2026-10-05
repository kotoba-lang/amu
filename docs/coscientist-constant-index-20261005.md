# Reject constant-index immediate checks for Picojpeg performance promotion

Following the cumulative-phase diagnosis, test a generic exact specialization of
checked vector accesses. A constant index in 0..4095 can compare unsigned length
against an immediate and add that immediate to the vector offset, avoiding the
index's temporary-register materialization. `length > index` unsigned is the same
predicate as the previous `index < length`. The handle check, bounds trap, fuel
and result/local preservation remain. Dynamic, negative and larger constant
indices keep the old route. No benchmark name is inspected, and the canonical
sources are unchanged. This is one-off new compiler algorithm authoring, not a
mechanical source refactor. The prototype stays outside product source.

The experiment was registered before timing. Native seed generations 2/3/4 are
identical, 817,568 bytes, SHA-256
`1a704bad9f2494239e0a73b4584c0ff8a23909a192f34ba0f5ad4e5d313f46f6`.
All 19 canonical workloads match the promoted sign-extension seed's representative
results, exact fuel consumption and fuel-exhaustion trap exits. Another 1,448
source comparisons cover zero-length and exact-boundary vectors, indices -1/0/1/
31/32/255/256/1400/4094/4095/4096, writes, alias-visible writes, deep temporary
expressions, invalid handles and positive fuel boundaries. Successful full-fuel
results have independently calculated expectations. All 8,192 workspace cells
from Picojpeg after one/two bodies match the promoted seed.

The SIR harness adds 60 handwritten fixtures, including admitted immediate bounds,
negative/4096 fallback, temp depths 0/4/5/7 for reads and 0/4/5 for stores, zero
and nonzero stored values, and two-charge success versus one-charge exhaustion.
All 1,014 executions across 217 fixtures pass hand-computed expectations. Test
and real layouts are identical. Twelve instruction audits find the exact
`cmp x16,#index; b.hi +2` sequence once for each admitted read. The fixture golden
and product source are not changed. No correctness outcome is relaxed.

The pinned zebulun Apple M4 runner resamples baseline/candidate/C anew with the
existing prospective policy: rotating order, 30 accepted triples, fixed limit
90 attempts, target 300 ms, minimum 50 ms, load <=4, estimated background idle
>=90%, arm RSD <=10%. Promotion requires >=5% speedup and a mean gap exceeding
summed standard deviations. All calibration/rejected rows and baseline lineage
are saved.

| Picojpeg arm | Mean us/body | RSD |
| --- | ---: | ---: |
| Promoted native sign-extension compiler | 260.473 | 3.16% |
| Constant-index prototype | 258.854 | 2.64% |
| Unchanged C comparator | 10.745 | 1.06% |

Speedup is 1.00625x, about 0.62% less time. The mean gap of 1.619 us is also below
the summed SD of 15.079 us. This rejects performance promotion. Code shrinks
from 45,092 to 44,616 bytes, but smaller code is not a demonstrated speed win.
Candidate/C is 24.09025x; C-or-better remains unachieved. These are aligned
whole-body timings, not official Embench scores. Fifteen workload binaries
change, four are byte-identical; there is no new full-suite timing mean and no
performance inference for the other fourteen changed workloads.

Do not repeat these measurements to fish for acceptance. Keep the promoted
sign-extension production compiler/integrated image. The next larger hypothesis
is straight-line reuse of a checked vector descriptor: code currently repeats
handle-table pointer reconstruction even when several reads use the same vector.
Admit only unchanged proven local handles/context, invalidate at local replacement,
control-flow joins and unknown effects/calls, and retain each index bound check.
A scratch-register reservation must be justified against local/argument/fuel
register allocation, not assumed from a register name. This is unimplemented;
raw SIR/source hashes still do not establish a native typed-definition CID bridge.

Evidence: [summary](evidence/coscientist-constant-index-20261005/summary.json),
[registered hypothesis](evidence/coscientist-constant-index-20261005/hypothesis.json),
[prototype patch](evidence/coscientist-constant-index-20261005/prototype.diff),
[native proof](evidence/coscientist-constant-index-20261005/native-proof.tgz),
[all timing rows](evidence/coscientist-constant-index-20261005/timing.tgz).
