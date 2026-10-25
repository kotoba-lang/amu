# Agent rules

## Selfhost is the top priority

- Use canonical `.kotoba` source and an Amu-built native compiler for the
  compiler, CLI, build graph, packaging and operational tooling. This outranks
  features, new targets and benchmark publication. Details:
  `docs/selfhost-priority.md` (owner decision 2026-10-22).
- Remove CLJK/CLJC/CLJS, NBB, KBB, Clojure, Java/JVM, GraalVM, Node.js and
  C compiler/loader/runtime dependencies from that closure. CLJK is not a
  retained final syntax-sugar surface. C-loader pinning is not acceptance.
- Only a compiler built and rebuilt by Amu selfhost qualifies. Historical
  hosted builds and C-loader receipts remain labelled historical evidence;
  they do not qualify the replacement route.
- Do not add a legacy host, C loader or hosted packaging fallback.
  Unreachable files stay on the scoreboard as refused, with the reason.
- Compiler benchmarks (Embench etc.) are published as selfhost results only
  when taken with a selfhost-built compiler on a quiet host.

## The measured Embench compiler is the compiler core

- Extend the adopted `seed/MANIFEST` compiler lineage for Amu selfhost and
  the public `amu` / `kotoba` compiler. Preserve its frontend, lowering,
  optimization and backend behavior while growing the complete command and
  build closure. Do not replace it with an independently implemented core
  or make it an optional benchmark-only backend.
- `seed/compiler-core.json` pins the measured M104 baseline and the adopted
  M105 source lineage. ADR 0370 defines the integration and review order.
  Review and merge this lineage before unrelated feature work.
- Preserve the full 19-workload corpus, exact result/fuel/arena/refusal
  behavior and source/artifact provenance. A successor needs complete
  self-rebuild and conformance evidence before replacing the admitted core;
  a new score needs fresh measurements of that exact compiler.
- Historical C-loader results remain historical. This core decision does
  not relax the native-only build/execution contract above or qualify the
  public CLI, a new runtime, or CDCI through source inspection alone.

## Q9 compiler routes must use Kotoba / Amu selfhost only

- Q9 callers use the Amu selfhost-built native `bin/amu` (the `bin/kotoba`
  and `bin/kotoba-compiler` aliases resolve to that same image) for the
  qualified `check` and explicit-target `compile` lane. The public host is
  native Linux x86_64; other public hosts remain unqualified. See
  `native-product.json` and `docs/native-public-entry.md`.
- The public default remains an engine-neutral Kototama program contract.
  Its native implementation is still missing: omitted compile targets
  refuse `E2`, without an implicit AArch64 or legacy-host substitution.
  Use explicit `--target`; the retired Node launcher's `AMU_TARGET` routing
  is not current native behavior. Browser / Worker / WASI targets need
  their own native qualification before callers can depend on them.
- The build and execution closure must not invoke NBB, KBB, Node, Java,
  Clojure/JVM, GraalVM, a C compiler or C loader, including through wrappers,
  `resolveWithJvm`, compatibility adapters or packaging helpers.
- Missing/stale dependency locks, unsupported commands/targets and project
  linker gaps fail closed. Do not silently remove `--source-path`, ignore a
  module lock or fall back to a legacy host to make a component compile.
- New Q9 compiler/test routes are authored in Kotoba, built by Amu selfhost,
  and executed as qualified native artifacts or selfhost-produced Wasm in
  the declared host. JavaScript/Wasm output does not authorize a Node/NBB
  compiler host. CDCI is limited to Amu selfhost and Kotoba native as
  loaderless `x86_64-linux-static` ELF artifacts.
- Preserve the positive/refusal and lock-failure corpus while migrating it
  to the native route. Record forbidden-process traces, compiler generations,
  source/lock pins, artifact hashes and actual execution results. Missing
  native functionality stays blocked; source admission alone is not a pass.

## Native CDCI and retired public entry

The integrated FULL47 source retains native CLI/CID/FS2, the native i64
receipt profile, all live/desktop modules and all18 normal adopted core
modules. Root and public images are rebuilt from this exact graph with
native ARM F1=F2, core generations, runtime cases and admission/refusal
proofs. The controller and both gate identities are preserved from the
qualified45 source. Current47 acceptance requires terminal exact-head
native ARM/x86, receipt-profile, controller/public and locked consumer CI.
Historical ARM/QEMU receipts remain bound to their own sources.
The closed v5 project reserves low20KiB for non-live context/catalog. The
v6 PCI candidate has128KiB RW storage and a64KiB private floor; its copied
BAR catalog starts at context20480. The v2 live ABI and v3 private user/desktop context provide separately
versioned queue/arena/capability/domain regions, with native admission and
actual guest receipts; full scheduling and shared Browser remain separate.

- The complete candidate uses `seed/FULL-MANIFEST` (47 modules), retaining
  every adopted core module. Static OUT is 12MiB because the complete
  TCP/spawn image exceeded the old 8MiB bound. The complete static profile
  also uses LitB1MiB and TOK786432 and NODE786432 and MM-WORDS31,064,064 (<2^25). Heap size, expected results,
  all19 workloads and all24 runtime fixtures remain unchanged.
- `seed/cdci` owns the Kotoba-native controller and gate. Its two mandatory
  roles are Amu selfhost and Kotoba native; legacy fleet/authoring labels
  are not extra gates. Privileged role sources, images and inputs are
  pinned; changed source needs matching newly built artifacts and proof.
- GitHub Actions/Python can stage bytes, launch test processes and transport
  artifacts. They do not replace the native controller's ordered verdict
  or turn source admission, cached historical receipts or pending execution
  into a successful native gate. Keep artifact qualification, terminal CI
  status and live service deployment distinct.
- Old Node/NBB/KBB launchers, package manifests, JVM deps and former README
  are complete non-executable historical text under
  `docs/retired/legacy-public-entry-20261023`. They are not fallback tools,
  installation inputs, current Q9 instructions or acceptance blockers.
  Preserve their corpus while porting genuinely missing public behavior.


## Shared agent rule

These rules apply to every agent. Migrate and qualify whole components,
including their launch/build/packaging dependencies. Keep historical
measurements distinct from current qualification and preserve unrelated WIP.

The native-only entry refuses `--format platform-linked` with E2. The
optional provider backend source and corpus are retained, but libc/dynamic-
loader execution is excluded from mandatory native CDCI. The static
launcher, complete core, all24 native cases and hardening remain required.

The linked GPU-provider fake-device/Vulkan/libc qualifications are also
excluded from mandatory native CDCI: they require the refused C-linked
format. Their source and corpus remain preserved, and provider qualification
is blocked until an Amu/Kotoba-native route exists. Do not mark those
excluded checks passed through the two bounded native compiler roles.

The public-product native check must receive the current complete compiler
receipt (`--complete`) and match the actual entry to all3 current native F
images/current FULL-MANIFEST bytes. An older self-consistent descriptor is
insufficient. Runtime/target changes must regenerate affected role/source,
root and product pins and re-run native positive/refusal/resource checks.

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

## Bounded native receipt profile (JUN-370)

`kototama.pure-i64-receipt/v2` retains the v1 language/admission and allows
budget0. `seed/84-kototama-i64-receipt.kotoba` delegates ordinary instructions
to the existing scalar emitters; its sealed fuel/quotient fault edges and
fixed process envelope report canonical overspend and typed failures. Keep
the adopted core and existing emitters authoritative. The native ordered
gate checks raw observations, named resource refusals and actual metering
removal; Python only stages bytes/processes. The unsigned process receipt
is not a signed VM receipt, fresh node admission or an in-process unwind ABI.

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


## Native CI derivation and independent ISA qualification

Fresh ARM bootstrap/one-compiler transport precedes separate ARM and x86
qualification jobs. Transport alone is never qualification: all six native
job executions (including both shared-module matrix entries) must succeed.
Every previous ARM/x86 gate, uncached main/full tier and fresh controller
verdict remains required. The ARM artifact includes root and final generations
for unchanged native producer pin checks after transport. No compiler/image
bytes, limits, case expectations or native gate commands change in this split.
