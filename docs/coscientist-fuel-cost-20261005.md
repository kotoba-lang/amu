# Fuel lowering sensitivity on the unchanged Picojpeg workload

The preceding scatter-zero hypothesis did not qualify for promotion. This
registered diagnostic tests the influence of emitted fuel checks on the complete
original Picojpeg workload. It intentionally changes observable fuel semantics.
The product backend and integrated image are unchanged.

## Identity and performance

Current checked definition identity is content addressing of normalized typed
KIR, effects, interface, semantic/desugaring profile and dependency identities.
It identifies an implementation rather than arbitrary mathematical equivalence.
Unison likewise identifies definitions by normalized syntax and dependency hashes
([official explanation](https://www.unison-lang.org/docs/the-big-idea/)).

A computation recipe can also be content addressed, sealing definition identity,
canonical immutable arguments and explicit handler/state snapshots. An optimized
artifact additionally needs compiler identity, target, context/fuel ABI, policy
and proof contract. That supports repeated checking/builds and reuse of proved
specializations; hashing alone does not accelerate a freshly executed workload.
The native seed route currently writes nil KIR/program identity fields, so its
raw source/SIR hashes cannot be called typed-KIR DefCIDs or evidence of an
end-to-end identity cache. See the [identity analysis](coscientist-content-address-20261005.md).

## Native diagnostic and proof

Qualified producer compiler SHA-256:
`98905d4a7c3da0d94465d99f4b32ae195c2e7972d1b995a3744a0d588595635d`.
It builds one diagnostic compiler, whose SHA-256 is
`2bbbfd3ae03e3fde1775b37392ecb9d4560e83acd29e0c16b296e8ccf6320757`.
There is no diagnostic fixed-point claim. The producer's build execution retains
product fuel checks; programs subsequently compiled by the diagnostic omit them.

Only `gn-op-fuel` changes: omit charge/check instructions while retaining nonleaf
`gn-ctx` restoration and its compiler bookkeeping. Leaf fuel loads in the prologue
and stores in the epilogue remain. This is a one-off diagnostic algorithm change,
not a mechanical refactor or a product implementation.

Canonical source hash remains
`f570d637a074437c8bf80dccd646efae834962a312f0cea72638f5376350b8cd`.
Product machine code is 43,084 bytes; diagnostic is 40,544 bytes. At n=0/1/2/17/32,
results match; product fuel consumption is 1/222003/443939/3772979/7102019,
diagnostic consumption is zero. All 8,192 workspace cells after one/two bodies
match. Supplementary checks also compare complete supervisor reports after
removing only the intentionally different fuel fields; resource usage matches.
At fuel=1,n=1 the product stops with budget/fuel, while the diagnostic returns1.
That explicit difference prohibits product promotion.

Only known bounded inputs are admitted. Native validation and timing children
retain 30-second CPU/wall supervision. Timing admission uses actual producer and
diagnostic compiler byte hashes, a bounded proof and n32. The dedicated harness
does not invent compiler generations or expose a product promotion flag.
The original measurement admission files and later supplementary verification
are retained separately; no timing was repeated after supplementary checks.

## Fresh quiet-host comparison

Host: zebulun, Apple M4. Exact current product code, unchanged original C binary,
canonical matrix and runner are pinned. All three arms are freshly measured:
30 accepted rotating triples from 31 attempts, 300ms target, 50ms minimum,
load <=4, estimated background idle >=90%, RSD <=10%, fixed 90-attempt cap.
All calibration, accepted and rejected rows are retained.

| Picojpeg arm | Mean us/body | SD us | RSD |
| --- | ---: | ---: | ---: |
| Current native selfhost product | 238.627 | 3.957 | 1.66% |
| Altered-fuel diagnostic | 189.106 | 3.253 | 1.72% |
| Original C comparator | 10.809 | 0.103 | 0.95% |

Diagnostic time is 20.752% lower, ratio 1.26187x. The 49.521us mean gap exceeds
summed SDs 7.210us. This is counterfactual sensitivity to omitted charge/check
code, including code-size/branch-layout effects. It is not an exclusive-time
decomposition or a rigorous upper bound, correcting the original registration's
“upper bound” wording. Product/C is 22.0775x; diagnostic/C is 17.4958x. Neither
C-or-better nor an official Embench score is established. Fuel lowering warrants
investigation, but most of the remaining gap survives even this diagnostic.

## Next prospective design

Prove bounded SIR regions and their maximum charge count. A pre-entry guard can
select a fast path when sufficient fuel is available; retain original decrements,
context publication/leaf commit points, effects and ordinary trap paths. An
insufficient budget or unknown shape executes the original region before any
charge or mutation. Unknown calls, handlers, allocations, context writes and
unproved control-flow edges are excluded initially. Exact structure selects the
proof; function names do not.

Before timing, require three matching native rebuild generations, all19 canonical
result/fuel/exhaustion checks, full Pico workspace parity and targeted partial
state/trap comparisons for every insufficient budget through the region cost.
Promotion still requires >=5% improvement and separation beyond summed SDs in
30 fresh quiet rotating product/candidate/C triples. This design is registered,
not implemented or qualified by the diagnostic.

Evidence: [summary](evidence/coscientist-fuel-cost-20261005/summary.json),
[diagnostic diff](evidence/coscientist-fuel-cost-20261005/diagnostic.diff),
[native proof and lineage](evidence/coscientist-fuel-cost-20261005/native-proof.tgz),
[all timing rows](evidence/coscientist-fuel-cost-20261005/timing.tgz),
[next hypothesis](evidence/coscientist-fuel-cost-20261005/next-hypothesis.json).
