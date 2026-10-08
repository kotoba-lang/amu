# Bounded review of ComputeCID / ResultCID integration

The two current documents already cover the requested policy: request identity includes input-state/read closure, dependency and rules versions, reader/ABI/effect/trap/resource contracts; Result identity owns semantic answer and ordered edge contributions; current admission and state updates belong to a separate TransitionReceipt. Incomplete, refused or budget-exhausted computations do not publish successful bindings. Current authority/fuel/charging remains checked at reuse. Equal Result alone does not stop consumers or clear SCC worklists. Total cold/warm cache costs and generated-code Embench costs are separate. No new broad design section is needed.

The remaining gaps are concrete implementation/evidence items already acknowledged by the contracts: registered owned-answer schema and lifetime; complete versioned read/dependency manifest and writer invalidation closure; actual importer/lookup refusal tests; consumer-visible transition view and SCC completion receipt; inclusive cost measurements. These documents are acceptance contracts, not implemented reuse qualification. C2 stays OFF, exclusions empty, new skips zero.

Three details should be made explicit in the next preregistration rather than repeated as general policy:

1. Dependency invalidation must name callee implementation/body and its transitive typed dependencies, not just callee name/signature. Preserve DefCID; bind rules/stage versions in request/provenance. A changed callee may force recomputation even when ABI is unchanged. If its newly computed owned Answer is equal, stopping is considered only after current transition and complete consumer read-view checks. This is an explicit test of the existing dependency-closure rule, not a missing conceptual rule.
2. Specify exact owner/snapshot/output-schema/read-role fields and consumer-view equality representation, plus SCC pending-work/revision membership. Without those concrete records, downstream stopping is not an executable acceptance predicate.
3. Specify cost boundaries and distributions: context seal/encode/hash/resolve/lookup/validate/replay/publish/invalidation and failed/miss paths, cold and warm, amortized context cost, baseline and hit-rate source. Logical saved analysis work alone is insufficient. Existing docs already include inclusive cold/warm costs; this is the measurement schema still to instantiate.

| Concrete acceptance check | Required observation |
| --- | --- |
| Same complete request under same snapshot | Strict decoded fields/owned bytes agree; verified binding admitted; direct/shadow transition matches. Digest alone is insufficient. |
| Changed callee body/dependency, rules, ABI, input state, effect/trap or budget (one at a time) | Actual lookup/admission invalidates old request or refuses; direct recomputation runs. Retain same-answer case separately. |
| Different complete requests recompute equal Answer | Compute identity changes; owned Result bytes/CID can agree; each request has its own current admission and transition receipt. Do not use same-payload encoding alone as recomputation proof. |
| Equal Answer with changed target aggregate, caller poison, authorization or consumer read field | Apply current ordered contributions; invalidate affected consumers; preserve fuel/charging; no unconditional stop. |
| Equal Answer with stable complete consumer view | Permit edge-local stop only after pending effects and declared SCC/worklist revisions settle. Another changed dependency still propagates. |
| Partial result, wrong owner, missing/duplicated/reordered edge, arity or -1/0 change, stale context, insufficient budget or revoked authority | Actual import/admission rejects; valid-last successful binding absent; unknown condition follows declared direct-analysis fallback rather than accepting a hit. |
| Cold/warm end-to-end total cost | Account every listed cache stage and failure/miss path; report real latency separately from logical work and independently from native Embench performance. |

Current lineage remains a blocker: the consumer contract explicitly says audited current16/current41 has no historical vw/stage6 shape-memo query path. Current7618 is a builder; historical 41-result is a separately registered subject. This review did not inspect new implementation source or infer that a consumer observer can instrument an absent current path. Choose and pin the analysis subject before implementing these checks.

Scope: read-only review of the two pinned documents against requirements relayed in the parent assignment; the full latest user text was not independently retrieved here. No product edits, native/compiler/SSH/network/process APIs, prior shadow40 reruns or new cache qualification.
