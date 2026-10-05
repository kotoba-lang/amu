# Content identity, computation identity, and native performance

Latest qualified follow-up: [native census and repeated scalar-mask composition](coscientist-native-census-mask-20261005.md)
reduces freshly measured MD5 time10.57% and SHA-2565.25%; other17 original guest
binaries are unchanged. Native seed fixedpoint, permanent regression, gates and
integrated three-generation/corpus parity pass. The unrestricted AES arm failed
and was rejected. Exact closed implementation proofs remove call overhead;
this is not connected DefCID caching or computation-result memoization.
C remains4.91x and12.62x faster in those respective aligned body comparisons.

Previous follow-up: [closed scalar-argument specialization](coscientist-static-arg-20261005.md)
produces11 native variants across5 original programs and passes native fixedpoint,
4233 hand-derived runs and180 actual allocating-import comparisons. All five
fresh timing comparisons fail promotion; product source stays unchanged.
Next registered step is a native dynamic cost census before another specialization.

Previous follow-up: [constant recovery across joins](coscientist-affine-join-20261005.md)
recovers4 sites after native observation falsified the source-only assumption
(0 sites). Native proofs pass; fresh4.37% shorter timing fails both promotion
criteria. No product change. Next hypothesis is closed-callee scalar-argument
specialization, including explicit loop-invariance proof.

Previous follow-up: [two affine signed-write candidates](coscientist-affine-writer-20261005.md)
preserve native state and fixedpoint but fail the prospective timing rule
(3.10% and4.59% shorter; ratios1.031967 and1.048076). Neither is promoted.
That registered index-operand hypothesis is evaluated in the latest follow-up above.

The previously qualified [signed-clamp composition](coscientist-clamp-call-20261005.md)
qualifies5.48% shorter freshly executed Picojpeg time and passes integrated
three-generation rebuilding, full supervisor comparisons and unchanged corpus
outcomes. Other18 guest binaries are unchanged. It uses stable exact SIR/body
proofs and refuses open imports; it is not DefCID or execution caching.
The previous [context proof](coscientist-context-call-20261005.md) improved UD.
C-level-or-better on the original aligned workloads remains unachieved.

Current code identity is content addressing. `kotoba.compiler.definition-identity`
alpha-normalizes checked typed KIR and seals six inputs: typed KIR, profile version,
desugaring contract, effect row, interface (including reachable schemas), and direct
definition dependencies. References use callee CIDs; recursive groups use `scc-v1`.
This identifies normalized implementations, not every mathematically equivalent
program. Names are not implementation identity; exported names and declaration
order can nevertheless affect artifact bytes. ADR 0300 and its amendments explain
those boundaries. The implementation has a Kotoba reading as well as bootstrap
readings. Existing compile/verdict stores reuse admitted artifacts/static verdicts;
a cache key alone is not proof that a particular native command uses those stores.

The measured native seed route lowers directly to SIR. Its Kexe writer explicitly
records `:program nil` and `:kir-sha256 nil`; the unified checker still refuses
`--json` because the definition-CID envelope is not linked. Therefore the current
integrated Embench compiler is not evidence of end-to-end DefCID caching.

Unison calls this content-addressed code too: normalized syntax and dependency
hashes identify a definition, while human names are separate metadata. Its reusable
checking and pure-test results follow from immutable code identity, not from a
claim that all executions or all algebraically equivalent functions share a hash.
Primary references: https://www.unison-lang.org/docs/the-big-idea/ and
https://www.unison-lang.org/docs/language-reference/hashes/.

A computation address would be a separate, versioned recipe identity, conceptually
`H(domain, DefCID, canonical input values, semantic profile, handler/state snapshot)`.
It is not a CPU/host address. An artifact address additionally seals compiler
identity, target, runtime/context ABI, optimization settings, policy/resource
inputs, ordered definition CIDs and export/packaging metadata. Hashing handles,
mutable names, or only function source is insufficient. Effectful calls need an
explicit snapshot/handler contract; unknown effects or unavailable identities
must refuse cache admission. Fuel, traps, allocation limits and cancellation are
observable: even pure-looking results cannot silently bypass them. A cached test
result must not be reported as a fresh executed Embench workload.

## Experiment CA-1: identical-content branch elimination

Hypothesis registered before timing: proving that both arms of an integer decision
tree return the same literal permits eliminating redundant branches, potentially
reducing Picojpeg instruction-cache pressure. Canonical benchmark sources stay
unchanged. This is new compiler algorithm authoring, not a mechanical rewrite;
no existing refactor rule covers the one-off experimental algorithm.

The prototype changes `lw-if` in the native seed lowerer. A bounded (32 levels)
exact proof recognizes integer literals and uniform nested `if` trees. Nested
conditions must be comparisons of literal/local scalar values. Unknown forms,
calls, mutable reads, division, capabilities and allocation are not admitted to
that proof. A root condition outside the pure subset is still evaluated once,
including its original fuel/trap behavior. Literal content equality is checked
exactly, without hashing. This is a local application of content equality, **not**
an implementation of DefCID integration or computation-result caching.

Three generations (2/3/4) of the native compiler reproduce identical bytes. All
19 canonical workloads preserve the existing representative results, exact fuel
consumption and fuel-exhaustion traps. Targeted probes cover signed extremes,
differing branches, a fuel-charging condition call, and a trapping vector read.
Picojpeg's complete workspace after one and two bodies is compared with the
previous selfhost compiler; source and compiler hashes are retained in evidence.

## Timing decision

On zebulun (Apple M4), the pre-existing pinned runner and unchanged C binary are
used. Baseline is the measured wrapper compiler's machine code; all three arms
are resampled, rotating order, 30 accepted triples, fixed 90-attempt limit,
300 ms target interval, minimum 50 ms, load <= 4, estimated background idle >= 90%,
and each arm RSD <= 10%. Promotion requires >= 5% speedup and a mean gap greater
than summed standard deviations. All rejected attempts/calibrations are retained.

| Picojpeg arm | Mean us/body | RSD |
| --- | ---: | ---: |
| Previous native selfhost | 314.615 | 2.18% |
| Content-equality prototype | 315.043 | 1.90% |
| C, unchanged comparator | 10.836 | 0.79% |

The candidate has 40,932 code bytes against 45,652 (10.34% smaller), but the
speedup is 0.99864x: no execution improvement. Candidate/C is 29.0738x in this
experiment. The hypothesis is rejected for performance promotion. The production
compiler and integrated image stay at the previously measured wrapper version.
These are custom aligned whole-body timings, not official Embench scores, and
no new full-suite performance geometric mean is inferred from one workload.

## Next experiment boundaries

1. Instrument hot helper calls and checked vector operations; select a measured
   execution cost rather than assuming repeated source means repeated work.
2. Test generic specialization with known immutable arguments. Key optimized IR
   by sealed definition/input identities and the compiler/ABI/profile; preserve
   fuel, bounds checks and effects. This can improve freshly executed workloads.
3. Connect identities to the native seed route only through an explicit checked
   SIR/KIR contract. Do not label raw SIR/source hashes as existing KIR DefCIDs.
4. Separately measure cold/warm compile and incremental rebuild caches. Reusing
   code/check results can improve development latency but does not demonstrate
   an Embench execution-speed win. Consider computation-result memoization only
   where reuse exceeds canonicalization, hashing and lookup cost.

Evidence: [summary](evidence/coscientist-content-address-20261005/summary.json),
[full native experiment](evidence/coscientist-content-address-20261005/native-proof.tgz),
[timing rows and baseline lineage](evidence/coscientist-content-address-20261005/timing.tgz).

## Follow-up: what “compute address” would identify

Verified again at source HEAD `03e147c3c1e70a80e8bea72ba3bcb11594d47b44`.
`src/kotoba/compiler/definition_identity.cljk` contains the typed-KIR/effect/
interface/dependency identity contract and a Kotoba reading. The measured native
seed artifact writer is `seed/amu-main/src/amu/kexe.kotoba`; its KIR fields are
explicitly nil. `seed/amu-main/src/amu/check_full.kotoba` still refuses the JSON
identity envelope. Existing identity modules therefore do not establish that
these particular selfhost commands have a DefCID-based cache.

Three different identities serve three different jobs:

| Identity | Sealed inputs | Reuse |
| --- | --- | --- |
| Definition content | Normalized checked implementation, dependency CIDs, type/interface, effects, semantic/desugaring profile | Checking and identifying an immutable implementation |
| Computation recipe (proposed) | Definition CID, canonical immutable arguments, semantic profile and explicit handler/state snapshot | Reusing deterministic results or unchanged subcomputations |
| Native specialization/artifact (proposed) | Definition/dependency identities, immutable static arguments, compiler content identity, target, runtime/fuel ABI, optimization contract, policy, ordered exports/packaging | Reusing compiled specialized code |

A computation address is itself content addressing of a computation recipe.
It is not an execution host's network address, a hash of one past output, or
proof of equivalence between arbitrary programs. If compute means a remote
execution location, that is a separate handler choice: Unison's `Location`
is explicitly distinct from its hash of a computation. The primary source is
[Unison incremental evaluation](https://www.unison-lang.org/articles/distributed-datasets/incremental-evaluation/).

Recipe admission must reject unavailable dependency identities, unknown effects,
mutable handle inputs without immutable snapshots, and unsealed profiles. A
native artifact also needs position-independent code or relocation metadata;
absolute/relative call offsets cannot be cached as independent functions and
reused at arbitrary locations. Cache verification does not substitute for
current capability/policy admission. Fuel exhaustion, traps, partial writes,
allocation and cancellation need an explicit resource/observation contract.

The next implemented experiment applies *structural proof and specialization*
to a hot bounded vector-fill loop. It does not add a DefCID cache or computation
memoization: the seed recognizes exact SIR and dependencies before lowering,
checks immutable loop parameters at runtime, and otherwise executes the original
loop. The comparison executes all original benchmark bodies freshly. This
separates a possible execution-speed benefit from a warm-cache reuse benefit.
Detailed native proof and timing decision are recorded in
[the bounded-fill experiment](coscientist-bounded-fill-20261005.md).

Future identity integration should separately report cold compilation, identical
warm compilation, private rename, one changed leaf and its affected dependents,
and changed compiler/target/profile/policy cache misses. Count actual rebuilt
functions and compare final artifact bytes. For result memoization separately
measure hit rate, canonicalization/hash/lookup overhead, retained bytes and
resource semantics. Neither cache experiment qualifies as fresh-body Embench
execution speed.

Latest native execution follow-up: [multiple-site cold fuel sharing](coscientist-multi-cold-20261005.md)
passes fixedpoint and native state proofs;8 of19 improve but EDN regresses.
It is rejected globally. Definition identity is unchanged; no cache hit is
counted as a fresh executed body. The next registered masked-writer experiment
uses exact SIR structural/dependency proof, not assumed DefCID integration.

Latest qualified execution improvement: [exact masked writer](coscientist-masked-writer-20261005.md)
shortens Picojpeg6.49% in fresh quiet measurements, preserves18 other workload
binaries and passes native state/regression plus integrated fixedpoint proofs.
It is promoted through the actual product path. This remains structural SIR
specialization, not DefCID/result caching; C-or-better remains unachieved.
