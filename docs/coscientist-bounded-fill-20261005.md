# Bounded vector-fill specialization

The [content/computation identity investigation](coscientist-content-address-20261005.md)
distinguishes canonical checked-definition CIDs from an invocation recipe and
from native artifacts. This experiment applies content/structural knowledge to
fresh native execution. It does not connect DefCID to the seed or cache results.

## Registered hypothesis and implementation

The preceding [index-write experiment](coscientist-index-write-20261005.md)
found a larger optimization opportunity in exact bound-8 fill loops. Dynamic
fuel counters identify repeated index/sign/write calls; counts of charges are
not timings or necessarily call counts. The prototype proves all SIR operations,
labels, parallel parameter updates and all called sign-16/in-place-writer bodies.
It recognizes no function names. Unknown shapes, callbacks, allocation or effects
are not admitted. This is one-off compiler algorithm authoring rather than a
mechanical source refactor; no existing AST rule implements it.

The native fast region validates the vector handle before touching its descriptor,
then guards `0 <= k <= 8`, `0 <= base < len`, nonnegative stride, and
`stride <= (len-1-base)>>3`. This conservative proof keeps even base+8*stride
inside the allocation and prevents index arithmetic overflow. It derives the
pointer once and emits sign extension, scalar writes and pointer increments.
Every guard failure enters the unchanged original SIR loop before charge/write.
There are no direct/indirect helper calls in the fast region. The old loop's
optional entry fuel, every helper charge/leaf commit, and each backedge charge
(including the last iteration) remain at the original observable boundaries.
No context-visible fuel is deferred across iterations.

## Native proof

Generations 2/3/4 are byte-identical, 836,448 bytes, SHA-256
`d436b00211cd60f34dff5118a8f767aa36ad414d795870d0c3fb6e185c702a11`.
All 19 canonical sources preserve representative results, exact consumed fuel
and exhaustion exits. Only Picojpeg machine code changes; the other 18 binaries
are byte-identical to the current sign-extension product compiler. Picojpeg's
complete 4,096-cell arenas after one and two bodies match (8,192 cells).

All 2,006 native SIR executions pass (377 fixtures). Real/test emitted layouts
match; three instruction audits confirm fast paths contain no BL, BLR or UDF,
with one helper BL retained on each fallback. All 4,130 signed source comparisons
and 6,912 handwritten baseline/candidate comparisons match exact supervisor
reports, results, resource counts, fuel, signal/budget trap reports and all
small owned vector arena cells, including partial writes on exhaustion. Tests
cover all 16 combinations of loop entry and optional helper charges, signed
extremes, valid terminals, guard fallbacks, invalid handles and bounds.

The first invalid-last test had an arithmetic oracle error: length 16, base 1,
stride 2 writes indices 1,3,...15, all valid, so both compilers correctly succeeded.
The handwritten suite initially passed 1,990/2,006 cases; its 16 failures shared
that bad expectation. Original tests/failure are preserved. Changing the test
length to 15 makes index 15 invalid; it traps identically. No compiler behavior
or genuine trap expectation was relaxed to pass the tests.

## Measurement and decision

On authorized zebulun (Apple M4), all three arms are freshly measured using the
pinned original C comparator and canonical source. Thirty rotating triples
satisfy the existing quiet-host and duration rules: load <= 4, background idle
>= 90%, RSD <= 10%, 300 ms target interval, 50 ms minimum and fixed 90-attempt
limit. The promotion rule was declared before timing: speedup >= 1.05 and mean
gap greater than summed standard deviations. All calibration/attempt rows remain.

| Picojpeg arm | Mean us/body | RSD |
| --- | ---: | ---: |
| Current native selfhost product | 259.047 | 2.83% |
| Bounded-fill prototype | 247.292 | 1.88% |
| C, unchanged comparator | 10.797 | 0.90% |

Speedup 1.04753x and elapsed reduction 4.54% do not meet the declared threshold.
The mean gap is 11.754 us, smaller than the 11.982 us sum of SDs. Reject product
promotion and do not resample identical code to seek a pass. Candidate/C is
22.9034x; C-or-better remains unachieved. Code is 45,340 bytes vs 45,092 in the
product. This is an aligned original whole-body comparison, not an official
Embench score, formal perfgate or a new suite geometric mean.

The experimental backend is archived, not installed in the product. No integrated
image is rebuilt from this rejected candidate; the previously qualified product
and its integrated fixed point remain unchanged. A next execution hypothesis
should target the larger coefficient initialization region and repeated checked
writes, selected from dynamic evidence and preserving exact fuel/trap/state.
DefCID-based compilation/specialization caches need separate cold/warm and
invalidation measurements, as described in the identity investigation; they
cannot be counted as fresh-body execution improvements.

Evidence: [summary](evidence/coscientist-bounded-fill-20261005/summary.json),
[prototype](evidence/coscientist-bounded-fill-20261005/prototype.diff),
[native sources, fixtures, failed oracle and proof](evidence/coscientist-bounded-fill-20261005/native-proof.tgz),
[all timing and baseline lineage](evidence/coscientist-bounded-fill-20261005/timing.tgz).
