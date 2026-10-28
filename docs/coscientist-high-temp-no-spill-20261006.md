# High-depth reads without call spills: matmult qualifies, unrestricted candidate rejected

Removing call spills produces a qualifying15.32% shorter original matmult time.
SHA-256 improves1.14% but fails the unchanged prospective rule. Reject the
unrestricted prototype. The structural distinction found afterward is exact loop
containment: matmult's access belongs to a repeated backward-branch region;
SHA's five accesses are setup outside loops. The loop-contained follow-up must
prove its machine equals the qualifying target and all other18 originals equal
current product, then complete product qualification. C-or-better remains the full
19-workload objective. These are **not official Embench scores**.

[Summary](evidence/coscientist-high-temp-no-spill-20261006/summary.json),
[independent timing audits](evidence/coscientist-high-temp-no-spill-20261006/timing-summary.json),
[checksums](evidence/coscientist-high-temp-no-spill-20261006/checksums.sha256).
Native/timing archives preserve sources, machines, full state and raw rows.

The preceding [high-depth experiment](coscientist-high-temp-read-20261006.md)
removed C calls while retaining their call-preparation spills. This version leaves
computed prefix values in x9..x15 and high homes. Nonleaf local registers are
x19..x28; x0/x1 argument staging, x7 context and x16/x17 ordered checks are
therefore disjoint. Original result alias protection and fuel remain. All original
checks execute at the original accesses. No ABI, resource, capability or result
cache change is involved; native DefCID caching remains unconnected.

Four native generations are byte-identical,811192B, SHA-256
`441141f5495677d6cd4a129d0d90e2ea9ece84c5aeb3625e9432bc1e6300e28e`.
All19 source/results/fuel receipts match; only matmult/SHA machines change.
The observation-only and quiet emitters produce identical guests.

Before timing,4196 fresh original regressions and17337 full-state comparisons
pass:15840 high-depth hand cases,1152 raw-read/nonleaf/deferred-local-alias/branch-
join cases,96 actual allocating open imports,40 partial resource writes and209
original19 full/partial-fuel observations. The independent native audit verifies
all6 actual ordered-check/load templates and all33 hand callers. No golden or
original expected result changes. The diagnostic observer initially injected at an
earlier matching helper; repair restricted it to the exact definition. A remote
launch initially referenced the prior directory; the proof-count assertion rejected
it before any measurement or status write. Both initial logs are retained.

Fresh Apple M4 zebulun comparisons use30 rotating product/candidate/C triples per
workload:60 accepted,62 attempted. Load<=4, idle>=90%, adequate interval and
relative SD<=10% hold. Promotion requires ratio>=1.05 and mean gap>summed SD.
Source/native/offset/compiler/C/runner/spec/preflight pins and every admitted or
rejected row are independently audited. No identical-machine retiming seeks a pass.

| Workload | Product ns/body | Candidate ns/body | C ns/body | Shorter time | Gap / summed SD ns | Decision |
|---|---:|---:|---:|---:|---:|---|
|matmult-int|21789.78|18450.55|923.36|15.32%|3339.22 /2190.38|Qualifies|
|nettle-sha256|2748.72|2717.39|215.78|1.14%|31.33 /81.15|Reject|

Static loop-containment analysis of the actual original SIR finds1 admitted
matmult access, enclosing label807 at SIR3274..3315. SHA accesses747/750/753/
756/759 in function726..782 have no enclosing backward branch. These counts are
not time shares. A general bounded same-function loop guard is registered; it
contains no source/benchmark names. This is compiler optimization of the complete
original workloads, with the full C-or-better goal unchanged.

Separately, actual native census finds unused callee registers and high temps in
six workloads. Using those registers with disjoint backup homes is a possible
future hypothesis, not implemented or measured here. It must retain original
frame size, callee preservation, fuel/traps/effects and independent proofs.

The experiments are one-off new Kotoba algorithm and diagnostic/test authoring,
outside existing mechanical AST rules. The unrestricted candidate is not promoted.
No fresh all19 aggregate, launcher switch, rung update or100% selfhost claim follows.
