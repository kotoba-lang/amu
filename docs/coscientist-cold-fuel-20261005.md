# Cold fuel failure layout: eleven improvements, one regression

The preceding region experiment failed performance acceptance. This registered
experiment keeps every original fuel checkpoint and moves its failure code out
of the success path. Eleven of19 original workloads qualify for improvement,
but EDN has a separated regression. **Reject global promotion.** The product and
qualified integrated image remain the scalar-tree version.

## Implementation and native proof

Each fuel-bearing function gets a shared failure block immediately before its
callable entry. FF-CODE, exports and direct/indirect/tail references point after
the block. Every original SUBS decrement remains. Success falls through B.LO;
failure branches backward into the block. Nonleaf context stores and leaf
return/exhaustion publication remain at their original semantic points. There
is no body duplication, precharge, deferred consumption or extra generator heap.
At each checkpoint, the actual branch position is computed after any gn-ctx
restore. An absent target or signed19-bit distance outside range uses the
original inline failure sequence. No function or benchmark names select behavior.
This is new compiler algorithm authoring, not a mechanical refactor.

The qualified producer is824,952 bytes, SHA-256
`98905d4a7c3da0d94465d99f4b32ae195c2e7972d1b995a3744a0d588595635d`.
Native generations2/3/4 match at821,096 bytes, SHA-256
`d71e3b182d0eb040b31b7c851062d98d247d8db729b6842f49f35ff9ec3f2289`.
Their main entry offsets also match at4, rather than the producer's0. Builders
read actual extracted offsets; an offset0 assumption is not qualification.

All19 canonical workloads preserve results/exact fuel at n0/1/2/17/32 and
exhaustion behavior. Every binary changes; Picojpeg is43,084 ->42,828 code bytes.
All8,192 Pico workspace cells after one/two full bodies match. Existing1,979
native executions pass, including callable entry/callback/tail cases. Test/real
fixture layouts agree across258 fixtures. Independent instruction audits resolve
334 cold branches in83 functions and check their exact failure targets, leaf
zero publication and nonleaf success stores. All2,776 full supervisor reports
and owned partial vector arenas match over low budgets, invalid reads/writes,
division traps, context restoration, charged wrappers and deep/live temporaries.

Five additional comparisons cover zero fuel at the callee's region entry after
a legal budget1 is consumed by its caller. Initial budget0 is refused by the
supervisor. Eight native generator cases cover the exact -262144-word branch
limit, one word beyond, actual context restoration and missing-target fallback.
The first isolated span-test builder duplicated main supplied by00-ns; the
producer refused E2001 before execution. Naming its test entry seed-main fixes
that test only; candidate compiler/program bytes did not change.

## All19 fresh comparisons

Host: zebulun Apple M4. Exact current product machine code, original C binaries,
canonical source matrix and runner are pinned. Thirty accepted rotating triples
per workload:570 accepted from593 attempts, 300ms target, 50ms minimum, load<=4,
estimated background idle>=90%, RSD<=10%, fixed90-attempt cap per workload.
All accepted row conditions, means and SDs are independently recomputed.
All calibration/rejection rows and baseline lineage are retained.

| Workload | Product us/body | Prototype us/body | C us/body | Product/prototype | Prototype/C |
| --- | ---: | ---: | ---: | ---: | ---: |
| picojpeg | 236.410 | 211.512 | 10.832 | 1.11771x | 19.5265x |
| aha-mont64 | 1.079 | 0.885 | 0.544 | 1.21925x | 1.6247x |
| crc32 | 3.929 | 3.447 | 1.707 | 1.13976x | 2.0199x |
| depthconv | 0.125 | 0.117 | 0.035 | 1.06332x | 3.3611x |
| edn | 12.042 | 13.077 | 0.764 | 0.92088x | 17.1167x |
| huffbench | 54.957 | 50.594 | 7.466 | 1.08623x | 6.7769x |
| matmult-int | 22.474 | 19.812 | 0.958 | 1.13437x | 20.6728x |
| md5sum | 14.191 | 12.893 | 2.533 | 1.10070x | 5.0899x |
| nettle-aes | 25.751 | 23.598 | 1.421 | 1.09122x | 16.6016x |
| nettle-sha256 | 3.050 | 2.852 | 0.222 | 1.06924x | 12.8363x |
| nsichneu | 0.703 | 0.698 | 0.079 | 1.00713x | 8.7944x |
| qrduino | 275.195 | 267.929 | 22.353 | 1.02712x | 11.9860x |
| sglib-combined | 41.807 | 39.383 | 5.820 | 1.06155x | 6.7671x |
| slre | 7.968 | 7.514 | 1.054 | 1.06035x | 7.1319x |
| statemate | 0.768 | 0.745 | 0.032 | 1.03105x | 23.4675x |
| tarfind | 14.487 | 10.839 | 1.007 | 1.33656x | 10.7651x |
| ud | 0.592 | 0.569 | 0.054 | 1.04090x | 10.4896x |
| wikisort | 214.100 | 209.683 | 15.206 | 1.02107x | 13.7896x |
| xgboost | 1364.451 | 1300.258 | 186.492 | 1.04937x | 6.9722x |

Promotion needs >=1.05 speedup and a mean gap greater than summed SDs, with no
separated regression. Eleven improve under that rule; eight do not qualify.
Depthconv's >5% ratio alone does not clear its summed SD. EDN is8.59% slower:
1.035us gap >0.532us summed SD. EDN's cause is unproven; it is the original
FIR/DCT numerical workload, not a parsing workload. Picojpeg shortens10.53%,
with24.898us gap >7.744us summed SD. These findings do not establish an exclusive
fuel-time decomposition or make EDN's regression acceptable after seeing results.

Across these19 aligned whole-body time ratios, the custom geometric mean is
1.07989x product/prototype; prototype/C is8.71071x. This is not an official
Embench score or formal perfgate qualification. C-or-better remains unachieved.
No product source, fixture golden, rung pin, bin/amu or integrated image changes.
The rejected prototype is archived; identical code is not retimed to seek a pass.

## Next prospective experiment

Require multiple syntactic charge sites before sharing a cold block. Count SIR
FUEL and optional charges of exactly admitted inline wrappers before generation.
Single-site functions keep legacy emission: moving one failure sequence does not
reduce total function size. With >=2 sites, retain the actual branch-distance
proof and original semantics. Static sites are not dynamic counts or exclusive
times. This generic profitability threshold does not assume EDN will recover.
No names/profile hints select optimization. Require native fixed point, all19
semantic proofs, single/multiple-site instruction audits and fresh timing of
every changed workload before promotion. This next hypothesis is registered,
not implemented or qualified here.

Evidence: [summary](evidence/coscientist-cold-fuel-20261005/summary.json),
[prototype](evidence/coscientist-cold-fuel-20261005/prototype.diff),
[native proof](evidence/coscientist-cold-fuel-20261005/native-proof.tgz),
[all19 comparisons](evidence/coscientist-cold-fuel-20261005/timing.tgz),
[independent row audit](evidence/coscientist-cold-fuel-20261005/timing-audit.json),
[next hypothesis](evidence/coscientist-cold-fuel-20261005/next-hypothesis.json).
