# Unused callee registers for high expression temps: rejected experiment

All six changed original Embench guests fail the unchanged prospective promotion
rule. Keep the qualified loop-contained high-read product at source commit
`affb9855665f6cb0cbe1d97a5803ac6efdb50b65`; no product algorithm/golden/launcher
change. C-or-better across all19 originals remains unachieved. These are aligned
native body timings, not official Embench scores.

[Summary](evidence/coscientist-callee-temp-20261006/summary.json),
[raw timing summary](evidence/coscientist-callee-temp-20261006/timing-summary.json),
[checksums](evidence/coscientist-callee-temp-20261006/checksums.sha256).
Native/timing archives contain scripts, source/unity, four native generations,
actual machines, full observations, per-case outputs, C artifacts, original
source/runner/spec pins and all accepted/rejected timing rows.

## Hypothesis and native proof

Use x19..x28 left unused by original local allocation for canonical expression
temps7+, keeping the original frame and local allocation. Save/restore added
registers in their original temp home slots; those mapped homes hold caller
backups and cease to store expression values. Low caller-register call saves
stay unchanged. New experimental Kotoba algorithm authoring is a one-off hand
exception; no mechanical refactor rule covers it. Product source is unchanged.

Generation1 is812776B. Generations2/3/4 are byte-identical813176B, SHA-256
`a9dfcc6c1dce58679782baf40b5d73d88126c5ffef008b60a5038187aee8aa82`.
Fresh native observation on all19 compiles identifies14 admitted functions across
six workloads and proves observer/quiet guest bytes/entry offsets equal. Every
register backup offset is disjoint from original callee saves; original frame
sizes stay unchanged. Independent native instruction audits check exact added
save/restore instructions on30 new deep-expression cases.

All402 permanent fixtures/7989 runs pass with existing expectations/golden
unchanged and real/test code/literal/entry layout equal. Additional750 independent
full-state comparisons cover depths8/10/17/31/63, caller locals occupying all10
callee registers, nested calls, joins, leaf bodies, allocations, tail calls, RET2/
RES2 and partial fuel.96 actual allocating replacement-import comparisons and40
resource exhaustion/partial-write comparisons pass.209 full/partial-fuel states
of all19 original workloads equal current qualified product, with canonical
source hashes and original results/fuel unchanged. Thus1095 additional full-state
comparisons were sealed along with7989 regressions before timing.

The authoring audit initially required offset>=16 for every function. Leaf
functions with no callee locals have no original callee-save region. Corrected
non-overlap bound is offset>=8*localnsv; actual instructions and original frames
are checked. Initial failure/script remain archived; compiler and execution
expectations were not changed.

## Fresh prospective timing

Apple M4 zebulun, same pinned runner/C/original sources/spec.30 accepted rotating
product/candidate/C triples per changed guest;180 accepted of188 attempts total.
Rows independently audited for rotating order, load<=4, idle>=90%, interval,
RSD<=10%, source/guest/offset/C/runner/proof pins. Qualification requires both
baseline/candidate>=1.05 and mean gap>summed SD. No retiming of identical machines.

|Original workload|Product ns/body|Candidate ns/body|C ns/body|Shorter time|Qualifies|
|---|---:|---:|---:|---:|---|
|huffbench|53349.57|53415.95|7187.32|-0.12%|No|
|matmult-int|18384.33|16701.06|935.17|9.16%|No|
|md5sum|12465.81|12300.02|2499.12|1.33%|No|
|nettle-sha256|2760.86|2846.92|218.99|-3.12%|No|
|slre|7830.99|7721.54|1037.96|1.40%|No|
|ud|534.05|552.82|53.95|-3.52%|No|

Matmult's9.16% shorter mean does not qualify:1683.27ns mean gap is below1823.65ns
summed SD. SHA and UD are slower. The unrestricted prototype is rejected, so
product gates/integrated rebuilding are not rerun for this rejected algorithm.
Other13 original guest binaries equal current product; no fresh19 aggregate.

## Evidence changes the next action

Named capacity is not the problem: historical native SIR matched to fresh
allocation metadata shows the high depths are actually named. MD5's two high
functions and two SHA setup functions each build vectors from only constants
plus VEC/RET (with an entry label). Deferred constant descriptors already avoid
high expression spills, so adding callee saves/restores does not replace that
work. All64/56 named temps are present; the earlier unused-declared-capacity
hypothesis is falsified.

Next observe actual high-temp materialization/reads, descriptor transitions,
coalescing and loop membership before choosing a general profitability policy.
Counts are not measured time shares. A later changed machine needs independent
semantics and fresh prospective timing, then permanent gates/integrated3gen/
per-case corpus proof before promotion. See [registered next hypothesis](evidence/coscientist-callee-temp-20261006/next-hypothesis.json).
