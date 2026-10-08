# Result equality and downstream stopping: independent SOURCE contract review

The consumer document correctly adds the boundary missing from a bare ComputeCID → ResultCID cache: after recomputation, equality of an owned semantic answer may suppress propagation **only for a consumer whose complete versioned read view remains equal after the current transition has been applied**. It cannot suppress current authority, budget/fuel/charge, ordered aggregate merge, caller support-loss/poison, or other required effects. This is a proposed acceptance contract, not a qualified implementation. C2 OFF, initial key exclusions empty, new skips0.

ComputeRequest identifies the complete requested calculation. Result identifies the answer under an explicit output contract, without inserting the request CID or execution activation merely to distinguish otherwise equal answers. VerifiedBinding/OwnershipReceipt must separately associate that answer with the actual context, target, mode/input contract, activation and writer provenance. TransitionReceipt binds current before/after state, merge/admission and consumption. A consumer may depend on an answer projection and on other state independently; Result equality cannot erase those dependencies.

| Case after recomputation | Required action | Downstream stopping decision |
| --- | --- | --- |
| Complete owned Answer differs | Apply current transition, propagate every changed declared input | Continue affected consumers |
| Complete owned Answer equal; current transition and all consumer-visible inputs equal | Validate/import contents and ownership, apply/check current transition and admission; compare versioned complete consumer view | Candidate to stop this dependency edge only; currently unqualified |
| Answer equal but target aggregate changes | Replay all ordered contributions against current prestate; invalidate readers of changed aggregate | Continue those consumers |
| Answer equal but caller support/poison/status/diagnostics change | Preserve caller post-query action and ordered effects | Continue readers of changed fields |
| Answer equal but authority, effect/trap, observable fuel/charge or budget admission changes | Recheck current authority/consumption; refuse unavailable admission; do not reuse successful receipt as current permission | No stop based solely on Result |
| ABI/rule/schema/reader/type/dependency contract changes | Invalidate request/binding or explicitly revalidate a new contract; track consumers' direct dependencies | Old binding unusable; new equal Answer alone insufficient |
| Edge value equal but owner/site/ordinal/order/duplicate/base/arity differs; -1 replaced by0 | Reject malformed Answer/transition; preserve exact edge identity and neutral/poison distinction | Refuse reuse |
| Memo hit has global scratch but no sealed matching owned summary | Emit SUMMARY_NOT_OWNED; keep existing baseline behavior | Refuse full Result construction/reuse |
| Unsupported, trap, budget exhaustion, incomplete/torn valid-last binding | Retain failure/partial receipt; no successful binding publication | Refuse reuse/stop |
| One Answer equal in SCC but pending work or external changes remain | Process required work and poison/invalidation; check all declared SCC inputs and convergence | No SCC-wide stop |
| Whole SCC stabilized under explicit merge/order/iteration contract and complete input closure | Prove no remaining dirty read dependency/pending transition; preserve any observable per-iteration obligations | SCC stop candidate only; currently unqualified |
| Consumer performs external writes or has unknown reads/writers | Require separate effect/transition preservation, otherwise directly evaluate | Refuse pure-result stop |
| Same digest but unverified payload/schema/provenance | Follow collision/content-verification/import contract; compare complete contents where required | Refuse digest-only acceptance |

## Missing concrete contract records

Before a downstream-stop implementation can be reviewed, define:

* OwnershipReceipt: context/snapshot, analysis subject and implementation, target, mode/input contract, actual activation/producer provenance, saved-summary owner/lifetime, complete/refusal status. Activation/provenance need not be semantic Result identity; their association must still be verified.
* ConsumerContract: consumer implementation/rule/schema, stage/mode, every read dependency and projection, input interpretation/ABI/effect/trap roles, permitted writers/aliases and lifetime, required transition/effect obligations, equality definition. Unknown read means HOLD.
* Invalidation closure: reverse consumer edges for Answer and independent context/type/interface/diagnostic/authority/aggregate dependencies, graph/version/epoch, dirty state and outstanding updates. A contract change must invalidate its transitive readers; equality cuts only a verified unchanged boundary.
* TransitionReceipt: each target's scalar-copied prestate/poststate at each merge, exact site/ordinal/target/base/arity/four contributions, support/poison before query/after query/after caller, status/diagnostic/trap, logical charge and actual cache work, current admission and valid-last publication.
* SCC/work scheduling contract: component membership and external inputs, pending obligations, order-sensitive merge behavior, convergence/iteration budget and failure policy. The inspected historical code has round-based iteration; no new generic worklist implementation was found or asserted.

Native refusal evidence is still needed for stale owner/context, field/reader/rule invalidation, missing/reordered edges, wrong arity, neutral→poison, omitted caller poisoning, altered diagnostic/charge, partial publication, and insufficient current admission. Encoded-field inequality and old shadow equality do not substitute for importer/admission rejection. No old15-shadow or40-call rerun is recommended.

## SOURCE facts and lineage blocker

The current16 module files were searched directly: no `vw-`, `cq-original-query` or stage6 shape memo path occurs. Current41 SHA4ed9… and fresh native761856bb… describe the current product producer. Native7618 may build a separately registered historical-analysis subject; that does not make the subject's stage6 path current product analysis. A readonly current-stage6 observer is therefore blocked until a truthful subject is selected or the analyzer is separately integrated. No product source was edited.

The historical `41-result.kotoba` is a different extended source. Selected concrete reads/writes:

* Lines2997–3012 memo key match/save use four prior/current entry bounds and stored validity; these inspected writers do not store an owned return-summary receipt/context/activation/mode/input-contract association.
* Lines3048–3076 replay reads each edge contribution, target widths10..13 and current aggregate6..9; -1 skips, other values merge using the original minimum rule. Query admission reads control1, support15, poison14, memo validity/link/head and key match29; miss runs fresh mode1, hit only replays.
* Lines3183–3191 return-summary controls9/11/12/13 depend on current candidate10 and flow data. Lines3246–3267 reset/run establish current flow owner5 and mode20, then overwrite scratch. No fresh summary is produced by the inspected hit branch.
* Lines3387–3415 shape caller checks support/poison and may zero outgoing target aggregate6..9 through poison-edges after support loss. Bounds finish reads export/kind/reachability and sets changed control25; shape-fixed iterates until no change, error, or round127 refusal. One query result equality cannot establish that whole loop is stable.

These are selected source observations, not the full61-definition/11-reader closure or a proof that every excluded field is irrelevant. The root's new consumer contract incorporates the necessary Answer/Transition and SCC distinctions. Its current status should remain **SOURCE acceptance contract with lineage/ownership/read/invalidation/runtime/cost gaps**, not downstream-stop readiness.

Costs remain separate: measure seal/encode/hash/lookup/validation/replay/publication/failure and cold/warm amortization before claiming analysis savings. Generated-code Embench runtime, original19 semantics, selfhost fixed point and quiet-host C comparison remain independent final gates.
