# Compound scalar specialization: qualified semantics, rejected performance

The native SIR dump proves the actual dependency chain: signed-16 narrowing,
multiply by the second parameter, +128, the wrapped negative-floor helper with
divisor 256, and signed-16 narrowing again. Unlike the earlier isolated floor
experiment, narrowed input and an adjacent known factor with |factor|<=4095
bound the intermediate magnitude below 134 million. There is no i64 overflow;
the exact source quotient therefore equals arithmetic shift by 8 in this domain.
This is a range proof over the complete chain, not an unconditional floor rewrite.

The prototype checks the complete compound SIR body and both dependency bodies,
every opcode and A/B/C operand, branch/join labels, natural parameter loads,
return/end and optional entry FUEL. Names do not enter admission. Both narrowing
calls must reference the same proved signed-16 function. Require the factor in an
immediately preceding CONST; absent identities, other dependencies, changed bias,
dynamic factors, |factor|>4095 and RES2 keep the previous path.

The admitted chain has no effect, allocation or possible arithmetic trap.
Its original optional charges (compound, narrowing twice, quotient: zero through
four) execute individually before its private arithmetic. Fuel exhaustion still
occurs with the same consumed budget and context state. No charge is deleted.
Emit signed narrowing, materialized factor, multiply, bias, arithmetic shift,
and signed narrowing; constant inputs fold the identical expression. Existing
local protection, result coalescing and high temporary homes remain. This is
one-off new compiler algorithm authoring, not mechanical refactoring.

All four native generations match, 830,824 bytes, SHA-256
`b02d380a7a7b782c76f62caaf30bf68649919951a80a71b780a8b3d0f33aeacd`.
All 19 canonical workloads preserve representative results, exact consumed fuel
and exhaustion behavior. Picojpeg is the only changed binary; the other 18 are
byte-identical. The complete 8,192 workspace cells after one/two bodies match.
No canonical source, product compiler or golden fixture is changed.

Independent handwritten SIR verification passes 2,814 executions across 241
fixtures, with identical real/test layouts. All eight combinations of original
entry charges, negative/zero/positive admitted factors, +/-4096 fallbacks,
MIN/MAX, narrowing and division boundaries, constants, high temporaries and
insufficient fuel are covered. Four admitted caller instruction audits show no
BL, direct B or SDIV; an out-of-range caller retains its direct callee branch.

Signed native-loader source probes pass 3,724 actual guest comparisons over 19
exports and 28 signed inputs at seven positive fuel budgets. The original
wrapped source oracle also covers a MAX factor whose multiplication can overflow
and must fall back. Another 322 comparisons deliberately change a dependency's
mask or negative-division bias, and preserve their distinct source results.
These source probes compare result/trap behavior at positive budgets; their loader
has no consumed counter. Exact counts are separately checked by the canonical
runner. Setup failure never counts as a guest trap.

## Prospective timing decision

All arms are measured anew on quiet zebulun Apple M4, unchanged canonical source,
pinned runner and original C binary: 30 accepted rotating triples, maximum 90
attempts, target 300 ms, minimum 50 ms, load <=4, estimated background idle >=90%,
RSD <=10%. The predeclared acceptance rule is >=5% speedup plus a mean gap above
summed SD. All calibration, accepted/rejected rows and baseline lineage survive.

| Picojpeg | Mean us/body | RSD |
| --- | ---: | ---: |
| Promoted native baseline | 261.432 | 2.66% |
| Compound prototype | 254.158 | 1.60% |
| Original C comparator | 10.887 | 0.97% |

Speedup is 1.02862x, about 2.78% less time. The 7.274 us gap is below summed SD
11.034 us and the 5% threshold. Promotion is rejected; do not resample this
identical candidate for acceptance. Code grows from 45,092 to 45,228 bytes.
Candidate/C time is 23.34547x. C-or-better remains unachieved. These are aligned
whole-body timings, not official Embench scores, formal perfgate qualification,
a new suite mean or computation-result caching.

Local scalar transformations have repeatedly failed to separate from variation.
The next investigation measures native dynamic fuel counts by emitting function
on the complete canonical workload, to locate major execution counts before a
new optimization. One body consumes 222,003 fuel units; this alone does not prove
that fuel is the dominant exclusive time cost. Instrumentation timings cannot be
used as benchmark scores. Preserve fuel, traps and effects in any next candidate.

Evidence: [summary](evidence/coscientist-compound-narrow-20261005/summary.json),
[zero-context prototype](evidence/coscientist-compound-narrow-20261005/prototype.diff),
[native compiler, SIR, fixtures and source probes](evidence/coscientist-compound-narrow-20261005/native-proof.tgz),
[all measurement rows](evidence/coscientist-compound-narrow-20261005/timing.tgz).
