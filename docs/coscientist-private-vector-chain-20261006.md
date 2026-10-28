# Content identity and native private descriptor transfer: negative performance result

The new descriptor-transfer compiler is implemented and independently tested,
but **rejected after a fresh low-load same-host measurement**. The qualified
[terminal-only-frame product](coscientist-small-tail-frame-20261006.md) remains
unchanged. This is progress toward the original19 C-or-better goal, not completion,
a release, or an official Embench score.

## Identity and the performance hypothesis

Unison identifies definitions by syntax-tree hashes, with dependencies addressed
by their hashes ([official explanation](https://www.unison-lang.org/docs/the-big-idea/)).
Kotoba's `lang/code-identity.edn` declares definition payload2 over checked typed
KIR, profile/desugar-contract versions, semantic effect row, interface and direct
definition dependencies. Alpha normalization precedes dependency linking. This
is **content addressing of checked definitions**. The reviewed contract also
labels prior bootstrap worker cache evidence separately from the native route.

A computation request additionally identifies arguments, observed external state,
execution profile and resource/authority conditions. Its canonical recipe can
itself be content-addressed; “compute address” is a useful conceptual name for
that different object, not an implemented substitute for DefCID. Definition
identity neither proves equal outcomes under changed inputs/state nor grants
execution authority. Hashing more inputs does not by itself accelerate execution.

Three falsifiable performance paths follow: reuse checked/compiled artifacts;
compile closed dependencies and effect contracts into lighter internal calling
conventions; and reuse pure deterministic results only under a separately complete
request contract. This experiment tests the second path. **Native DefCID artifact
cache and result memoization are not connected by this change.** The generator,
layout and private ABI are sealed by SHA256 in the prototype proof/timing manifest;
those pins are not presented as a new canonical DefCID implementation.

## Fresh original statemate measurement

Authorized zebulun Apple M4,30 accepted rotating product/candidate/C triples from
31 attempts, using unchanged load/idle/interval/stability/qualification rules:

| Original body | Mean ns | Sample SD ns |
|---|---:|---:|
| Current qualified native product |561.635870|16.947368|
| Private descriptor prototype |580.189937|13.354113|
| Unchanged pinned C |30.567810|0.371193|

All arms meet the stability threshold. Candidate mean is3.3036% higher; the
difference is below summed SDs and the1.05x qualification threshold. Neither
improvement nor regression qualifies. Candidate/C is18.980422x. The candidate
changes only statemate; the other18 original native guests are byte-identical.
No identical-candidate retiming, historical speedup compounding, full19 new
aggregate, or official Embench score is claimed.

Raw triples, admission, means/sample SDs, results, source/artifact/fuel/runner/C
pins are independently recalculated. Original statemate code grows21316→23714
words. Extra guard/control-flow and code footprint are plausible explanations
for the negative result; this measurement does not isolate their cost shares.

## Implementation and exact safety boundary

Start from the qualified compiler, excluding all previously rejected unsigned-
comparison and local writer candidates. Actual closed mode2 Vec→Vec functions
with one parameter,1..3 locals/temporaries, no frame/spills/outgoing calls,
returning/indirect calls, allocation, capability or floating operation qualify.
x3 length/x4 item base/x5 positive validated handle are spare under that contract.
The public entry clears x5. A genuine compatible terminal B can enter exactly
one word later. Unknown callers, exports and function addresses retain the public
entry. Original published five-word fuel charges remain in place.

Every first access compares the actual handle with a nonzero key. A miss performs
original handle validation and captures immutable descriptor metadata at the
original access; every hit retains the actual access's own index check. Target
classification validates typed SIR, local/depth ranges, owned labels and an actual
unexpanded terminal call. Layout accepts the private fix only on a real B and
actual public clear marker. This is a closed compiler/supervisor contract, not
proof against arbitrary corrupted memory or an arbitrary hand-written ABI caller.

Native generations2/3/4 are byte-identical,838024 bytes, SHA256
`3d813e7b739b73bab5b007160b1b98586f4f677693b6a3e1e35f1707ce9b9cee`.
Generation1 differs (838000 bytes); four-generation equality is not claimed.

11,232 full supervisor comparisons include9,450 independently predicted chain
states,1,445 states across all17 supported integer binary/comparison/unary
operators,209 original19 fuel states,38 original resource states, and90 new
resource states. Changed/invalid handles, writes preceding transfers, aliases,
quotient traps, fuel exhaustion and all partially written items are checked.
119 source-field mutations and5 private-layout mutations are refused. All508
existing fixtures and14,523 native executions pass; original fixture bytes and
real/test layout code/offsets remain exact.

Read-only generator observers emit exactly the quiet candidate bytes/offsets.
All19 original SIR, frame/local/depth/leaf metadata match. Machine audit checks
291 private B targets,390 public cold-entry functions, and1,806 original charge
prefixes. These are static counts, not runtime cost shares. The earlier calibrated
[dynamic census](coscientist-terminal-census-20261006.md) remains separate evidence.

An independent oracle initially assumed slot6 retained handle1 after a write;
both baseline and candidate correctly trapped on the overwritten handle49.
The oracle now reads postwrite state and all9,450 cases were rerun. An audit
initially read pre-FN cache mode rather than recorded post-FN mode; corrected
all19 audit passed. Neither correction changed compiler behavior or weakened an
expectation. Initial failure evidence is retained.

## Decision and next experiment

No product generator/layout, fixture golden, loader, default rung, bin entry or
capability grant changes. Product BUILD/ERR/G1–G5 and integrated adoption gates
are not rerun for this rejected prototype: performance is their prerequisite.
The one-off temporary compiler algorithm/layout design and independent fixtures
are an authoring exception, not a mechanical refactor of product source.

The next registered hypothesis restricts private transfer to an unchanged-root
witness valid on every reaching path, so a proved access may omit equality
checking. Branch joins, root assignment and unknown effects must kill/intersect
that witness; no speculative access may move before original fuel. First count
eligible original sites, then independently verify semantics and perform one
fresh unchanged-rule timing campaign. If too few actual accesses qualify, pivot
to scalar state representation rather than retime this candidate.

Evidence: [summary](evidence/coscientist-private-vector-chain-20261006/summary.json),
[timing audit](evidence/coscientist-private-vector-chain-20261006/timing-audit.json),
[internal ABI](evidence/coscientist-private-vector-chain-20261006/internal-abi.json),
[next hypothesis](evidence/coscientist-private-vector-chain-20261006/next-hypothesis.json),
[native experiment archive](evidence/coscientist-private-vector-chain-20261006/native-experiment.tgz),
[checksums](evidence/coscientist-private-vector-chain-20261006/checksums.sha256).
The archive retains sources, native generations, full state observations,
observers and raw remote timings. Extract and run `replay-analysis.py` to check
stored state oracles and recalculate timing controls; replay is not a fresh
native execution. The original C-or-better full19 goal remains open.
