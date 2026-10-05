# Content identity, computation recipes, and measured native reuse

Subsequent qualified experiment: [dominated same-local reads](coscientist-same-local-read-20261006.md)
removes the later dynamic-key comparison after a stable-local/straight-line proof.
Fresh30triples qualify18.494929% shorter originalmatmult; permanent native tests,
gates and committed-source integrated3gen/full actual-output parity pass. The
dynamic-cache-only trial below remains rejected. C-or-better all19 remains open.

The current checked-definition identity is **content addressing** of a normalized
implementation. A computation recipe can also be content addressed; these are
layers of identity, not two competing kinds of hash. Neither identifies every
mathematically equivalent algorithm or a physical CPU location.

## Implementation audit

`src/kotoba/compiler/definition_identity.cljk` seals typed KIR, profile version,
desugaring contract, effect row, interface/reachable schemas, and direct dependency
identities. It alpha-normalizes binders, replaces callee names with CIDs, and handles
recursive groups using the canonical `scc-v1` contract. Unavailable identities
remain refusals. Module artifact material additionally preserves definition order
and export names because those can affect emitted bytes.

Unison likewise describes definitions as content-addressed syntax trees with
positional binders and dependency hashes. Its computation hash can support
memoization of a delayed computation; this still does not identify arbitrary
semantic equivalence or an execution machine. Primary references:
[code identity](https://www.unison-lang.org/docs/the-big-idea/) and
[incremental evaluation](https://www.unison-lang.org/articles/distributed-datasets/incremental-evaluation/).

| Identity | Required material | Potential benefit |
| --- | --- | --- |
| Definition | Normalized typed implementation, dependencies, interface/effects, semantic contracts | Reuse checking and stable specialization proofs |
| Native artifact | Definition identities plus compiler, target, runtime/context ABI, optimization/resource/policy configuration, relocation and packaging contract | Reuse emitted code; rebuild changed definitions and their dependents |
| Computation recipe | Definition plus canonical immutable arguments and explicit handler/state snapshot and observation contract | Reuse deterministic results or incrementally recompute changed inputs |

The third row is a proposed recipe identity, not a statement that the product has
a result cache. Hashing a mutable vector handle does not identify its contents.
Effectful calls require a sealed handler/state contract. Fuel, traps, allocations,
partial writes and cancellation remain observable even for expressions returning
simple values. A matching artifact does not bypass current capability admission.

The measured native seed route lowers source directly to SIR.
`seed/amu-main/src/amu/kexe.kotoba` explicitly emits `:program nil` and
`:kir-sha256 nil`. Existing compile/static-verdict cache modules have Kotoba
readings, but their presence is not evidence of end-to-end DefCID caching on this
route. Missing typed identity must remain unavailable; a raw source/SIR digest
must not silently become a DefCID.

## Prospective research tracks

1. **Native definition-to-artifact connection.** First measure cold compilation,
   identical warm compilation, a private rename, a changed leaf and affected
   dependents, then compiler/target/profile/policy misses. Record actual rebuilt
   functions, hashing/lookup time, bytes retained and final artifact equality.
   Position-dependent calls require relocatable objects or verified relocation
   metadata. This track targets build latency, not fresh Embench body execution.
2. **Proof-guided native specialization.** Use exact structural/closed-dependency
   proofs now, then key reusable proofs by real DefCIDs once connected. Measure
   helper transitions, repeated checks, spills and loop execution rather than
   assuming shared code implies shared dynamic work. Preserve all original bodies.
3. **Computation-result reuse.** Admit only explicit immutable input/snapshot
   recipes with specified effect/resource observations. Compare lookup plus
   canonicalization/hash cost with actual recomputation cost. Report hits, misses,
   retained bytes and invalidation separately. Cached results never count as fresh
   executed Embench iterations.

Track 2 is the implemented experiment below. Tracks 1 and 3 remain proposed;
no product cache, network execution or compute-address API is claimed.

## Experiment: high-loop descriptor reuse

Registered before native build/timing at source commit
`3edefd64577c316b97fc890384f45590b68ec28a`. Baseline is the qualified
[direct affine-index read](coscientist-affine-read-direct-20261006.md), not an
older rejected cache compiler. This one-off new Kotoba algorithm and independent
hand fixtures have no existing mechanical AST refactor rule.

A bounded scan admits only an original nonleaf function containing a validated
same-function high-depth vector read in a loop. The experimental emitter retains
one dynamically checked positive handle, descriptor length and base in x5/x3/x4.
A hit still checks the current index and reads the current item. Calls invalidate
reuse; function entry starts empty. Frames, local allocation, fuel and the existing
scalar-tree state remain unchanged. This is invocation-local descriptor reuse,
not content hashing or result memoization.

Actual native observation finds exactly two admitted original sites, both in
`matmult-int`; all other 18 original guest binaries are unchanged. Diagnostic
compiler and quiet compiler produce identical target bytes for all 19. Exact
machine templates verify register disjointness and branch targets.

An initial suspicion of alternating distinct A/B handles was falsified by the
canonical source and native execution. The authoritative full batch stores both
matrices in one 2,001-item vector, at offsets 800 and 1,200. Replacing only the
cache-hit equality branch with a branch to an appended diagnostic trap reaches
that trap for every positive canonical n; n=0 returns. This establishes actual
reuse-path execution, not a hit count or speedup. Diagnostic code is excluded
from timing.

Before timing, four native compiler generations are byte-identical at 815,512 B
and SHA-256 `48ad455d44aa4e26cc684c41a866a122a037f9f0606ece982afc306ea021e7d7`.
All original19 results/exact-fuel/traps match. Existing 434 fixtures/9,339 native
runs pass without changing their expectations. An additional 2,237 full-state
comparisons cover loop keys, joins, mutation, allocating calls, open imports,
ASCII/Unicode paths, output, seven-argument indirect calls, partial resource
writes and original19 full/partial fuel.

The frozen experiment compares current product, quiet candidate and unchanged C
on authorized zebulun (Apple M4). It uses one prospective batch of30 accepted
rotating triples, minimum background idle90%, load<=4, per-arm RSD<=10%, speedup
>=1.05 and mean gap greater than summed standard deviations. Raw rejected rows
and calibration are retained. These are aligned original-body measurements,
not official Embench scores. Performance qualification alone does not promote
source: permanent native guards/unit checks, release gates and committed-source
integrated fixedpoint/full corpus parity still apply.

## Terminal timing decision

| Fresh original matmult body | Mean us | Standard deviation us |
| --- | ---: | ---: |
| Current qualified product | 15.8725 | 1.0278 |
| High-loop descriptor prototype | 15.3777 | 1.4430 |
| Unchanged C comparator | 0.92125 | 0.00893 |

30 triples were accepted out of32 attempts. The prototype is3.12% shorter on
average (ratio1.032178), below the required5%; the0.49482us mean gap is also
below summed standard deviations2.47078us. **Reject performance promotion.**
The prototype remains16.6923x C. No performance benefit has been qualified;
product source remains the prior direct-affine-read compiler. Gates/integrated
promotion are not run for rejected source, and original test goldens are unchanged.
No full19 aggregate or official score is inferred from this single comparison.

Next registered, not implemented/measured: prove a later read has the same stable
local handle and is dominated by the original successful checked read in a bounded
loop with no intervening call/clobber; reuse the descriptor without the later
runtime key comparison. First-access handle checks and all index checks remain.
Unknown identity/dominance/effects must refuse. This structural proof may later be
cached by real typed definition identity; it does not implement that cache now.

Frozen [summary](evidence/coscientist-identity-and-reuse-20261006/summary.json),
[prospective follow-up](evidence/coscientist-identity-and-reuse-20261006/next-hypothesis.json),
and [native proof/prototype/raw timing archive](evidence/coscientist-identity-and-reuse-20261006/research-artifacts.tgz)
retain exact sources, scripts, images, negative hypothesis correction, pins,
full-state comparisons, raw measurements and timing decision. The archive is
research evidence, not product source. The all19 C-or-better objective remains open.
