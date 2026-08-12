# Amu

Amu is the multi-target, deny-by-default compiler for the safe Kotoba
language. The repository is `kotoba-lang/amu`; the name evokes Japanese
「編む」— weaving checked source, typed KIR, and target artifacts together.

The existing `kotoba.compiler.*` namespaces, `kotoba-compiler/1` wire marker,
and `bin/kotoba` launcher remain compatibility APIs. New automation should use
the `io.github.kotoba-lang/amu` dependency coordinate and the plain-Node
`bin/amu` front; `bin/kotoba-compiler` delegates to it.

That primary Node front resolves its pinned source closure from
`deps-lock.edn`, bound to the exact `deps.edn` digest. Amu CI checks the lock
hermetically and compiles/executes a representative native artifact with JVM
executables removed from `PATH`; every dependency pin change must regenerate
the lock with `nbb scripts/lock-classpath.cljs`.

Primary Wasm and ordinary-native compilation are policy-bound as well:
`:budgets :fuel` controls the emitted Wasm module or sealed native fuel ABI
rather than admission alone, and every compile publishes the same sealed
`:kotoba.provenance/v1` sidecar as the JVM compatibility path.
`:language-profile` controls semantic analysis and HIR-cache identity rather
than being mistaken for a capability grant. Worker cache hits integrity-check
and reproduce both Wasm output files. Primary compiles stage and `fsync` the
artifact, provenance, and a deterministic `:kotoba.output-set/v1` marker in one
private directory, then publish the marker last. `amu verify-output-set FILE`
rejects absent, stale, basename-renamed, or byte-mutated sets; the marker is commit
evidence, not a publisher signature.

The accepted [worldwide 95% platform coverage roadmap](docs/adr/0001-worldwide-95-percent-platform-coverage.md)
defines the planned native, WebAssembly, GPU, NPU, server, mobile, and IoT
targets. It is a completion plan, not a claim of current platform support.

Compile latency is measured as a versioned cold-process and persistent-worker
matrix. See [Compile performance](docs/performance.md) for the bounded worker,
verified cache contract, phase timing, and reproducible benchmark command.
The same document also defines a five-engine runtime comparison for Amu native,
Amu Wasm, Rust, Clojure, and ClojureScript. Its ratios are evidence for one
declared workload and host, not a universal language ranking.

The pinned native path lowers scalar control values through versioned
GMIR/MIR. MIR schedules complete single- and multi-phi predecessor edges as
parallel copies: acyclic joins need no phi frame, while register cycles share
one bounded temporary slot. Amu executes the resulting bytes on both x86-64
and AArch64; it does not reconstruct or reorder the schedule. Non-escaping,
non-empty fixed records whose fields are only `:i64` or `:bool` are scalar
replaced into ordered SSA bundles before GMIR, so a record-valued `if` emits one
phi per field without heap allocation. Escaping, nested, and non-scalar records
still use the legacy path. Non-escaping sealed variants whose payloads are only
`:i64` or `:bool` likewise become an internal tag-and-payload SSA bundle;
variant-valued `if` emits two phis and `variant-match` lowers to target-neutral
comparison control flow without a variant stack region. The closed scalar
subset now also crosses an exported native boundary; nested/non-scalar payloads
and a general recursive aggregate ABI remain outside this slice. This is not a
Rust-wide performance-parity claim.

The pinned native closure now publishes aggregate-boundary contract v3. It
names the existing escaping-record representation precisely: one declaration-
ordered pair-chain handle, owned by the host context and bounded by 4,096 arena
cells. It adds the scalar-variant boundary as a context-owned pair of
declaration ordinal and payload, while preserving the canonical public value
`[type case payload]`. It also records that every register in the extracted
allocator profile is call-clobbered. Scalar direct calls lower through
GMIR/MIR/MC v3 with
per-function frames, live-value preservation, parallel argument assignment,
and a single-word return register. Straight-line callers now materialize only
values live across a call; the representative module shrinks from 123 to 84
bytes on x86-64 and from 108 to 88 bytes on AArch64. Record and variant values remain held at
function boundaries. The pinned verifier consumes this vocabulary, re-emits a
two-function module, and keeps its aggregate predicate independently derived.
Portable bool/bit negation, i64 shifts, and every admitted i32 wrapping
operation also use this machine-IR path. The i32 names normalize into portable
word arithmetic and shifts before target selection; the real-loader table
executes the same rows on both native ISAs.
Scalar f64 arithmetic, min/max, sqrt, bit-pattern conversion, ordered
comparisons, and unordered detection now follow that boundary as well. The
real-loader table includes ordered values and NaN cases on both ISAs.

Entryless native libraries also have a measured scalar host boundary. The
executor reads parameter and result types from the selected sealed export,
not an absent `main` signature: host booleans cross `:bool` slots as native 0/1
words and return as booleans, while integer and boolean host values cannot
impersonate each other. Amu tests this by compiling and signing a two-export
Kotoba library and invoking it through the real native loader process. Strings
now cross that same boundary as bounded canonical UTF-8 copies: inputs are
placed in the loader arena before guest entry and selected results are copied
from either code literals or the dynamic pool before process exit. Raw pair
handles never become host strings. Scalar records cross as exact-key maps, and
qualified scalar variants cross as exact canonical vectors. The variant loader
validates its arena handle, declaration ordinal, and boolean payload before a
typed supervisor report is copied back; raw handles never become host values.

The first reproducible coverage snapshot can be audited with:

```bash
bin/kotoba -M coverage data/coverage/interactive-2026-06.edn \
  --dataset data/coverage/statcounter-os-worldwide-2026-06.csv
```

A platform marked `release` is counted only when every manifest evidence digest
resolves to a currently valid Ed25519 envelope from a trusted, non-revoked
signer. The signed statement binds the platform, native/Wasm paths, exact target
profiles, conformance and runtime digests, CI run, test time, and expiry.

## Execution policy

The compiler has one source-admission and KIR pipeline. Its primary application
artifact is a Wasm Component/profile: a component is portable, linked through
typed WIT imports, and receives no authority except the capabilities admitted
by its host. `wasm32-wasi` does **not** mean ambient WASI access: the current
profile rejects ambient WASI imports and expects a closed capability adapter.

Direct x86-64/AArch64 AOT remains a supported backend for aiueos boot/kernel,
engine, driver, root-key adapter, and explicitly trusted low-level primitives.
It is not the default route for an ordinary Kotoba application. The compiler
must not duplicate runtime policy: `kototama` owns component linking/execution
and `aiueos` owns grant decisions, while a small native host independently
enforces the resulting grant. See
[`ADR-2607252500`](https://github.com/com-junkawasaki/root/blob/main/90-docs/adr/2607252500-kotoba-wasm-component-first-execution-boundary.edn).

The portable reference runtime also defines the identity-to-capability
boundary. A host resolves and verifies an identity proof (DID or another URI
scheme) and supplies a sealed principal, delegated grant, local policy and
evidence hashes. Immediately before each provider call, Amu intersects the
exact request scope with the program's admitted capability set, the delegated
grant and local policy. The runtime does not resolve DIDs or expose ambient
identity authority. An authorized call can emit a
`kotoba.run-receipt/v2` whose executor signature binds the resulting authority
decision; receipts without dynamic authority remain compatible v1 receipts.

For production native effects, the dependency and evidence direction is
strictly one-way:

```text
Kotoba semantics / provider types
  -> Amu admission and sealed artifact
  -> kotoba-native machine code and aiueos image ABI
  -> aiueos C-free boot, kernel, process, capability broker and provider
  -> Amu backend qualification receipt
```

`aiueos.vm`, `aiueos.hvt`, Tender, Linux and the retained C kernel may test or
serve as reference oracles, but their success cannot flow upward as production
native qualification evidence. Amu owns neither scheduling nor syscalls. The
current exact gate is `backend-provider-qualification-v2.edn`; native remains
pending until the aiueos C-free CPL3 path supplies runtime, semantic-vector and
empty-foreign-code receipts. See ADR 0240 and aiueos ADR-0013.

Project compilation accepts repeated `--source-path ROOT` arguments to link
explicit package roots into one closed graph. Every dependency remains
confined to one of those real paths. If the same qualified namespace exists
in multiple roots, compilation rejects the ambiguity instead of selecting a
package by argument order.

### CID-pinned modules

Path resolution is ambient: what a build compiles depends on what happens to be
on disk, so the same source can compile to two different artifacts on two
machines and neither build can say which inputs it actually used. `--module-lock`
resolves `(:require ...)` through a lock that names every module by CID instead.

```sh
# Pin a path-resolved project once.
kotoba -M module-lock src/example/app.kotoba \
  --source-path src --blocks .kotoba/blocks --output kotoba.modules.edn

# From then on, compile by CID. No path search, no fallback.
kotoba -M compile --module-lock kotoba.modules.edn --blocks .kotoba/blocks \
  --target wasm32 --output app.wasm
```

Bytes are read from the block directory and rejected unless they hash to the
CID the lock names, and a `:require` for a namespace the lock does not pin is an
error rather than a reason to go looking. `module-lock/lock-cid` gives the whole
resolved input set one identity, so a receipt can bind a value that changes
whenever any input does.

This is deliberately distinct from the semantic definition CIDs in
`kotoba-lang/codebase`. A source-tree CID says which bytes were compiled; a
definition CID says what a definition *means*. Conflating them would let a
comment change invalidate a definition identity, or let two different sources
claim one.

All compilation results carry
`:kotoba.floating-point/ieee-754-f32-f64-v7`; restricted JavaScript artifacts
seal the equivalent policy. Scalar `:f32` and `:f64` provide exact bit
conversion, explicit arithmetic, ordered comparisons, unordered detection,
and checked-versus-lossy numeric conversions on Kotoba Script and Wasm targets.
Decimal literals remain f64; f32 creation always names its rounding, integer
conversion, or bit construction. The reader normalizes every f64 literal to its exact
signed-i64 IEEE-754 bit pattern before KIR, preserving signed zero and making
JVM and JVM-free compiler artifacts byte-identical. NaN payloads are not
observable and canonicalize to `0x7ff8000000000000`, including arbitrary NaN
payloads introduced through `f64-from-bits`; f32 observation similarly uses
canonical `0x7fc00000`. Implicit coercion, nested floating values, fused operations, remainder, square root,
transcendentals, and native or CLJS lowering remain rejected.
The v2 profile adds NaN-propagating square root, minimum, and maximum. Minimum
selects negative zero and maximum positive zero for opposite-signed zeros;
binary32 rounds after each named operation.
Qualified quarter-turn f64 sine and cosine use fixed Horner polynomials without
FMA, trap outside finite `[-pi/4, pi/4]`, and guarantee absolute error no larger
than `4e-15`. They do not delegate semantics to a host transcendental library.
Bounded wide-angle sine/cosine extend this through fixed split-`pi/2` reduction
over finite `[-8192*pi,8192*pi]`, with ties-away-from-zero quadrant selection
and a `5e-12` absolute-error bound. Outside that domain compilation artifacts
trap rather than silently accepting unreliable large-argument reduction.
Qualified near-zero exponential (`[-0.5,0.5]`) and near-one logarithm
(`[0.75,1.5]`) use fixed degree-18/21 kernels with a `4e-15` absolute-error
bound. They trap outside their domains and never call host exp/log functions.
Qualified `f64-atan2-bounded` accepts finite coordinate pairs, preserves the
IEEE signed-zero quadrant cases, and uses fixed octant reduction plus a
degree-39 odd kernel with `2e-15` absolute-error bound. NaN and infinity trap;
neither output target calls a host atan2 function.
`f64-exp-bounded` supports `[-512*ln(2),512*ln(2)]` through fixed split-`ln(2)`
reduction and exact binary scaling. `f64-log-bounded` supports
`[2^-512,2^512]` through sealed exponent/mantissa extraction. They provide
`1e-13` relative/absolute error bounds, trap outside those domains, and never
import host exp/log functions.

Conversions are explicit: `i64-to-f64-checked` rejects inexact integers,
whereas `i64-to-f64-rounded` names the IEEE rounding request.
`f64-to-i64-checked` accepts only finite integral in-range values;
`f64-to-i64-truncating` names truncation toward zero while still rejecting
NaN, infinities, and signed-i64 overflow.

## Stack topology & boundaries

This repository is the **foundation layer** of the kotoba stack: it depends
on nothing else in the stack (`security` and the pinned `kotoba-script` JS
backend only), and `kotoba` / `kototama` / `aiueos` / `kotobase` consume it —
as a library or as emitted artifacts — never the reverse. The canonical
topology, the dependency-direction invariants, and this repo's assigned
design-cleanup items (admission-gate ↔ backend capability parity, unified
`=` equality surface, kexe-loader validation in Kotoba objects, classpath-scan
robustness) are recorded in
[`docs/adr/0074-stack-topology-admission-backend-parity.md`](docs/adr/0074-stack-topology-admission-backend-parity.md)
(root authority: `com-junkawasaki/root` ADR-2607241100).

## Relationship to `kotoba-lang/kotoba` and `kotoba-lang/kotoba-lang`

This repository is the CLJC-native successor of `kotoba-lang/kotoba`'s
historical Rust "safe Kotoba" three-gate design (`policy.rs`/`subset.rs`/
`effects.rs`, removed from that repo `604896171b` 2026-07-01 — see
`kotoba-lang/kotoba`'s README, "Language — kotoba-lang & kotoba wasm"
section, which now states this attribution correctly) — not
`kotoba-lang/kotoba-lang`, which owns the source-extension/CLI/package
*contract* only and does not implement compile-time admission gates. The three gates map onto this repo's
`src/kotoba/compiler/frontend.clj` as follows:

| safe-Kotoba gate | Theorem | This repo |
|---|---|---|
| Subset | no ambient code/effect | `forbidden-heads` (`eval`/`require`/`import`/`set!`/`defmacro`/reflection/... rejected in `validate-expr`) |
| Capability | T3 — Capability Confinement | `cap-call` (a typed, arity-checked capability invocation form) |
| Effect | T2 — Effect Soundness | `direct-facts` + `infer-effects` (interprocedural fixpoint over `:calls`, converges through mutual recursion) |

`kotoba-lang/kotoba`'s reference-implementation grammar (`def`/`defn`/`ns`,
`if`/`when`/`let`/`do`, full arithmetic/comparison, `and`/`or`/`not`, strings,
recursion — no capability/effect gate baked into the language itself) and
this repo's admission-gated KIR-level grammar (`if`/`let`/`cap-call`,
`quot`-only arithmetic, heap-pair-encoded lists, plus `and`/`or`/`when`,
keyword literals, and `get`/`assoc` map literals as of ADR-2607150000 —
ported from/inspired by `kotoba-lang/kotoba`'s already-proven implementations,
all desugared to the existing `pair`/`pair-first`/`pair-second`/`if`/`let`
primitives with no backend/codegen change, since those primitives were
already host-imported capabilities rather than guest-managed WASM linear
memory even before this change — but still no `do` sugar, since this
profile's `let`/`defn` bodies are still exactly one result expression) are
two different, independently-evolved surfaces — narrower than before, but
still not fully reconciled into one shared grammar spec. See
`com-junkawasaki/root` ADR-2607141600 / ADR-2607150000 for the fuller
cross-repo analysis.

### Semantic-analysis reconciliation direction

The repository boundary is named **sema**, not frontend. In Kotoba architecture
`kotoba-sema` means source/forms through name resolution, type/effect checking,
capability elaboration, and checked HIR. This avoids the Web/app meaning of
"frontend". Existing internal `kotoba.compiler.frontend` namespace names are
compatibility implementation details and may move incrementally.

The semantic and machine-IR extraction waves are complete: `kotoba-sema` owns
source-to-checked-HIR analysis, `kotoba-hir` owns the validated envelope,
`kotoba-gmir` owns the target-independent closed contract, and `kotoba-mir`
owns target selection and explicit register-allocation state. This compiler
consumes those repositories while retaining orchestration and compatibility
entry points. See ADR 0222 for the dependency graph.

The pinned native closure now routes production KIR exclusively through
whole-module GMIR, target-selected MIR, allocated MC, and closed target
encoders. It publishes multiple exports from one layout and carries word-field
records, recursively nested one-word record handles, and option/result handles
under aggregate ABI v7. Record-payload variants reuse those handles. Callable
indirection is a sealed ordinal dispatcher, `apply` is capped at four arguments,
and native project linkage requires a digest-bound closed graph with no ambient
or unresolved symbols. Retired ISA emitters are unreachable from public
production and test routing; IR rejection has no fallback. Arbitrary code
addresses, open-ended variadic parameters, and dynamic unresolved linkage stay
rejected.
Terminal local calls release the current native frame and branch without
linking on both x86-64 and AArch64, so tail recursion no longer grows the stack.

The reconciliation target is not to expose this compiler's KIR-level
`cap-call`, numeric capability IDs, WIT imports, or provider callbacks as the
preferred Kotoba source language. `kotoba-lang/kotoba-lang`'s
`lang/guest-grammar.edn` remains the source-surface authority. The compiler
must consume or mechanically check that contract, perform bounded desugaring,
infer transitive effects, elaborate named operations into hidden typed ability
parameters, and only then lower to typed KIR.

Function effect annotations are public contracts or ceilings; inferred
effects remain authoritative for admission. Explicit capability values belong
in source only where authority is attenuated or delegated. Target-specific
numeric ID spaces may remain stable wire ABIs, but their semantic
name/schema/effect declarations should be generated from one language-owned
catalog rather than maintained independently.

Structured host data uses the org-owned `kotoba.value.v1` codec through
`kotoba.value.codec`. Compiler/provider adapters apply each typed ability's
`max-bytes` before decoding and after encoding; raw `bytes-ptr`/`bytes-len`
sugar is not a second data contract and is not added to authored Kotoba.

Definition identity is computed after desugaring, type/effect checking, and
ability elaboration, with the relevant contract versions sealed into the
identity. The executable plan and per-slice gates are documented in
`kotoba-lang/kotoba-lang/docs/kotoba-centered-migration-plan.md` and root
ADR-2607279200.

The first CI7 slice accepts one-argument qualified operations such as
`(http/post request)`, `(storage/transact request)`, and
`(llm/generate request)`. Request type is inferred from the lexical value and
result type from the enclosing typed context; the elaborated HIR is identical
to the existing `typed-cap-call` form. The semantic name, source operation,
effect, and stable compiler wire ID come from the language-owned catalog
vendored by the pinned `kotoba-sema` dependency as
`kotoba/lang/capability-catalog.edn`. Calls whose result has no typed context
still fail closed instead of guessing a provider schema.


GPU compilation now begins with a separate typed accelerator KIR rather than
allowing arbitrary shaders into scalar CPU KIR. `kotoba.compiler.accelerator`
validates bounded f32 elementwise/reduction kernels and deterministically emits
WGSL, CUDA C or Metal Shading Language. Sealed GPU artifacts bind KIR/code hashes and are independently
re-lowered during verification, including against attacker-resealed code. This
is the shared GPU compiler contract consumed by `kotoba-lang/num`; see
ADR-0002.
`.kotoba`, `.cljk` (CLJ-shaped Kotoba), and `.cljc` (portable common source)
are admitted source-discovery extensions. All three enter the exact same closed
Kotoba reader, type/effect admission and selected backend; none enables the JVM,
the full Clojure/ClojureScript reader, reader conditionals, or ambient host APIs.

```text
source -> inert reader -> typed/effect HIR -> SSA-like KIR
       -> wasm32 | x86_64 | aarch64 | cljs -> independent verifier -> admission
```

## Runtime: nbb-native for Wasm and ordinary native compile/check

`bin/amu compile`/`check` for `wasm32*` and ordinary `x86_64*`/
`aarch64*` targets runs entirely under `nbb` (ClojureScript on Node) --
**no JVM process is spawned at all** for those paths. Target-specific
entrypoints avoid loading either native emitter for Wasm and avoid loading the
other ISA emitter for native compilation. This matches the monorepo's
repo-wide runtime priority (`kotoba wasm runtime` first, JVM/`bb` demoted to
last-resort compat). The frontend reader/validator
(`kotoba.compiler.frontend`), the KIR lowering/compile-time oracle
(`kotoba.compiler.ir`), the wasm32 backend (`kotoba.compiler.backend.wasm`),
and capability admission (`kotoba.compiler.admission`) are `.cljc`, sharing
one source with the JVM path (no behavior fork, no second implementation to
drift) -- only a handful of reader-conditional branches differ, mainly
around representing `.kotoba`'s full signed-64-bit integer semantics as JS
`bigint` (`kotoba.compiler.cljs-i64`) instead of a JVM `long`, and reading
`.kotoba` source with a small purpose-built reader
(`kotoba.compiler.kotoba-reader`) instead of the JVM-only
`clojure.tools.reader` (its nominal ClojureScript sibling,
`cljs.tools.reader`, depends on several `cljs.core` internals nbb's SCI
interpreter doesn't resolve -- see that ns's docstring). `test/nbb/run.cljs`
(`npm run test-nbb-wasm32`) verifies that this path emits valid Wasm for every
`examples/*.kotoba` fixture plus dedicated i64/sleb128 boundary cases (true
i64 max/min, add-wraparound, the sleb continuation-bit crossing at 127/128).
Observable semantics, ABI behavior, resource bounds, and fail-closed rejection
are the compatibility contract; byte layout is not.

The `x86_64-aiueos-*`/`aarch64-aiueos-*` firmware and kernel packaging
targets, plus every other `kotoba` subcommand (`package-ios`, `sbom`,
`attest-release`, `sign`, `run`, receipts, coverage, etc.), still go through
`clojure -M:run` (`kotoba.compiler.cli`, JVM) for compiler commands and
`clojure -M:native-run` for `measure-runtime` / `run` -- native
ELF64/PE32+ packaging, signing, runtime execution, and release/coverage
evidence are not part of this nbb-native slice and remain JVM/compat. Ordinary
native nbb compilation still seals artifacts, runs the independent verifier,
and emits provenance before writing. The split mirrors the same way
`kototama`'s own R1 (JVM/Chicory tender) is demoted to "compat suite" behind
its R2 native-WASM-host path. `bin/amu` picks the path automatically
based on the subcommand and `--target`; nothing about the CLI's argument
shape changes.

`cljs` (ADR-2607151500) is a genuinely different kind of backend from the
other three: it lowers KIR to plain ClojureScript SOURCE TEXT, not machine
code or a WASM binary. `:cljs-kotoba-v1` (with `:cljs-node-kotoba-v1`/
`:cljs-browser-kotoba-v1` os-scoped variants, mirroring how
`wasm32-browser`/`wasm32-wasi` relate to `wasm32`) is in
`compiler/targets`, so every existing cross-backend consistency test now
also compiles through it. Since a cljs runtime already has real
heap-allocated persistent data structures, `pair`/`pair-first`/
`pair-second` become plain 2-element vectors + `nth` -- no hand-rolled
linear-memory heap simulation needed, unlike wasm32/x86_64/aarch64. KIR's
`if`-is-0-false and comparison-returns-1-or-0 conventions (neither of
which plain cljs semantics reproduce for free) are made explicit at every
emission site, and the module-global, never-replenished 512-call fuel
budget (identical to WASM's own semantics) is reproduced with a
`defonce` atom. Real execution (not just JVM `eval`) was verified via
`nbb`, including one real bug this uncovered before landing: KIR's own
function order does not guarantee a synthesized `loop`/`recur` helper is
defined before the `defn` that calls it, and plain `defn` forms (in cljs
*or* JVM Clojure) do not forward-hoist across a file the way WASM's
function-index table does -- fixed by emitting a `(declare ...)` of every
function name ahead of any `defn`. `cap-call` dispatches through an
exported `set-cap-dispatch!` (a fn [cap-id value] -> i64 the host installs
before calling `main`, this backend's equivalent of WASM's `kotoba:cap`
host import) -- no dispatcher installed means every cap-call is denied,
fail-closed. i64 wraparound is not exactly reproduced (would need every
value as a JS BigInt end to end, not attempted) -- but every `+`/`-`/`*`
result is checked against JS's own safe-integer bound (2^53-1) and throws
`:arithmetic-overflow` rather than silently continuing with an imprecise
value, narrowing the gap from "silently wrong" to "loudly fails," the
same fail-closed posture as fuel/division/capability. See
`backend/cljs.clj`'s own docstring for the full, honest scope.

The extracted native scalar-call path pins canonical parallel function-entry
assignment. Four live i64 parameters remain zero-frame and spill-free on
x86-64 and AArch64; the five-live-parameter case uses one bounded lazy entry
spill. Both paths are executed through real loader subprocesses in the
shared dual-ISA test table.

The restricted JavaScript target is selected with `--target js`. A Web
library may deliberately omit `main`, but only when its namespace declares a
non-empty host boundary, for example `(ns example.math (:export [add1]))`.
This produces an entryless ESM artifact whose frozen API contains only those
exports. Entryless source is rejected for every native, Wasm, and
ClojureScript target; executable programs still require an exported,
zero-argument `main`. Missing, empty, private, duplicate, or unknown exports
fail closed before lowering.

The Web target also carries the first non-i64 value profile without erasing
types. Typed parameters use alternating name/type pairs and an optional result
type follows the parameter vector:

```clojure
(ns example.text (:export [greet]))
(defn greet [name :string] :string
  (string-concat "こんにちは、" name))
```

This lowers to checked `kotoba.kir/v4`; `:string`, `:keyword`, `:map`, `:bool`,
`:option-i64`, `:result-i64`, and `:i64` remain distinct in
every function signature. The admitted string surface is deliberately small:
`string-concat`, `string=?`, and `string-byte-length`. Literals must be
well-formed UTF-16 and at most 4,096 UTF-8 bytes, all module literals together
are capped at 65,536 bytes, and runtime values are capped at 65,536 bytes.
Generated ESM revalidates types, Unicode shape, and byte limits at function and
host boundaries. The qualified Wasm algebraic subset uses the sealed
`kotoba.typed/externref-v1` ABI described below. Native and ClojureScript
targets, and typed operations not yet lowered by Wasm, fail closed; strings are
never replaced with hashes or silently treated as integer handles.

Keywords preserve canonical Unicode text with a 512-byte bound and never use
probabilistic integer hashing. The first owned map profile admits at most 128
unique keyword keys with signed-i64 values. `get`, `assoc`, and `{:k value}`
lower to typed KIR map operations; generated ESM uses canonical frozen entry
arrays and persistent updates. Mixed/nested map values remain fail-closed.
Booleans are strict values rather than integer truthiness. `nil` lowers only
to the none case of `:option-i64`; `(some value)`, `some?`, `nil?`, and
`option-value` operate on an explicit bounded option. Web host values use
frozen `[false]` or `[true, bigint]` tags. Host null/undefined, malformed tags,
integer sentinels, and non-i64 payloads fail closed.

The first algebraic-result profile is `:result-i64`. `(result-ok value)` and
`(result-err error)` each carry exactly one signed-i64 payload;
`result-ok?`, `result-value`, and `result-error` inspect it without host
truthiness or sentinels, and the two projections evaluate their fallback only
for the opposite variant. Its Web ABI is frozen `[true, bigint]` or
`[false, bigint]`. This closes a monomorphic tagged-union ABI foundation; it
does not yet admit generic or recursive ADTs.

Parametric results use `[:result ok-type err-type]`. Their constructors and
projections are the explicit `result-*-of` forms and always carry the same
descriptor, so neither the frontend nor generated JavaScript guesses types
from host shapes. Descriptors and nested runtime payloads are capped at depth
8 and 64 nodes and are revalidated at every function/export boundary.
`match-result` requires the canonical pair of `(ok binder body)` and
`(err binder body)` branches. Binder types come from the descriptor, branch
result types must agree, and only the selected branch is evaluated; omitted,
duplicated, reordered, or ill-typed branches fail during checking.

Closed user variants use
`[:variant :qualified/type [[:case payload-type] ...]]` with 1--32 unique
cases inside the same depth/node budgets. Runtime values carry the complete
descriptor, case keyword, and payload; a same-named case from a different
descriptor cannot cross a boundary. `match-variant` requires every case once,
in declaration order, and admits no wildcard that could hide schema growth.

Generic options use `[:option payload-type]`. Their canonical Web ABI is
`[descriptor, false]` for none and `[descriptor, true, payload]` for some, so
even a payload-free none retains exact type identity. `option-some-of`,
`option-none-of`, `option-some?-of`, `option-value-of`, and exhaustive
`match-option` carry the descriptor explicitly. Null, undefined, untyped
sentinels, cross-option substitution, malformed tags, and eager fallback
evaluation are rejected.

Fixed heterogeneous vectors use `[:vector [item-type ...]]` with at most 32
positions inside the shared descriptor budget. Their canonical Web ABI is
`[descriptor, item ...]`; exact descriptor identity, length, and every
position's type are revalidated at boundaries. `(hetero-vector descriptor
...)` constructs an exact value. `hetero-vector-at` and
`hetero-vector-assoc` require an admission-time in-range integer index, making
the projected/replacement type static. Updates return a new frozen value, and
`hetero-vector-equal` performs validated structural equality without exposing
JavaScript object identity. Dynamic indexes, sparse values, append/drop, and
host mutation are not admitted.

Typed sets use `[:set item-type]` and at most 32 values inside the shared
depth/node budget. Canonical values are `[descriptor, sorted-items]` with
recursive type validation, a language-owned total order across every admitted
value family, frozen Web arrays, and duplicate rejection. `(typed-set
descriptor ...)`, count, membership, idempotent insertion, removal, and
structural equality preserve this representation without observing host
insertion order or object identity.

A top-level `def` may use a non-empty set literal only when every item is a
keyword and the set has at most 32 items. The frontend lowers it immediately
to canonical `[:set :keyword]` data. Empty, mixed-type, floating, oversized,
or computed set constants remain rejected; use an explicit typed constructor
where the item type cannot be safely inferred.

Closed top-level constants may reference other declared constants, including
inside vectors and maps. Resolution is compile-time-only, must terminate in
bounded literal data, and rejects unknown names and cycles. A symbol never
falls through to host lookup or execution.

Canonical typed maps use `[:map key-type value-type]` and at most 31 entries
inside the shared 64-node value budget. Values are
`[descriptor, sorted-entry-vector]`; every entry is an exact two-item
key/value vector, sorted by the same language-owned total order used by typed
sets. Duplicate keys fail closed. `typed-map-new`, `typed-map-count`,
`typed-map-contains`, `typed-map-get`, `typed-map-assoc`,
`typed-map-entry-at`, `typed-map-dissoc`, and `typed-map-equal` preserve the descriptor and validate
both sides recursively. Lookup returns `[:option value-type]`, so absence
never uses null, undefined, zero, or a caller-provided sentinel. JavaScript
object identity, property coercion, insertion order and mutation are outside
the ABI. The older leaf `:map` profile remains a separate keyword-to-i64
compatibility type and is not interchangeable with `[:map K V]`.
`typed-map-entry-at` accepts a checked i64 index and returns
`[:option [:vector [key-type value-type]]]`; it provides deterministic,
fuel-bounded traversal without admitting callbacks or host iterators.

Nominal bounded records use
`[:record :qualified/type [[:field field-type] ...]]`, with 1–32 unique
keyword fields in declaration order under the shared descriptor budget. Their
canonical ABI is `[descriptor, field-value ...]`. `(record descriptor ...)`
must supply every field exactly once; `record-get` and `record-assoc` require a
declared keyword literal, so field types remain static and updates are
persistent. Exact nominal descriptor, arity, and recursive field validation
exclude cross-schema substitution, unknown/dynamic fields, sparse host objects,
prototype behavior, and host identity from record semantics.

The Clojure-shaped `defrecord` surface uses that same 32-field bound rather
than the unrelated five-parameter callable bound. `->Type` and exact-literal
`map->Type` stay ordinary source constructors; a positional constructor wider
than five lowers directly and intentionally is not a first-class function.
Schema-shaped declarations automatically expose `[:ref :namespace/Type]`, so
nested sets, maps, records, and signatures can reuse the nominal identity
without a duplicate namespace `:schemas` entry. `get`, keyword lookup, and
destructuring remain type-directed.

The machine-readable corpus at
`resources/kotoba/compiler/typed-value-conformance.edn` is the shared
qualification source for these algebraic value families. Every positive vector now executes against the reference
interpreter, restricted Web emitter, and Wasm externref runtime, with the same
compile-time or runtime fail-closed boundary for negative vectors. `.cljk` is
a Kotoba source extension selecting the compiler; it is not a separate runtime
ABI and must follow the ABI of the selected target.

The Wasm parity path reserves the versioned `kotoba.typed` custom section for
canonical binary descriptor and literal tables. Hosts parse it with strict
UTF-8, uniqueness, EOF, depth, node, member, and table limits before
instantiation. Binary typed ABI v4 retains scalar `f64` tag 12 and adds scalar
`f32` tag 13; an older host rejects it before instantiation.
`kotoba.typed/externref-v1` consumes that table through frozen, host-issued
canonical values, validates every reference parameter and result, and rejects
forged, descriptor-reused, or cross-schema values. The compiled result seals the required Wasm
reference-types feature only when reference values are present. Scalar-only
floating-only modules use the Wasm scalar ABI without unnecessary value-host
imports. f32 users seal `:kotoba.typed/mixed-f32-f64-v3`; f64-only users retain
`:kotoba.typed/mixed-f64-v2`. Unsupported KIR v4 operations still fail during
lowering; metadata presence alone is never treated as qualification.

The first bounded sequential collection is `:vector-i64`, constructed
explicitly with `(vector-i64 ...)` and capped at 16,384 items at runtime.
Source forms retain the independent 128-item admission bound; larger binary
inputs enter Web through checked arrays and typed Wasm through the host-issued
`typedValues.bytes`/`typedValues.vectorI64` factories. `vector-count`,
`vector-get`, `vector-at`, `vector-drop`, `vector-assoc`, and `vector-conj` preserve signed-i64 elements;
get uses a lazy fallback for every out-of-range index, while assoc traps.
Generated Web values are frozen arrays and updates are persistent. Ordinary
`[1 2 3]` literals now lower to this profile. `[a b & rest]` destructuring uses
trapping required positions and a bounded frozen suffix. Nested vector/map
patterns select accessors from inferred heterogeneous-vector, record,
typed-map, or homogeneous-vector types; missing positions fail closed instead
of silently becoming zero or nil. Typed-map bindings require an explicit `:or`
payload default. Destructured function parameters declare their structured type
explicitly.
The explicit `(list ...)` surface retains the legacy pair-chain representation.

Release-oriented target identities explicitly bind execution format, ISA, OS,
ABI, and runtime profile. Current explicit names are `wasm32-browser`, `wasm32-wasi`,
`x86_64-linux`, `x86_64-macos`, `x86_64-windows`, `aarch64-linux`,
`aarch64-macos`, `aarch64-windows`, `aarch64-android`, and `aarch64-ios`.
The short `wasm32`, `x86_64`, and `aarch64` names remain experimental
compatibility aliases with `:os :unspecified`; they cannot serve as platform
release evidence. `x86_64-windows` compilation now emits a reproducible KEXE
whose Windows OS, internal ABI, and supervisor identity are independently
verified. Native execution and release evidence still fail closed until the
measured Windows supervisor is trusted for the current host. Historical hosted
Windows x64 execution remains useful regression evidence, but those GitHub
Actions runners are no longer the CI authority and the current murakumo fleet
has no Windows node. The explicitly qualified Zig 0.15.2 and 0.16.0
toolchains now cross-build the reviewed loader twice byte-identically for
x86-64 and Arm64, and the gate independently checks PE32+ machine identity.
That is product portability evidence, not Windows runtime or physical-device
release evidence.

The Android and iOS names begin with distinct compile/verify identities.
They produce equal reviewed AArch64 instructions but distinct sealed artifact
digests and runtime contracts. Android isolated-process loading and iOS signed
static/AOT product embedding are still required before either target is executable or
counted as native mobile coverage.

Android now also has a first NDK host-library boundary. Pinned NDK
27.3.13750724 cross-builds the AArch64 shared library twice byte-identically;
CI requires AArch64 ELF identity, NX stack, RELRO, immediate binding, and one
exported execution function. That function maps verified code RW then RX,
flushes the instruction cache, installs the fixed fuel/capability/pair context,
and requires the Android target identity. It deliberately expects an Android
isolated process to contain guest traps. No emulator or physical-device
execution is claimed yet. The NBB conformance can require native execution on
an attached Arm64 Android device by setting `KOTOBA_ANDROID_EXECUTE=1`; it then
pushes a minimal harness and verified code through adb and checks the result,
fuel, and heap report. GitHub-hosted macOS Arm64 runners timed out booting API
35, 31, and minimal AOSP API 28 images, so this evidence is deliberately not a
required hosted-CI claim.

iOS now has a static AOT packaging command:

```bash
kotoba -M package-ios program.kexe --entry main \
  --platform ios --output program.o --manifest-output program.edn
```

It reverifies the explicit iOS KEXE, emits a canonical Mach-O `MH_OBJECT` with
AArch64 bytes in `__TEXT,__text`, and binds artifact, code, entry, platform, and
object digests in the manifest. `--platform ios-simulator` emits an explicitly
tagged Simulator object. Pinned Xcode 16.2 CI builds a no-JIT static host archive
twice byte-identically. Device code signing, app embedding, trap
isolation, and physical iPhone/iPad execution remain release gates.
A separate CI job additionally links that same static host archive into a
plain executable against the `iphonesimulator` SDK and runs it for real inside
the iOS Simulator (`npm run test-ios-simulator`, arm64-native on the Apple
Silicon CI runner, no Rosetta) -- unlike the device path above, this actually
executes the compiled code and checks the result, not just static Mach-O
shape. This needs no physical hardware or paid signing (Simulator binaries
run unsigned), but does not by itself count toward this repo's coverage
percentage -- see ADR-0001's Phase 3 for why.

`wasm32-wasi` is the first sealed server core-Wasm profile. It is not yet a
WebAssembly Component Model component. Its Wasm custom section
seals `wasm32-wasi-kotoba-v1`; the dependency-free host rejects missing or
substituted target identity and admits only `kotoba:cap` and `kotoba:heap`
functions. Ambient WASI filesystem, socket, clock, random, environment, and
process imports are rejected before instantiation.
CI also executes the sealed pure ABI and fuel traps on Wasmtime 42.0.1, fetched
by an NBB installer that verifies the pinned official release SHA-256. This is
independent engine evidence alongside Node/V8, not yet a Kubernetes release
claim.

The planned `wasm-component-kotoba-v1` target is generated directly by the
compiler: Kotoba schemas and typed capabilities become a closed WIT world and
canonical ABI component. WASI filesystem, HTTP, clocks, and similar interfaces
belong only to explicitly declared provider components, never to the
application as ambient authority. Wasmtime is a conformance engine for that
artifact; no Wasmtime-specific Rust runner is part of the language ABI.
Bounded `:vector-i64` and `:vector-f64` identity exports now cross that real
Component boundary as `list<s64>` and `list<f64>`; the compiler validates
pointer, length, alignment, arena range, and the 16,384-item limit, while
`drop`, `assoc`, and `conj` export results use bounded copy-on-write and
canonical post-return so they neither mutate nor alias a borrowed input.
Option/result matches may return those owned lists from a selected payload,
another vector parameter, or a bounded literal. Selected aggregate leaves
remain fully validated and inactive joined slots remain lazy. Repeated
internal construction still needs linear reuse for efficiency; the
export-boundary ownership rule does not claim to solve that optimization.
Structural scalar `[:option T]` and `[:result T E]` values now use the same
standard Canonical ABI union codec as sealed variants. Identity exports and
the explicit `option-*-of`/`result-*-of` constructors compile from Kotoba to
real `option<T>`/`result<T,E>` Component exports. Their tag predicates and
fallback projections also execute directly at the Component boundary; the
core boundary traps out-of-range discriminants and non-canonical active bool
payloads without interpreting an inactive case. Nested option/result payloads
apply the same rule recursively at every discriminant, including bounded
string and list leaves. CI checks
`none`/`some`/`ok`/`err` with the pinned Wasmtime engine.
The same union codec crosses an explicitly named capability import. In
addition to scalar leaves, the request/result may carry bounded
strings/keywords, `list<s64>`/`list<f64>`, and nested option/result payloads.
General bounded lists may recursively contain scalar, string/keyword,
option/result, finite-record, or list items under shared whole-value byte and
item-count budgets.
The compiler emits the exact WIT import, a separately packaged provider
exports the matching structural type, and closed-world composition rejects
missing or extra providers. Both sides derive their bounded Canonical arena
from the recursive payload layout; unsupported or nominal aggregate shapes
fail closed rather than falling back to an ambient WASI or generic host
import.
Exhaustive `match-option` and `match-result` over `i64`, `f32`, `f64`, and
`bool` payloads also compile to Components. Their branch bodies use the shared
typed binary Wasm expression emitter, including its fuel global, so
arithmetic, comparisons, `if`, and `let` do not have a parallel
Component-only implementation. The host-free adapter specializes only the
Canonical i32 discriminant/native payload boundary; selected bool values are
checked as 0/1 without interpreting an inactive payload. Heterogeneous
`result<T,E>` payloads use the Component Model joined-flat coercion table:
their bits are wrapped/reinterpreted into the selected case type only after
the discriminant is validated. Multiple such match exports and private scalar
helpers are emitted into one Component core module, sharing the same sealed
fuel global while retaining per-function bool validation scopes. WIT export
and parameter names are collision-checked after canonical normalization.
Within an `option<list<T>>` or symmetric `result<list<T>,list<T>>` match, the
selected list can be reconstructed, sent through an explicitly named
capability with the same request/result descriptor, and immediately matched
again for `s64`, `float64`, `string`, and `keyword` items. This path stays in
that shared module and uses the standard WIT import's caller-allocated result
storage; `bool`, finite numeric/bool record items, and nested lists recursively
ending in `s64`/`float64` are supported under the same path. Maximum request
and result lists can coexist in the bounded arena. Every inline bool field,
indirect item, and nested pointer/count graph is visited on both sides of the
provider call even when source code observes only the outer count, enforcing
canonical 0/1 bytes, pointer/range checks, the shared 1 MiB byte budget, and
one 16,384-item budget across all nested nodes. Other aggregate
match/capability combinations remain fail-closed until admitted by an explicit
Canonical codec.
General bounded `[:list T]` types are shared KIR/Wasm metadata ABI values.
Component identity and named capabilities admit scalar, string/keyword,
structural option/result, finite-record, and recursively nested list items.
Every active bool, discriminant, pointer/length, per-leaf bound, and arena
range is checked. All UTF-8 leaves share a 1 MiB budget and all nested list
nodes share a 16,384-item budget; depth-specific loops prevent inner
traversals from corrupting outer cursors. Canonical lift borrows the complete
item graph through return, and post-return releases it afterward.
Symmetric `result<list<T>, list<T>>` values also cross this shared path. Both
the outgoing `ok`/`err` case and the provider's returned case stay explicit;
the returned discriminant and active list are validated before either branch
observes its count.
Bounded string payloads use the same option/result path and expose only their
validated UTF-8 byte length. Payload and enclosing result-area alignment are
independent Canonical properties, preventing the string's byte alignment from
weakening union result-pointer checks.
Sealed finite scalar records can be reconstructed from an option match,
passed through the named capability, and projected from the returned record.
The shared flat codec validates the returned option and every active bool
field before exposing the selected scalar field.
Finite record payloads with recursively scalar `i64`, `f32`, `f64`, and
`bool` leaves use that same match path. Record binders may only escape through
a statically resolved `record-get` chain; selected bool leaves are validated
even when branch code does not read them, while inactive joined slots remain
uninterpreted. Closed namespace schemas may reference a distinct nominal
record root; inline field-aware descriptors must exactly match the declared
schema before `[:ref ...]` and the descriptor are type-compatible. A
source-level `.kotoba` test packages and runs a nested record boundary, not
only a hand-built KIR fixture.
Aggregate match modules may invoke scalar named capabilities from either
branch. The compiler emits the match adapter, private helpers, fuel global,
and standard32 capability import in one core module; closed-world composition
then requires an exact provider before execution. Canonical adapters reject a
typed capability with no named binding instead of falling back to a generic
ambient host import.
String and keyword leaves inside selected record payloads may also feed
`string-byte-length`. They stay as Canonical `(ptr,len)` values: the shared
core emitter validates their declared byte limit, pointer overflow, and actual
memory range without constructing a host string. Selected but unread indirect
leaves are still validated; malformed inactive slots are ignored.
Selected `:vector-i64` and `:vector-f64` record leaves likewise feed only
their matching count and trapping element-read operations. Their Canonical list
pointer/count pair is checked for element alignment, the item ceiling,
unsigned byte-size/range overflow, and the module's actual memory size.
`vector-at`/`vector-f64-at` additionally validate the unsigned index before
loading one scalar element. Raw list escape and other operations remain
fail-closed.
`vector-get`/`vector-f64-get` perform the same list validation, but return
their explicit fallback for a negative or out-of-range index without forming
a memory address.
Top-level drop/assoc/conj operations now return owned i64/f64 list results:
the Component validates the borrowed input, allocates and copies a new buffer,
applies the bounded update, emits the standard pointer/count result area, and
releases transient storage through post-return. Input buffers are never
mutated or exposed as result aliases.
The Core-Wasm compatibility ABI also lowers the monomorphic
`:option-i64`/`:result-i64` operations through the same sealed descriptor
encoding as `[:option :i64]`/`[:result :i64 :i64]`; admitted scalar ADTs no
longer fail late in the Wasm emitter.
The pinned official specification baseline and synchronous/async version split
are documented in `docs/component-model-baseline.md`.
The full test matrix includes a native `ubuntu-24.04-arm` runner: AArch64 KEXE
execution under the W^X loader, sanitizer vectors, architecture-specific
libFuzzer coverage floors, the WASI host, and Wasmtime all run without CPU
emulation.

The WASI profile also ships a bounded HTTP service adapter and a digest-pinned
multi-architecture Node container. Each request receives a fresh Wasm instance
and private fuel/heap; input is limited to 4 KiB, five canonical decimal i64
arguments, and eight concurrent executions. Kind CI deploys two replicas as
non-root with a read-only root filesystem, RuntimeDefault seccomp, all Linux
capabilities dropped, no service-account token, and explicit CPU/memory limits.
Health and execution identities are checked before and after forced pod
replacement.
Guest execution runs in a per-request Worker with a one-second deadline. A
separately constructed sealed infinite-loop module must be terminated while the
service process remains healthy, providing an explicit cancellation and
engine-hang containment vector.
`/metrics` exposes only bounded low-cardinality counters for requests, success,
rejection, guest deadlines, active workers, and the sealed module identity;
arguments and guest results are never labels or logs.

Release artifacts can now carry deterministic SPDX 2.3 and signed provenance:

```bash
kotoba -M sbom service.wasm --output service.spdx
kotoba -M attest-release service.wasm --sbom service.spdx \
  --target wasm32-wasi --key release-key.edn \
  --not-before 1000 --expires 2000 --output service.release.edn
kotoba -M verify-release service.release.edn --artifact service.wasm \
  --sbom service.spdx --trust trust.edn --now 1500
```

Verification regenerates the canonical SBOM, checks both raw file digests and
sizes, reconstructs the exact target profile, and applies Ed25519 trust,
revocation, and validity windows. Artifact, SBOM, target, or statement mutation
fails closed.

The first Windows supervisor slice historically executed verifier-extracted
x86-64 KEXE code on a hosted Windows runner. It maps code RW, copies it,
transitions it to RX, flushes the instruction cache, then prohibits further
dynamic code. A Clang `sysv_abi` adapter supplies the hidden `r9` context. A
one-process Job Object, low-integrity restricted impersonation token,
system32-only DLL search, and error-mode hardening surround guest entry. That
run covered runtime arguments, transitive calls, fuel reports, capability
allow/deny, bounded pairs, filesystem/process/network denial, measured runtime
trust, signed execution, receipt verification, mutated loader bytes, and a
substituted OS profile. The Windows-host conformance program now additionally
covers option/result host round trips, signed limits, guest construction and
projection, and invalid handles. None of this is claimed as continuously gated
runtime evidence until a Windows murakumo node runs it. Authenticode/MSIX,
Windows Arm64 execution, and renewed x64 execution remain required.

WebAssembly is one backend, not the compiler architecture. Native backends emit
machine instructions directly and never invoke an assembler, LLVM, a JVM JIT,
or a Wasm runtime. Native output is deliberately a sealed `KEXE` object rather
than an OS executable: an aiueos loader must verify it, map code W^X, and expose
only policy-derived capability trampolines.

The aiueos freestanding profiles additionally produce boot artifacts. The
kernel profile packages its sealed x86-64 code as an import-free ELF64 image
and writes a linkable ELF64 object exporting `kotoba_aiueos_probe`:

```sh
bin/kotoba-compiler compile examples/aiueos-probe.kotoba \
  --target x86_64-aiueos-kernel-v1 --fuel 4096 --output kotoba_aiueos_probe.o
```

The object is emitted directly by the Kotoba compiler—no generated C or host
runtime—and is intended to be linked and boot-tested by the aiueos repository.
For single-source core/native compilation, `--fuel` is build metadata and is
sealed into the artifact; executable kernel packaging copies that same finite
value into the hidden machine context. The CLI and the generated image are
both tested, so a printed request cannot disagree with the executing budget.
The UEFI profile packages a deterministic PE32+ EFI application with `.text`,
`.data`, and `.reloc` sections and no import directory. Its entry shim satisfies
the Microsoft x64 stack/shadow-space boundary only for the language's required
zero-argument `main`, initializes the hidden Kotoba context, and returns the
integer result as `EFI_STATUS`; internal functions retain the compiler's
Kotoba SysV/context-r9 ABI. Firmware service bindings are not implied by this
packaging contract.

The native verifier treats embedded KIR as hostile even when an attacker has
recomputed every unkeyed hash. It independently validates the KIR AST, lexical
scope, call arities, transitive capability effects, ABI limits, node/depth
budgets, and `let` expansion cost before regenerating and comparing machine
code.
KEXE, signed envelopes/statements, trust policies, capability policies,
runtime identities, signing/verification keys, receipts, and receipt fuel maps
all use exact versioned schemas: unknown fields are rejected rather than
ignored. For pure KEXE, the verifier also re-executes `main` with the normative
KIR interpreter and requires sealed `:value` metadata to match; effectful KEXE
must carry no oracle value.

The current experimental slice supports pure integer functions, parameters,
direct calls, sequential `let`, `if`, arithmetic, comparisons, and immutable
`pair` / `pair-first` / `pair-second` values, with `list`, `cons`, `first`,
`second`, `rest`, and `empty?` as bounded frontend syntax. Safe numeric/truth
predicates include `not`, `zero?`, `pos?`, and `neg?`. It emits
executable Wasm with real runtime parameters, locals, calls, and branches, plus
verified runtime functions for x86-64 and AArch64. KEXE seals its
target, KIR identity, effects, resource limits, and exact code bytes with
SHA-256. Pair allocation is the sole admitted heap operation; general objects,
mutation, indirect control flow, and OS ABI emission fail closed until their
verifier rules exist.

Pair storage is a fixed 4,096-cell (64 KiB) arena per execution. Handles are
one-based integers validated on every access; zero, negative, future, and
out-of-range handles trap before an address is formed. Allocation is monotonic,
immutable, and traps at capacity—there is no fallback to host allocation and no
GC pause or unbounded growth. The normative KIR executor enforces the same
capacity. Native code reaches only fixed context-v2 callbacks at sealed
offsets; the loader owns the arena. The typed callback admits bounded strings
and monomorphic `:option-i64`/`:result-i64`. Options and results use canonical
pair-backed `(tag,payload)` handles; the loader validates the handle and tag on
both sides and additionally requires a none option's payload to be zero. Wasm
uses equivalent `kotoba:heap` imports, whose host implementation must enforce
the same contract.

The empty list is the i64 value zero. Non-empty lists are immutable pair chains;
projection from zero or any forged handle traps. `list` is capped at 128 items
and is expanded before structural and lowering budgets are checked, so surface
syntax cannot hide unbounded backend work.

Compilation has explicit structural budgets in addition to the 1 MiB source
limit. Function count, common five-argument ABI, bindings, expression nodes, and
the estimated `let`-elided lowering size are checked before backend emission;
compact substitution chains cannot amplify into unbounded native code.

```bash
bin/amu compile example.kotoba --target wasm32 --output app.wasm
bin/amu compile example.kotoba --target wasm32-wasi --output service.wasm
bin/amu compile example.kotoba --target x86_64 --output app.kexe
bin/amu compile example.kotoba --target x86_64-windows --output app-windows.kexe
bin/amu verify app.kexe
npm ci
npm run conformance
```

The checked-in `.npmrc` permits no dependency lifecycle scripts. This keeps
`npm ci` fail-closed and makes npm 11 bootstrap behavior independent of a
developer's user-level `allow-scripts` list.

The canonical `bin/amu` front runs on plain Node and starts the selected NBB
compiler runtime once. The compatibility `bin/kotoba` driver and conformance
orchestrator run on NBB rather than POSIX shell. Clojure remains a private
compiler implementation detail.
On x86-64 Linux and AArch64 macOS/Linux, `npm run conformance` additionally compiles the small
auditable loader in `tools/kexe_loader.c`, maps verified code RW, transitions it
to RX with `mprotect`, and executes a runtime arithmetic/comparison vector. No
RWX mapping is created. Zero division and signed-division overflow must trap on
all three backends; loader resource limits keep native traps outside the compiler.
Linux additionally applies `no_new_privs` and a seccomp-BPF syscall allowlist
before guest entry. macOS applies a deny-by-default Seatbelt profile in the
child. CI independently requires filesystem, network, and process-creation
probes to be denied on both OS families.

Wasm modules contain a private, non-replenishable i64 fuel global initialized to
512 by default (or the finite `--fuel` value). Every function entry checks and
decrements it before evaluating guest code.
This permits bounded recursion while guaranteeing that recursive cycles trap.
x86-64 reserves r9 and AArch64 reserves x7 for a loader-owned fuel-context
pointer; both charge every function entry before guest instructions. Their real
call paths support bounded direct and mutual recursion through verified
`CALL rel32` / `BL imm26` relocations.

KIR v3 includes a normative fuel-bounded reference executor. Signed i64
add/subtract/multiply wrap modulo 2^64; invalid division traps. CI compares
boundary vectors with Wasm and the native ISA available on each runner, so
compile-time validation cannot silently use different arithmetic semantics.

`runtime/browser-host.mjs` is the dependency-free browser execution boundary
for `wasm32-browser-kotoba-v1`. It copies and byte-caps the input, measures its
SHA-256 with Web Crypto, optionally requires an expected digest, and admits only
the four exact `kotoba:cap` / `kotoba:heap` function imports. It rejects exposed
memory, tables, and globals, rechecks capabilities at every call, and owns the
private 4,096-cell pair arena. Host errors and Wasm traps are reduced to stable,
non-diagnostic codes. The module intentionally receives no DOM, network,
storage, clock, randomness, or dynamic-linking authority.

```js
import { instantiateKotoba } from "./runtime/browser-host.mjs";

const hosted = await instantiateKotoba(wasmBytes, {
  expectedSha256: artifactDigest,
  allowCapabilities: [7],
  capCall: (id, value) => value
});
const result = hosted.instance.exports.main();
```

`runtime/worker-host.mjs` adds a closed one-shot module-worker protocol. Each
request binds a bounded ID, exact operation, Wasm bytes, expected digest,
runtime capability allowlist, and at most five i64 arguments. The worker
serializes execution, rejects unknown fields and concurrent requests, and
returns only the result, digest, heap report, or normalized error class.
Capability handlers are trusted install-time functions in the static worker
entry; guest messages cannot introduce executable callbacks or ambient APIs.
The deployment profile in `runtime/CSP.md` uses same-origin static workers and
the narrow CSP `'wasm-unsafe-eval'` token, never JavaScript `'unsafe-eval'`.

`npm run test-browsers` compiles fresh `wasm32-browser` artifacts and runs the
same direct-host, Worker, capability allow/deny, bounded-heap, forged-handle,
and CSP-denial vectors in pinned Playwright Chromium, Firefox, and WebKit.
Pixel 7 and iPhone 15 profiles add viewport/input/user-agent emulation. These
are engine and emulation conformance signals only: they are not evidence for a
branded Chrome/Edge release, physical Android/iOS hardware, or Safari itself.
The isolated browser CI additionally installs current Google Chrome Stable and
Microsoft Edge Stable on Linux and Windows. Its versioned machine-readable receipt records
the exact Playwright project, engine, browser version, evidence class, commit,
CI run, and host OS, and is retained as a workflow artifact. It is conformance evidence,
not yet a trusted signed platform-release statement.
On `macos-14`, a separate NBB-controlled SafariDriver job launches the installed
Safari rather than Playwright WebKit. It navigates the same production-CSP
fixture, waits for the direct/Worker/capability/heap result, separately verifies
the CSP denial page, and records the Safari version as
`safari-stable-macos` evidence.
Evidence schema v2 also binds the observed `cspWasmEnforced` property. Current
Safari reports `false`; all other gated engines and branded browsers report
`true`. Therefore CSP denial is never substituted for Kotoba artifact and
capability admission.

The test gate generates a deterministic 100-program property corpus across
arithmetic, comparisons, `if`, lexical `let`, and direct calls. Every program is
compiled to all three targets; the gate requires identical KIR, deterministic
native bytes/seals, successful re-verification, and rejection after a one-byte
mutation.

`kotoba -M check` performs capability admission before backend selection.
`cap-call` accepts only a literal ID in `[0,255]`; effects propagate through the
full function-call graph, including cycles and lexical bindings. Admission is
deny-by-default and conservatively covers every declared function, including
private functions; it returns a least-privilege policy and reports unused
grants. Wasm lowers admitted calls to the sole
`kotoba:cap/call(i64,i64)->i64` import; the host rechecks policy on every call.
Native targets carry a sealed context-v1 layout. Generated code checks its
256-bit allow bitmap before calling the single fixed callback slot; the callback
checks the same bitmap again. x86-64 keeps the context in r9 and AArch64 in x7.

KEXE authenticity uses a separate Ed25519 envelope. The signed statement binds
the artifact SHA-256, signer fingerprint/public key, not-before, and expiry.
All external EDN inputs—including KEXE, envelopes, trust stores, policies,
execution inputs, and receipts—pass through one strict bounded decoder before
verification. It accepts exactly one valid UTF-8 form and caps bytes, nesting,
token length, decoded nodes, and strings. Source files are byte-capped while
streaming before the frontend allocates the complete input.
All CLI outputs are written to a same-directory temporary file, forced to disk,
then atomically renamed. Destination symlinks are replaced
rather than followed, and generated Ed25519 private-key files are explicitly
owner-readable/writable only (`0600`).
Verification requires an explicit trusted-signer set, checks signer/artifact
revocation and time validity, then runs the normal KEXE verifier.

```bash
kotoba -M keygen --output key.edn
kotoba -M public-key key.edn --output verification-key.edn
kotoba -M trust-key verification-key.edn --output trust.edn
kotoba -M sign app.kexe --key key.edn --expires 2000000000 --output app.signed.kexe
kotoba -M verify-signed app.signed.kexe --trust trust.edn
```

`keygen` proves that the encoded Ed25519 private and public keys form one pair
before any signing operation. `public-key` emits a separate
`:kotoba.verification-key/v1` without private material; `trust-key` validates
its algorithm, encoding, fingerprint, and exact shape before provisioning
trust. Direct provisioning from a validated signing key remains supported for
bootstrap compatibility but is discouraged outside local setup.

Verified executions can produce `kotoba.run-receipt/v1`. Its hash binds the
signed envelope and artifact, signer, target/entry, required effects, exact
policy admission, input/output hashes, fuel accounting, status, time interval,
and optional parent receipt. Verification repeats current signature, trust,
revocation, policy, and artifact checks before accepting the evidence. The
receipt hash is itself signed by a trusted executor key; a hash chain alone is
not treated as proof that execution occurred.

`kotoba -M verify-chain chain.edn --trust trust.edn` requires every node to have
a currently trusted, non-revoked executor signature and returns the explicit
scope `:executor-attested-chain/v1`. It verifies provenance and linkage; full
execution evidence still uses `verify-receipt` with the envelope, policy, input,
and result. Creating a child receipt likewise refuses an unattested parent.

```bash
kotoba -M check examples/capability.kotoba \
  --policy examples/capability-policy.edn
kotoba -M compile examples/capability.kotoba --target wasm32 \
  --policy examples/capability-policy.edn --output capability.wasm
```

`cap-call`'s capability id may also be written as a namespaced keyword name
(ADR-2607182410) instead of a magic integer, e.g. `(cap-call :identity/sign
value)`. The name is resolved against the language-owned semantic catalog,
`kotoba/lang/capability-catalog.edn`, supplied by `kotoba-sema` on the
classpath. The compiler derives its closed name-to-wire-id table from that
vendored authority at parse time -- before anything else in the compiler runs, so
`--policy` still grants/denies by the resolved integer id exactly as before.
An unregistered name is a hard parse-time error. `examples/capability-named.
kotoba` / `examples/capability-named.edn` are the named-form counterpart of
the pair above, and additionally show the optional `ns` `(:capabilities
#{...})` declaration, which the compiler checks is an exact match (declared
== used) for every named `cap-call` in that namespace:

```bash
kotoba -M check examples/capability-named.kotoba \
  --policy examples/capability-named.edn
kotoba -M compile examples/capability-named.kotoba --target wasm32 \
  --policy examples/capability-named.edn --output capability-named.wasm
```

After putting `bin/amu` on `PATH`, the canonical command is `amu ...`.
`kotoba -M ...` remains accepted as a compatibility API. JVM-only operations
remain private implementation paths and can be replaced without changing the
Amu command contract.

Failures emit exactly one EDN value on stderr and no host stack trace:

```clojure
{:format :kotoba.cli-error/v1
 :ok false
 :error :decode
 :message "EDN input contains trailing forms"
 :details {:phase :decode}}
```

Exit codes are stable by boundary: `64` usage, `65` rejected input/compiler or
verifier data, `69` execution setup, `74` output I/O, `76` receipt, `77`
signature/trust/runtime identity, `70` redacted internal failure, and `120` for
a measured guest trap.

`kotoba -M run` is the admitted native execution path. It verifies the signed
KEXE envelope and current trust/revocation state, checks local capability
policy, requires host ISA and entry arity to match, then invokes the supervised
loader. The command writes the measured result separately and creates an
executor-signed receipt using the supervisor's actual post-execution fuel
counter; callers cannot supply result, status, timing, or fuel values.
The result evidence also binds the pinned loader-source hash, the exact loader
binary hash, the resolved C compiler executable's byte hash, and its version
output hash. Runtime v3 additionally binds the compiler-reported assembler and
linker executable byte hashes. Runtime v4 also binds a deterministic manifest
of the compiler's builtin include/resource directory. Runtime v5 binds the exact
source and system/SDK header closure emitted by the compiler dependency scan.
A source mismatch is denied
before compilation, and the executor signature makes the runtime identity part
of the receipt's output evidence.

For high-assurance verification, provision the measured runtime from a reviewed
build into the trust policy before any guest execution. The measured loader is
published owner-only and executable; `run` hashes that exact file and never
invokes a C compiler:

```bash
kotoba -M measure-runtime --output runtime.edn --loader-output kotoba-loader
kotoba -M trust-runtime runtime.edn --trust trust.edn --output pinned-trust.edn
kotoba -M run app.signed.kexe --trust pinned-trust.edn \
  --runtime runtime.edn --loader kotoba-loader ...
kotoba -M verify-receipt run.receipt.edn --trust pinned-trust.edn ...
```

The pin covers the reviewed loader source, reproduced loader binary, compiler
binary/version output, assembler, linker, and builtin compiler resources. `cc` is resolved once to an absolute real
path; both builds use that path, and its bytes are re-hashed after the second
build to detect persistent replacement during measurement. The assembler and
linker paths reported by the compiler must resolve to regular executable files;
their bytes are likewise measured before and after both builds. Native execution
always requires an explicit
`:trusted-runtime-sha256` membership; an absent or empty set denies every
runtime. Runtime revocation uses `:revoked-runtime-sha256`. Measurement is a
deliberate provisioning operation and still executes the local toolchain, so it
belongs in a controlled build environment rather than on an exposed executor.
No subprocess inherits the bootstrap environment. Toolchain processes receive
only a canonical `PATH` containing the resolved compiler directory plus system
binary directories, `C` locale, UTC, and fixed reproducibility variables.
Variables such as `CPATH`, `LIBRARY_PATH`, `SDKROOT`, `LD_PRELOAD`, and
`DYLD_*` cannot influence measurement. The admitted loader receives only its
explicit structured-report flag.
The selected sealed export also owns the typed host framing. Scalar records
with 1–128 unique `:i64`/`:bool` fields cross as keyword maps, but remain the
aggregate ABI v2 declaration-order pair chain inside native code. The loader
accepts exactly the declared host keys, validates an exact-length chain and
its zero terminator on return, then copies field words before unmapping the
arena. Raw pair handles never escape the process.
Monomorphic `:option-i64` and `:result-i64` exports use the same tagged vectors
as the reference and restricted-ESM hosts. The loader materializes their
canonical `pair(tag,payload)` handles before entry and validates/copies the
selected result before teardown. Tags are exact 0/1 words; option none is
uniquely `(0,0)`.
Native runtime identity v6 additionally includes the exact explicit target
profile measured on the host. Execution requires artifact ISA/ABI/OS/runtime
compatibility, runtime-to-host exact profile equality, and explicit trust in
the resulting runtime digest. A loader identity measured for another OS is
rejected even if that digest was provisioned into the trust store.
The resource manifest sorts relative paths and binds each path, size, and file
hash plus aggregate bytes. It rejects symlinks and special files, more than
10,000 files, paths over 4,096 characters, and trees over 64 MiB before hashing
contents, preventing the measurement step itself from becoming an unbounded
filesystem traversal. Total directory entries are separately capped at 20,000.
The dependency scan uses the same compiler, isolated environment, warning
policy, and optimization mode as the real build. Its Make-style depfile parser
handles escaped characters and line continuations, caps serialized input at
1 MiB, then binds every canonical real path, size, and content hash. The closure
is limited to 10,000 files and 64 MiB and is recomputed after both builds.
Every spawned process has a Java-side wall deadline and separately bounded
stdout/stderr capture. A hanging or output-flooding compiler or loader is killed
together with its descendants. Toolchain builds allow 30 seconds and 1 MiB per
stream; admitted execution allows 5 seconds and 64 KiB per stream in addition
to the loader's internal three-second supervisor deadline.

Security mutation fuzzing runs in every CI job with a recorded seed. It mutates
sealed native artifacts (including attacker-resealed KIR/code/ABI fields),
Ed25519 envelopes, and executor receipts, requiring every case to fail closed.
A failure can be replayed locally:

```bash
KOTOBA_FUZZ_SEED=5426643073673934426 KOTOBA_FUZZ_CASES=1000 clojure -M:test
```

The C loader is also compiled with AddressSanitizer and UndefinedBehaviorSanitizer
in every Linux and macOS CI job. The sanitizer gate executes verified native
code and a malformed CLI corpus covering empty, overflowing, invalid ISA,
capability, arity, and i64 inputs.

The same production parser implementation is compiled into a fuzz harness.
Linux CI performs 20,000 libFuzzer coverage-guided runs from a committed seed
corpus with ASan/UBSan enabled. macOS CI runs 20,000 deterministic sanitized
mutations of the identical harness because the current Xcode image does not
ship its libFuzzer runtime.

A separate `long-fuzz` workflow runs the Linux coverage-guided harness for five
minutes every Monday and can be started manually with a custom duration. It
uploads the evolved corpus plus any `crash-*`, `timeout-*`, or `leak-*` inputs
for 30 days even when fuzzing fails, so findings remain reproducible rather than
being lost with the runner.

Downloaded corpus artifacts are reviewed in dry-run mode before promotion:

```bash
npx nbb scripts/review-fuzz-corpus.cljs path/to/artifact/corpus --dry-run
npx nbb scripts/review-fuzz-corpus.cljs path/to/artifact/corpus --apply
```

Promotion accepts only non-symlink regular files no larger than 1024 bytes,
enforces aggregate limits, rejects untrusted filenames, deduplicates by content
SHA-256, and reruns the sanitized fuzz harness before copying new inputs under
canonical SHA-256 names.

All repository build, conformance, sanitizer, fuzz, and corpus-review
orchestration is implemented in NBB/ClojureScript. No POSIX shell script is a
project execution boundary.
CI uses an exact Node 24 runtime and Clojure CLI version. Every third-party
GitHub Action is pinned to a full commit SHA; an NBB workflow lint gate rejects
mutable tags, unpinned toolchains, and reintroduced `.sh` execution files.
GitHub also requires action SHA pins at the repository boundary. The exact
Actions permissions and app-bound, strict `main` checks are versioned in
[`docs/adr/0249-version-github-merge-governance.edn`](docs/adr/0249-version-github-merge-governance.edn).
An administrator can audit the live settings without exposing administration
access to CI:

```bash
npx nbb scripts/check-github-governance.cljs
```

The EDN is desired state; only a successful GitHub API readback establishes
current enforcement. See
[`ADR 0249`](docs/adr/0249-version-github-merge-governance.md) for the recovery
rule and blocked-canary evidence.

Linux libFuzzer emits `:kotoba.fuzz-coverage/v1` summaries containing edge
coverage, feature count, and corpus count. CI compares them with the reviewed
architecture-specific baseline in `fuzz/baselines/native-parser.edn`. Baseline
v2 is bound to the raw
loader-source SHA-256, so a C change cannot silently reuse stale coverage
expectations. Linux runs use the fixed libFuzzer seed `424242`; current minimums
are x64 cov 60/features 100/corpus 20 and Arm64 cov 60/features 100/corpus 18.
The separate corpus floors account for deterministic architecture-dependent
instrumentation and minimization without weakening either coverage threshold.

The managed compiler boundary also runs 600 deterministic frontend mutations:
300 edits of a valid structured program and 300 raw grammar inputs. Any accepted
source must produce identical KIR across Wasm, x86-64, and AArch64,
byte-reproducible Wasm, and verifier-admitted native artifacts. Rejections must
use a controlled compiler phase rather than leaking host reader exceptions.

See [docs/architecture.md](docs/architecture.md) and
[docs/threat-model.md](docs/threat-model.md).
