# Retire the hosted C1/C3 generation graph

Tracking: [AWAI-66](https://linear.app/kotobalabs/issue/AWAI-66), Kotoba Labs.
Codex thread: 01a15eb9-ef0b-73f3-a095-1a1af90d3a21.

The owner requires canonical Kotoba, Amu selfhost and a loaderless native
controller and two CDCI gates. A C-loader pin, generated C header, equality
with a C embedding, hosted interpreter or Node/KBB generator cannot remain a
prerequisite. This cleanup removes that obsolete generation/comparison graph.
It does not implement or qualify the remaining native closure.

## Removed consumers before producers

1. Remove six npm entries: the loader warning comment/compile command, the
   decision generator, both decision-driver commands and the boundary driver.
   Remove the two corresponding decision/boundary steps from the old workflow.
2. Remove the three Node/KBB comparison drivers for C1 decisions, C3 handlers
   and typed export-boundary behavior. They build/run a C loader, and the
   boundary driver also requires a hosted interpreter comparison.
3. Remove both Node/KBB generators. One compiles and executes decisions through
   a C loader to write C source; the other refuses to write native decision
   artifacts until their bytes equal the C source embedding. That cycle is
   retired rather than made a condition on Amu selfhost.
4. Remove the corresponding generation/equality instructions from canonical
   source headers and legacy cache documentation. Preserve the complete
   decision/name/boundary forms, public exports, indices and exact strings.

The hosted cache/source-SHA assertion is also retired, including its two
unused imports. Even a comment edit changes a raw source SHA and makes that
assertion demand the deleted generator. It cannot remain an acceptance
condition or be repaired by relabelling old artifact source hashes. The full
assertion is recorded by immutable source/blob provenance. Current sealed
artifact identity and native qualification remain required and open.

## Complete historical corpus remains identifiable

The immutable pre-retirement source is Amu commit
`7872d10f587a2d4a0b92bc124037915e34c0cf26`. Every case, control, literal,
boundary sweep, refusal/resource assertion and differential observation in
the removed drivers remains recoverable as a complete Git object. The exact
paths/blobs are in [the retirement record](native-decision-host-retirement.edn).
No small smoke set replaces that domain and no successful placeholder is
installed. Historical observations retain their original compiler/runtime
provenance and cannot certify a new artifact.

The historical embedded artifact payloads, loader source, classification
data and adopted/benchmark evidence are unchanged. They remain migration
inventory and provenance, not current native qualification. Their remaining
consumers and eventual retirement are still open.

## Required native replacement

Build the **complete** canonical C1 and C3 components with the qualified
Amu-produced compiler for the image ISA. Admit their actual seals, source and
lock identities, exports, context ABI, authority/resource limits and code
placement through the complete native packager. The native constructor must
use these actual artifacts; a stale hosted cache or source-supplied successful
seal is not a fallback. Keep the real grant, provider, kind, scope and named
refusal behavior.

The complete export-boundary component and actual typed argument/result
mechanisms must preserve its full token/type/value/traversal domain. The
current static command's arity-zero entry does not qualify general exports.
Port the full positive/refusal/resource/control corpus into canonical Kotoba
and run it through the selfhost-produced native route with recorded process,
compiler-generation, source/lock and artifact evidence. That work remains
open; no tests or project/compiler/generator/loader implementations were run
for this source cleanup.

Byte capability kinds/lowering/providers/results, arbitrary raw-file/hash/I/O,
whole resolver/materializer/authoring callers, exact decision artifacts,
remaining ABI/runtime and actual Amu self-rebuild/CDCI remain open. Existing
native vector/bytes/package drafts are source candidates only.

Only the two old workflow steps named above are removed here. The remaining
Node/NBB/C/Python workflow inventory is still to be retired or replaced; this
PR does not claim that Amu's CDCI is native-only. No native gate is declared
green. The separate merge-guard workflow/required-context approval is held
separately. No protection, live service, production route or package lock is
changed by this cleanup.
