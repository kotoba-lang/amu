# Direct affine-index checked read: qualified native improvement

The current native compiler composes an exact affine index and immediately
consuming vector read, eliminating intermediate homes and result copies while
retaining original handle/index checks. Original matmult time is13.12% shorter
in one fresh30-triple comparison, passing unchanged variation/profitability rules.
Other18 guest bytes equal the previous qualified product. C remains16.97x faster
than this candidate; all19 C-or-better goal is unachieved. These are aligned native
body measurements, not official Embench scores or a new suite aggregate.

Source `8b147965a4e32036eaf8de71805a2f8be95cfc69`; integrated command6092664B,
SHA-256 `54b2c9765e19524e875c9196e7d86c2f296117144a6c1c9c431af177b4eeea00`.
[Summary](evidence/coscientist-affine-read-direct-20261006/summary.json),
[timing](evidence/coscientist-affine-read-direct-20261006/timing-summary.json),
[checksums](evidence/coscientist-affine-read-direct-20261006/checksums.sha256).
Archives retain raw measured rows/C/runner/spec, actual source/guest binaries,
all native generations, oracles/full-state receipts, initial untimed variant,
authoring failures/corrections, new permanent fixtures and committed-source
integrated rebuild/corpus actual outputs.

## Exact implementation and native proof

Admission uses six exact LGET/CONST/integer-MUL/LGET/integer-ADD/integer-ADD records,
then RT-VECTOR-AT at high-2 with two arguments. Require original nonleaf frame,
high>=7, valid resident local sources, prefix constant[-4095,4095], nontrivial
factor, validated same-function loop and bounded dead-intermediate/index proof.
Unknown structures, live index, absent loop and unknown ownership refuse.
No workload/function names, result cache, callee allocation or scalar-tree state14
changes. Existing gn-protect/gn-co/gn-dreg/gn-fin preserve aliases and final placement.
Every handle/index validation and fuel/allocating effect remains in original order.

All4 native generations byte-match814312B,
SHA-256 `a9cceee002d6365f3e68b740321b9e362635121bd575b613ac28d4b3da93372e`.
Actual observer/quiet guests and entry offsets equal for all19. Only2 actual sites,
original matmult SIR3291/3300, emit exact MADD/immediate arithmetic and read directly
into original x14/x15. Original192B frame and5-local prologue are byte-preserved.
Matmult machine10328→10280B. The initial10288B read-composition variant still moved
results from x0; it passed semantics but was never timed. Final direct variant
has independent native generations/proofs and differs from all rejected machines.

Original402 fixtures/7989 native runs pass unchanged expectations before timing.
4950 independent modular-arithmetic/index/alias/coalescing/live-index-RET2 refusal/
cold/nontrivial-factor/prefix-range/fuel states,1260 actual allocating-open-import/
invalid-handle/index/resource partial-write states,2520 additional source-operand
and handle-alias states, and209 complete original19 states pass. Total8939 sealed
before timing. Actual MADD admission/counts are audited for every new hand case.

Permanent fixture table grows to434/9339, preserving the exact402/7989 prefix.
New pure hand expectations cover integer extremes, invalid handles/indices,
partial fuel, source/handle aliases and refusal.12 independently constructed
native guard states cover admission, leaf/frame-slot/unknown-prefix/range refusal,
reserved fields, invalid locals, wrong read slot/depth/arity and wrong label.
Real/test layouts and normal unit stdout match independent fixture image; update
generated golden only after9339 actual runs pass, then normal native unit passes.
Initial loader-copy mode, test table-name, Python namespace and unit allowed-path
failures are corrected without changing program limits or prior expected results.
This is new Kotoba algorithm/hand-fixture authoring, not mechanical refactoring.

## Fresh timing and complete product checks

Apple M4 zebulun, pinned original source/C/runner/spec.30 accepted rotating triples
of31 attempts. Independent audit recomputes every rejection/order/mean/SD and
verifies source/machine/compiler/offset/C/runner/preflight pins. Load<=4,
background idle>=90%, allRSD<=10%, speedup>=1.05 and gap>summedSD.

|Original workload|Product µs/body|New µs/body|C µs/body|Shorter time|
|---|---:|---:|---:|---:|
|matmult-int|18.008|15.645|0.922|13.12%|

Gap2363.41ns > summedSD2216.84ns; ratio1.1511.
No identical-machine retiming or result memoization. No newall19 geometric mean.

ERR/G1–G5 pass under explicit native-generation mapping; G2 retains its existing
one refused corpus case, with0 changed accepted outputs. Bootstrap inventory is
byte-identical. This is six gates, not all release gates. Commit-snapshot integrated
image/command/container/native code and all162objects match across3generations,
with117frontend objects and input content hashes verified. Generation3 checks and
compiles all19 canonical sources, yielding exact measured guest bytes/entry offsets.

All391 check classifications/messages and391 compile outcomes retain previous
qualified results; all891 export classifications retain875same,15existing closure
handle differences,0timeouts and1missing. All391 normalized actual check messages
and1780 native export output/status files equal previous product. Existing compile
counts remain300behavior-same,27Amu-only accepts,12Amu-only refusals,3differing
accepted behaviors,49shared refusals. These gaps remain explicit; no100%selfhost,
launcher switch, rung-record update, wire20 grant, merge/main or release claim.

## Next registered hypothesis

[Guarded descriptor reuse after elimination of the high-read C boundary](evidence/coscientist-affine-read-direct-20261006/next-hypothesis.json).
A prior descriptor cache was invalidated by the adjacent high-depth C helper.
Current qualified loop reads remove that boundary. Restrict a new experiment to
structurally witnessed high-inline loops, retaining all index checks and actual
call invalidation, then prove/measure a distinct machine. Native DefCID/result
caching remains unconnected; this local specialization uses exact SIR content.
