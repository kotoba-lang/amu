# Checked-vector descriptor reuse: two negative execution experiments

Cumulative Picojpeg diagnosis prioritized transform execution. The constant-index
experiment then failed promotion. This wave tests two generic descriptor-reuse
algorithms in the native selfhost compiler. Both retain canonical benchmark
sources and the existing promoted sign-extension production compiler.

## Exact admission and invalidation

A checked vector access resolves a handle to its descriptor; the next access
normally repeats that resolution. Cache the descriptor pointer in x6 only when
the handle is a proven local and x6 is free: non-leaf functions store their
locals outside argument registers, or a leaf has fewer than seven local slots.
The original first handle check remains. A cache hit restores x16 from x6; each
access still loads the descriptor and performs its own unsigned index/length
check, bounds trap and item lookup. Vector element values are never cached.
Fuel charging and high-temp fallback remain unchanged. No ABI or context layout
change is made. No use of platform-reserved x18 is introduced.

The cache is invalidated at labels, branches, comparisons (including fused
branches), unknown operations/effects/calls and replacement of the tracked
local. Results coalesced directly into that local also invalidate it, including
when the following LSET is consumed. Writes to vector elements can reuse the
unchanged descriptor, but each write checks its index and a later read observes
the new element. Heap metadata mutation or allocation is not admitted across a
cache boundary. The generator's per-function zeroing resets the cache state.

VD-1 invalidates every source CALL. VD-2 retains it across CALL only when the
existing exact SIR matcher certifies an actually inlined sign-extension,
identity, vector-at or vector-assoc-in-place wrapper. Genuine and unknown calls
still invalidate it before argument-register setup. The sign wrapper's original
optional entry fuel remains charged. Neither algorithm uses benchmark names or
unverified source/hash equivalence. These are one-off new compiler algorithm
prototypes, not mechanical product refactors or a native DefCID bridge.

## Native correctness evidence

Each prototype reaches three byte-identical native generations (2/3/4).
VD-1 is 820,200 bytes; VD-2 is 817,328 bytes. Exact hashes are in the summary.
All 19 canonical workloads retain representative result values, exact fuel
consumption and fuel-exhaustion exit behavior. Both compare all 8,192 Picojpeg
workspace cells after one/two bodies with the promoted native seed.

VD-1's 912 hand-computed SIR runs across 169 fixtures pass. VD-2's 914 runs
across 171 fixtures add a certified sign wrapper between accesses and test its
entry-fuel boundary. Cases cover alias-visible mutation, explicit local
replacement, coalesced replacement, an actual seven-argument call clobbering x6,
branch joins, repeated loop entry, high operands and an out-of-bounds second
read after a valid first read. Real/test layout bytes and offsets match.
Instruction audits find descriptor capture and repeated hits in `desc_reads`,
and no capture/hits in a seven-local leaf where x6 belongs to a parameter.
VD-2 audits reuse across the inlined sign wrapper too. Product fixture goldens
are untouched, and no expectation is weakened.

VD-2 additionally passes 1,448 source-level baseline/candidate comparisons over
zero-length/exact-boundary vectors, negative/large indices, alias-visible writes,
deep temporary expressions, invalid handles and positive fuel boundaries. Valid
full-fuel outputs have hand-calculated expectations, alongside exact fuel and
trap parity. The first probe runs at the SIR level are not presented as this
additional source suite.

## Prospective timing decisions

Each distinct algorithm has its own registered hypothesis before measurement.
The fixed zebulun Apple M4 runner resamples baseline/candidate/C freshly for each
experiment: rotating order, 30 accepted triples, maximum 90 attempts, target
300 ms, minimum 50 ms, load <=4, estimated background idle >=90%, RSD <=10%.
Promotion requires >=5% speedup and a mean gap above summed standard deviations.
All calibration and measured rows, including any rejects, are retained.

| Experiment | Baseline us/body | Candidate us/body | C us/body | Speedup | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| VD-1, every CALL invalidates | 260.413 | 263.191 | 10.783 | 0.98944x | Reject |
| VD-2, certified inline wrappers retained | 260.136 | 257.786 | 10.765 | 1.00911x | Reject |

VD-1 is slower at the observed means; VD-2's approximately 0.9% time reduction
is below the 5% threshold and its 2.349 us mean gap is below 11.652 us summed SD.
No improvement is confirmed. Code sizes are 45,076/44,852 versus baseline 45,092
bytes; size changes do not prove execution gains. Candidate/C ratios are
24.4074/23.9470x. These aligned whole-body experiments are not official Embench
scores, do not establish C-or-better performance, and yield no new full-suite
geometric mean. Keep the negative results without repeating identical candidates
to fish for promotion. Production source/integrated image remain unchanged.

## Next hypothesis

Current direct self-tail-calls restore the function frame and branch to the
callee entry, which reconstructs the same frame and parameter homes. Replace a
proven scalar direct call to the same function followed immediately by its RET
with rebinding the new arguments inside the existing frame, then branching to
its body entry. Initial admission should exclude stack arguments and multi-result
returns. Evaluate every argument before rebinding to preserve parallel swaps,
retain the caller's original saved registers/return address until the eventual
return, and execute the original entry fuel on every iteration. Other calls
retain the existing route. Frame reuse is an unimplemented hypothesis; it must
pass permutation/high-temp/fuel/exhaustion tests and fresh canonical C comparisons.

Evidence: [summary](evidence/coscientist-vector-descriptor-20261005/summary.json),
[VD-1 prototype](evidence/coscientist-vector-descriptor-20261005/vector-descriptor.diff),
[VD-2 prototype](evidence/coscientist-vector-descriptor-20261005/vector-descriptor2.diff),
[VD-1 native proof](evidence/coscientist-vector-descriptor-20261005/vector-descriptor-native.tgz),
[VD-2 native proof](evidence/coscientist-vector-descriptor-20261005/vector-descriptor2-native.tgz),
[VD-1 timing](evidence/coscientist-vector-descriptor-20261005/vector-descriptor-timing.tgz),
[VD-2 timing](evidence/coscientist-vector-descriptor-20261005/vector-descriptor2-timing.tgz),
[source probes](evidence/coscientist-vector-descriptor-20261005/source-probes.tgz).
