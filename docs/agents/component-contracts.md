# amu component and ticket contracts

Moved verbatim from `AGENTS.md` (JUN-974, owner decision 2026-11-19: ticket-level contracts may live under
`docs/agents/`). The text below is unchanged; only its location moved. `AGENTS.md` keeps an index of these
sections. Before you change one of these components, read its section here.

## Bounded canonical Kototama native frontend (JUN-369)

`compile-kototama` requires the explicit `kototama.pure-i64-aot/v1` profile,
target and positive fuel. `seed/83-kototama-i64.kotoba` validates canonical
DAG-CBOR and translates only its closed scalar slice into compiler-owned
source for the unchanged adopted core. Original names are data, never source.
Reuse the lowerer's existing annotation interface and native OP-FUEL; do not
introduce another compiler, an interpreter or a hosted fallback. The native
ordered gate is built by Amu; Python only stages fixed vectors and observations.

This is an entry-only, nonrecursive, heap-free engine profile, not whole-VM
or Murakumo Cell admission qualification. State/effects, CID-bound cache,
fresh admission, receipts, recursive methods and runtime arguments remain
separate gates. See `docs/kototama-i64-aot.md` for exact limits and protocol.

## Scoped flock candidate (AWAI-81)

The wire-35 FLOCK/UNLOCK provider and its local native gate are documented in
`docs/native-scoped-flock.md`. Keep one cooperative lock per process, preserve
root/no-symlink checks and the existing seccomp boundary, and never allocate
the lock path with mmap after seccomp. Local AArch64 gates do not qualify
x86 host execution, default artifact promotion or release/CDCI selection.

## Bounded native receipt profile (JUN-370)

`kototama.pure-i64-receipt/v2` retains the v1 language/admission and allows
budget0. `seed/84-kototama-i64-receipt.kotoba` delegates ordinary instructions
to the existing scalar emitters; its sealed fuel/quotient fault edges and
fixed process envelope report canonical overspend and typed failures. Keep
the adopted core and existing emitters authoritative. The native ordered
gate checks raw observations, named resource refusals and actual metering
removal; Python only stages bytes/processes. The unsigned process receipt
is not a signed VM receipt, fresh node admission or an in-process unwind ABI.

## Budget-independent local cache (JUN-371)

`seed/85-kototama-i64-cache.kotoba` retains that closed language and reuses
the same emitters, but separates immutable code identity from the fresh
stdin72 invocation context. Cache identity binds Program CID, compiler/source
digests, decoder/value/fuel/profile/ABI, target baseline CPU, optimizer and
empty imports. Never persist authority, approvals, lease or mutable fuel in
the code cache. Reject a missing/mismatched context before any guest code.

The dedicated pinned factory builds `seed/cache/host.kotoba` with a fixed
compiler/source policy, using the existing native CDCI supervisor primitives.
It is a bounded local x86 host, separate from the two mandatory CDCI roles.
Keep the private16-slot/1MiB-image/concurrency1/compile120s/guest5s bounds and
fresh empty-authority admission on every hit. Runtime deadlines are host
failures, never fabricated fuel receipts. Remote signatures, effectful grants,
Cell integration and an ARM supervisor require separate qualification.

## Locked shared components (JUN-93)

Complete47 adds seed/98-x86_64-project.kotoba: a pure, locked typed project
adapter for x86_64-linux kx64-v1 and the existing native runner. Preserve every
module/declaration, immutable source locks and all18 normal adopted core files.
No effect grant, kernel heap runtime or floating profile is introduced.
The native project fixture/refusal gate and independently source-pinned shared
text/DOM/text-edit goldens must execute on actual x86 Linux. ARM code generation
alone cannot qualify x86. Source-owner pins live in shared-browser-components.json;
text's canonical owner is kotoba/lib/kotoba.text, not its archived repository.
CSSOM/surface/kernel desktop/dapps/persistent restore remain later JUN-93 gates.

## Native iteration scheduling and observations (JUN-332)

The Apple Silicon diagnostic FS2 runtime now has scoped F metadata and E
range reads in `seed/macos-fs2-runtime-packager.kotoba`. Check the reviewed
word derivation and signed probe in
`docs/evidence/mac-fs2-ef-20261026/README.md` before claiming Mac media
coverage. Its larger arenas are diagnostic capacities; the full wire-35
provider, compiler fixed-point requalification on this expanded runtime
and release remain separate.
The repository-local Mac bootstrap and its current fixed-point gate are
tracked separately in JUN-417. Earlier probe receipts retain their exact
historical pins; source admission of a probe does not qualify its runtime.

Run new heavyweight local native commands through
`python3 scripts/seed/native_build_queue.py -- <command>`. Its default shared
admission directory is `~/github/workspaces/codex/native-build-slots-v1`;
`KOTOBA_NATIVE_SLOT_DIR` selects an existing host-wide directory. Cooperating
invocations share two slots across worktrees. Existing unmanaged jobs are
outside that limit; do not stop them or call a busy host quiet. CI uses
`RUNNER_TEMP/native-build-slots`, two gate groups maximum per runner, with
the longest derivation admitted first. Use `--jobs 1` for a serial comparison.
Keep one slot capacity per directory; a mismatch refuses.

Local source/image preflight and locked native project controls run before
the full bootstrap. `check-native-cdci.py --stage preflight` supplies early
native24/refusal/parent-death feedback only; it never qualifies the rebuild.
The default full stage repeats every control and the actual controller.
`controller-profile.json` observes /proc and wait4 outside the native process;
it does not change its binary, arguments, environment, limits or verdict.
Source/image/fixed-point/case/fuel/arena/refusal requirements are unchanged.
There is no new cache substitution or legacy runtime fallback.

## Immutable SIR label proofs (JUN-332)

`glx-prepare` owns the module-local unique-label index after preparation and
before emission. It is restricted to SIR larger than the T2 rewrite limit;
changes to that rewrite scope or any emission-time SIR mutation require
invalidation/requalification. Keep arbitrary suffix/accumulator scans and the
CCF excluded window/reserved operands exact. No CODE/FIX prefix proof is cached.
The index temporarily uses existing heap capacity and a disjoint alen-state
cell. No-room falls back to original scans, and emission releases/zeroes the
index. Keep the original G size and all fuel/arena limits.
The full-prefix native differential oracle and nine successfully built but
semantically refused guard-removal mutants run on both native ARM and x86
in the shared two-slot gate plan. Original gate groups remain mandatory.

## Explicit selfhost parameter types (JUN-27 / JUN-332)

The three `ck-r6c-doctail` / `ck-r6c-dt` / `ck-r6c-lit` implementation
parameters `S` are explicitly `:string`. This avoids repeated inference
rounds when building the compiler sources; it is a source-build optimization,
not a new inference algorithm. Keep the complete unannotated counterpart
in `check-native-label-index.py`: compile it afresh, require whole-image
byte equality with the annotated source, and execute both its semantic and
wrong-mode controls on native ARM and x86. All nine original mutation
controls and every existing gate remain mandatory.

Do not memoize mutable CODE/FIX prefix proofs using query/counts alone.
`check-prefix-cache-counterexample.py` executes same-extent rewrites that
the original validator must refuse. Any future reuse needs complete
write-aware invalidation, including direct memory-vector writes, and a
fresh native differential/refusal/resource oracle.

## Native incremental identity foundation (JUN-332 / JUN-358)

The native `definition-cids <file.kotoba>` candidate (seed/DEFINITION-CIDS-MANIFEST, entry
`seed/99-definition-cids-entry.kotoba`, gate `scripts/seed/check-definition-cids-native.py`) is documented in
`docs/definition-cids-native.md`; it grows no adopted manifest.

`seed/04-definition-cid.kotoba` is a bounded payload-v2 codec candidate,
qualified separately on native ARM/x86 against the pinned canonical bytes
and CIDs. It is not in the adopted FULL-MANIFEST. A supplied canonical payload
is not proof of checking, SCC identity, object-cache validity or admission.
Keep the existing canonical identity authority and all six sealed inputs;
never relabel a source/SIR hash as a canonical DefCID. Unknown/unsupported
values refuse. Native constructors, refusal and built mutation controls are
mandatory before widening the codec. See `docs/native-incremental-build.md`.

## Native vector zero highwater contract (JUN-27 / JUN-332)

The native runtime tracks an absolute item highwater in
private global byte offset760, separately for ARM/x86. It may skip clearing
only the untouched suffix of its fresh anonymous mapping. Descriptor creation
raises the highwater; arena rollback must never lower it. Existing item
writers finish through descriptor creation or write within a previously
described view. New writers require an audit of this invariant.
Keep all vector/item/region limits, five rollback counters, fuel and refusal
conditions. Native scope reuse, partial old/new ranges and missing/relative
watermark and last-word mutants must pass before adoption. Wasm's context is
separate and its own offset760 must remain unchanged. Source changes alone do not qualify
the current root/public/role pins; finish native rebuilding and all gates.

Owner-approved exception (2026-10-26, KOTOBA-144): an explicit
`--runtime-profile large-vectors-v1` may select67,108,864 vector descriptors
for a native Linux artifact. The default `standard-v1` remains4,194,304.
Keep private growth-region rows at4,194,304, all item/pair/string/individual
vector limits, rollback/highwater checks, authority, fuel and refusals.
Never infer this profile from workload names, failures or speed. Unknown,
malformed and duplicate profile declarations refuse. This is implementation
approval only: both ISA gates, rebuilt root/public/roles and new executed
boundary/mutation controls remain required before adoption or measurement.


## Closed native benchmark measurement host candidate (KOTOBA-145)

Owner approved a separate hash-pinned native measurement-host factory on
2026-10-26. This is not a third CDCI role or a public privileged guest mode.
Keep ordinary guest/private-runtime refusals, the original19 libraries and
registered counts, every resource limit and offset760 physical highwater.
Only exact pinned host/registry source may enter this factory. Owner scope
decision2026-10-26: qualify the declared ARM host through both native ARM and
native x86 compilers, with exact equality to the host/payloads actually run
on ARM. A native x86 measurement host and x86 payload admission are separate
follow-up work, not support implied by that equality. Both ISA compiler fixed
points, native refusal/mutation controls, full accounting and all native CI
remain mandatory before this scoped qualification. Do not promote descriptors
or make timing/performance claims from source or export admission.

## Native instruction-class filter qualification

The CCF high-byte mask is immutable and must conservatively include every
PC-relative class. Keep word bounds and all original target/refusal checks.
Do not cache mutable CODE/FIX prefix proofs by their counts. The native gate
adds131072 comparisons against the original evaluator and four built/executed
mutants on both ISAs; all previous gates and uncached main/full remain required.
The candidate must rebuild core/controller/root/public pins and pass fresh
native qualification before its qualification flags are promoted.

## Native checked identity / SCC prototype

`seed/05-checked-definition.kotoba` and `seed/06-definition-groups.kotoba`
remain outside FULL-MANIFEST. Preserve the current payload-v2 authority,
profile6/desugar2, one binder counter, direct dependency CIDs and the exact
scc-v1 minimum/rank/tie over at most eight members. The fixed-root traversal
must match the retained native exhaustive minimum; do not widen its one-byte
index/graph/codec bounds from a small-group speed result. Run native kr/name/check freshly;
caller-supplied checked flags, unsupported schemas/effects and oversized
groups refuse without partial identities. Immutable normalized member bytes
may be reused inside that one identity calculation; only structurally recorded,
native-created group-reference leaves may change under permutations.
Keep native full-payload equivalence, independent oracle, version-drift
refusals and actually built/executed mutants on both ISAs. This is not a
persistent object store, a build-cache hit, a native admission verdict or
qualification of the full Seed frontend. See docs/native-incremental-build.md.

## Native definition-object build prototype

The identity/object prototypes share `seed/05-definition-graph.kotoba` with
the complete checked Seed SIR call-graph observer. Keep sparse append-history
validation, all vertices, iterative traversal, member-index coverage and the
sealed-write refusal. The DFS workspace becomes component heads after
traversal; node9 then means next-member+1, not a live DFS parent. Preserve
name ordering in canonical groups and source ordering in object bindings.

The shared native graph gate exhausts66067 directed small graphs against
reachability, covers8191-vertex paths/cycles, freshly imports the complete
pinned compiler manifest, checks its edges through independent FF-SIR intervals and
compares complete partitions with an independent observer oracle. Every
named mutant must actually build/execute and hit its native guard. Existing
identity/object oracles, SCC<=8 refusal and all selfhost gates remain required.

SIR omits inlined constants and stateful templates. Retain those declarations
as explicit unresolved vertices, and record every CALLI owner. A direct-only
call graph is never a canonical identity or admission proof. The complete
source/checked-KIR bridge, larger-SCC identity, literal/type/effect handling
and trusted producer-image binding remain separate requirements. Do not
accept a persisted graph or a caller's checked/sealed flag as a fresh plan.

`seed/07-definition-objects.kotoba`, `08-definition-object-emitter.kotoba`
and `09-definition-build.kotoba` remain outside FULL-MANIFEST. This bounded
pure scalar KIR route captures the original xg emitter's unlinked bytes and
symbolic fixups and reuses an entire SCC only after complete fresh identity
and target admission. Preserve reference ELF byte equality, equal-CID binding
occurrences, all nine build-context seals, private immutable durable storage,
fresh label/definition resolution and final range/fuel checks. Do not widen
literal/type/profile bounds from synthetic format checks. Keep the separate
native object gate and actually built/executed mutants on both ISAs.

The test observer supplies the compiler-image context. This is not a trusted
production image-binding host, whole Seed cache or CI speed qualification.
Same-principal compiler/storage administration is trusted; a checksum-valid
private object is not an untrusted remote code-admission proof. Keep the
existing uncached full derivation and all qualification gates intact.

