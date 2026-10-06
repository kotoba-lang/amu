# Local constant-index rewrite: native proof passes, performance candidate rejected

The co-scientist loop now connects the [rooted rewrite/SMT/translation proof layer](coscientist-rewrite-proof-20261006.md) to an actual native AArch64 compiler candidate. The candidate is correct under its tested closed contracts, but one prospectively registered unchanged-rule comparison does not qualify a speed improvement. It is rejected for promotion. The qualified product remains unchanged; C-or-better across the original 19 workloads is not achieved.

The [completed-element census](coscientist-element-reuse-census-20261006.md) independently found constant local indices on all 480 observed closed accesses in one original statemate body. That observation motivated bounded scalar facts and constant-offset loads/stores, rather than result memoization or benchmark-specific recognition. Dynamic counts select a hypothesis; they do not prove cost or speed.

## Rule and implementation

Only existing typed closed mode2 Vec-to-Vec functions with at most three locals/temporaries are admitted. Three appended generator metadata cells track known scalar indices 0..4095; zero encodes unknown. CONST/LGET/LSET facts retain all original runtime assignments and descriptors. Explicit and coalesced writes invalidate their targets; control and unknown calls erase facts. Exact already-proved vector-at/vector-assoc! wrappers, optionally carrying their original fuel charge, may retain facts. Unsupported descriptors, modes, indices and calls use the original lowering.

A known index uses the existing checked handle/base path, unsigned CMP/B.HI/UDF bounds sequence, and scaled immediate LDR/STR. Original traps, assignments, reads/stores, charges, private transfers and ABI remain. No allocation, capability, unknown effect or result cache is newly admitted. The layout file is byte-identical to the product. This is a one-off new algorithm research prototype outside the product; it is not a mechanical product refactor.

The initial v1 covered 119 direct reads but missed writes through exact wrappers. Independent observation exposed the gap before timing. V2 adds those exact wrappers and covers 119 static reads plus 383 static writes. Static code counts differ from the one-body dynamic census. V1 has native proof evidence but no timing. Equal candidate sizes do not imply equal binaries.

## Proof before timing

- Actual native candidate generations 2/3/4 are byte-identical: 842,376 B, SHA256 `c161cee0516f929950635b6399cd1d49f94315f368491fa17b310ad13d508a20`. Generation 1 differs.
- Current 593 authoritative fixtures and 25,658 native runs pass without golden changes.
- 9,367 full supervisor groups compare result, trap, remaining fuel, resources and partial vector mutations: 9,120 independent new fact/alias/control/wrapper cases, 209 original workload states and 38 low-capacity original workload cases. Thirty-two native metadata guard controls pass.
- All 19 original SIR/frame/local/depth/leaf and representative outputs/fuel agree. Eighteen native images are byte-identical. Statemate changes from 21,929 to 21,810 words, 87,716 to 87,240 B.
- A read-only observer emits exact candidate bytes and offsets for all 19. Independent source-fact and instruction audits verify 502 constant accesses, 289 private transfers, 390 closed functions and 1,806 original five-word fuel prefixes, plus original explicit assignments.

Abstract SMT bounds/address laws are sealed alongside the exact source/compiler/ABI recipe. They prove the specified arithmetic laws under their assumptions, not the entire lowering or compiler. Native translation observations and machine audits add concrete evidence for this candidate. The earlier rooted graph worklist and finite authority model remain diagnostic prototypes; TLC/TLAPS and real authorization-runtime model checking have not run. Semantic DefCID, artifact recipe identity and computation/result identity remain distinct; hashing does not prove meaning or speed.

Two authoring errors were rejected by the audits: the observer factory initially referenced v1, and an audit initially assumed incorrect numeric opcode constants. The distinct v2 observer was rebuilt and matched all 19; the audit now derives opcodes from the authoritative source snapshot. The original failures and corrections are retained. No expected semantic outcome or acceptance threshold was weakened.

## Fresh comparison and decision

One campaign on quiet Tailscale host zebulun (Apple M4, arm64) rotates current product, candidate and pinned C. Original workload bodies execute afresh. The pre-registered rule requires at least 5% improvement and a mean gap greater than the sum of standard deviations, with 30 accepted triples, load/activity admission and relative SD at most 10%.

| Original statemate, ns per body | Mean | Standard deviation |
| --- | ---: | ---: |
| Current native product | 509.116 | 13.600 |
| Candidate | 513.973 | 18.956 |
| C | 30.238 | 0.323 |

Thirty triples are accepted from 31 attempts; the rejected triple is retained. All three arms meet stability admission. The candidate mean is 0.954% higher, within the measured variation; neither improvement nor regression qualifies. Candidate/C is 16.997x. This is an aligned original-body comparison, **not an official Embench aggregate score**. No different experiment's gain is compounded into these numbers.

Independent replay recomputes admission, raw statistics, source/native/C/offset hashes, fixed-point identities and fuel controls. After the failed performance prerequisite, adoption gates and integrated product rebuild are not run. The candidate is not promoted.

## Next experiment

Before another optimizer, attribute completed original fuel charges by SIR site and closed chain on unchanged statemate. Previous [sufficient-fuel regions](coscientist-fuel-region-20261005.md) and [cold failure layout](coscientist-cold-fuel-20261005.md) were rejected for performance, while [Picojpeg fuel attribution](coscientist-native-fuel-profile-20261005.md) counted a different workload. This next diagnostic must independently calibrate plain and charged-wrapper paths, preserve register/NZCV and full observable state, use bounded counters, and reproduce product bytes with instrumentation disabled. Counts alone cannot establish exclusive CPU cost. A later fuel-register candidate needs a proved ABI and publication at every trap/escape before any fresh timing. It is registered, not implemented here.

Evidence: [summary](evidence/coscientist-local-constant-index-20261006/summary.json), [preflight](evidence/coscientist-local-constant-index-20261006/preflight.json), [timing audit](evidence/coscientist-local-constant-index-20261006/timing-audit.json), [native sources, binaries and histories](evidence/coscientist-local-constant-index-20261006/native-proof.tgz), [raw accepted/rejected timing and C reference](evidence/coscientist-local-constant-index-20261006/timing.tgz), [untimed v1](evidence/coscientist-local-constant-index-20261006/v1-native-proof.tgz), [corrections](evidence/coscientist-local-constant-index-20261006/authoring-corrections.json), [next hypothesis](evidence/coscientist-local-constant-index-20261006/next-hypothesis.json), [archive checksums](evidence/coscientist-local-constant-index-20261006/archive-manifest.json).
