# Loop-produced high-temp registers: rejected experiment

Native materialization evidence narrows register allocation to dynamic arithmetic
inside actual backward regions. Only1 original function/2 temps are admitted;
other18 guests equal current product. The new machine passes semantics but its
fresh30-triple timing still fails the unchanged variation criterion. Reject it;
current qualified product stays at `affb9855665f6cb0cbe1d97a5803ac6efdb50b65`.
C-or-better across all19 remains unachieved. These are not official Embench scores.

[Summary](evidence/coscientist-loop-temp-registers-20261006/summary.json),
[raw timing summary](evidence/coscientist-loop-temp-registers-20261006/timing-summary.json),
[checksums](evidence/coscientist-loop-temp-registers-20261006/checksums.sha256).
Archives preserve actual source/unity, native generations, observations/guest
machines, guard failure repairs, independent state oracles, pinned C/runner/spec
and all accepted/rejected measurement rows.

## Native implementation and proof

A bounded function scan accepts a non-coalesced high integer ADD/MUL result from
adjacent LGET/CONST producers only within a validated same-function backward
region. Trivial constants0/1/-1 refuse. Highest admitted temp bounds a contiguous
mapped range; original local allocation/frame/outgoing area remain unchanged.
Added callee registers save/restore in the original mapped temp homes. Existing
state14 tree flag is untouched. There are no source/workload names or result
caches. Experimental Kotoba algorithm and independent hand-fixture authoring are
one-off exceptions to mechanical refactoring; product source stays unchanged.

Generation1 is813824B. Native generations2/3/4 are byte-identical813816B, SHA-256
`74ee0950a44723c45266e3ccca51326c7b658d8a28d0b04c4d9a813c0829bfb4`.
Actual native observation and exact guest/entry equality admit only matmult FN5,
temps7/8 in x24/x25. Independent instruction audit verifies original frame and
one exact save/restore each at disjoint backup offsets80/72. Candidate10308B
machine differs from rejected10316B three-register machine; no identical-code
retiming. All18 other guest bytes equal current product.

All402 permanent fixtures/7989 native runs pass unchanged expectations/golden,
with real/test code/literals/function offsets equal.750 independent deep-expression
full-state comparisons now explicitly enclose producers in one-iteration loops,
including extra backedge fuel in the oracle. Depths8/10/17/31/63, caller locals
occupying all10 callee registers, nested calls, tail calls, RET2/RES2, joins, leaf
bodies, allocating calls and partial fuel pass with actual added save/restores
independently verified for all30 new cases.96 real allocating open imports,
40 resource exhaustion/partial-write comparisons and209 full/partial-fuel states
of original19 pass:1095 additional state comparisons before timing.

Nine fresh native guard checks cover actual hot admission, cold/constant/trivial/
coalesced refusal, zero budget, wrong label record, foreign label position and
wrong function start. Failure sum is bounded0..9; command exit0 proves all pass.
Initial proof authoring duplicated the standard main wrapper, then expected
scalar stdout from command mode. Correct the proof to define seed-main and use
its bounded failure exit; compiler/guard expectations unchanged. Initial scripts
and failures remain archived. Source/goldens/launcher/rung/wire grants unchanged.

## Fresh timing and rejection

Apple M4 zebulun, original matrix/source and pinned C/runner/spec.30 accepted
rotating current-product/new-candidate/C triples of33 attempts. Independent audit
recomputes every mean/SD/order/rejection and verifies source/machine/offset/C/
runner/native preflight pins. Load<=4, background idle>=90%, intervals sufficient,
allRSD<=10%. Promotion also needs ratio>=1.05 and meanGap>summedSD.

|Original workload|Product ns/body|Candidate ns/body|C ns/body|Shorter time|Qualifies|
|---|---:|---:|---:|---:|---|
|matmult-int|18027.76|16232.95|923.93|9.96%|No|

Mean gap1794.81ns is below summedSD2153.23ns.
Candidate/C execution-time ratio is17.57. No speedup adopted,
no freshall19 aggregate, no gates/integration rerun for rejected source.

## Next registered hypothesis

Current native SIR has two closed high-depth affine expressions with known prefix:
local*constant+local+prefix. Existing enc-madd can compose their arithmetic and
avoid intermediate homes without extra callee saves. Validate exact integer
shape, local mappings, actual prefix descriptor, same-function loop, bounded
liveness (including future RET2/read refusal), aliases/coalescing and final skip
bookkeeping before a new machine. Structural matches are not admission or
measured time shares. [Next hypothesis](evidence/coscientist-loop-temp-registers-20261006/next-hypothesis.json).
