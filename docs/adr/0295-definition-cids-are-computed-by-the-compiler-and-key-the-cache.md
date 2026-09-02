# ADR-0295: definition CIDs are computed by the compiler, and they key the cache

- Status: accepted
- Date: 2026-09-02
- Consumes: kotoba-kir `1e00f830` (`kotoba.kir.definition-identity`:
  `definition-cid`, `identity-payload`, `normalize`, `effect-row-from-hir`),
  kotoba-lang `lang/code-identity.edn` (the contract), kotoba-lang
  `lang/code-identity-vectors.edn` (the frozen payload-v2 vectors).
- Relates: ADR-0294 (`:abort` is a row member nobody can grant), superproject
  ADR-2608550000 (the build cache key is the definition graph's properties).

## Context

`lang/code-identity.edn` has said since it was written that a definition's
identity is its canonical typed KIR plus five other sealed inputs, and
kotoba-kir has implemented that identity for as long. Nothing computed one.
Measured on this repository at `ca869d79`, `definition-cid` appeared in exactly
one place — as an unpopulated field name in
`src/kotoba/compiler/logic_manifest.cljc`. No compiled function had an
identity, so:

- a package lock could pin `:dep/definition-cids`, and no build could produce
  the CIDs to satisfy it;
- the compile cache keyed on **source text**, so renaming a private helper and
  its call sites recompiled a module that emits byte-identical bytes;
- the two questions "is this the same build?" (`:hir-sha256`, `:kir-sha256` —
  one hash of one whole-module value) and "which of these definitions are the
  same code?" had one answer, and it was the wrong one for the second question.

## Decision

The compiler computes a definition CID for every top-level function, on both
routes, and the definition-CID closure keys Wasm emission.

`kotoba.kir.definition-identity` remains the authority: it owns the canonical
DAG-CBOR encoding, the sealed payload and every refusal. The new namespace
`kotoba.compiler.definition-identity` owns the compiler half — turning KIR into
the six sealed inputs, identically under Clojure and ClojureScript.

## Four measurements this rests on

**1. `kir`'s `normalize` does not alpha-normalize.** It is a canonical encoder
over an EDN value domain; a symbol becomes `["sym" <name>]` verbatim. Measured
directly:

```clojure
(definition-cid (payload '(+ a 1)))  ; bafyreigucwk5cmuh7b7xwcviysfzuiemmevwqvj6jl3i3wuwvnzdmdmmki
(definition-cid (payload '(+ b 1)))  ; bafyreiazdjhcwy3jj3sigeol5ydpaopblxx3bksbrknxzaoauwxasie6ka
```

Two bodies differing only in a binder name have different identities. The
contract says `:alpha-normalization :de-bruijn`, so the renaming is the
compiler's job and it happens before anything reaches the identity. Binders are
numbered `k0`, `k1`, … by a single left-to-right counter that never resets, so
the renaming is a function of position alone. The five KIR binding forms are
`params`, `let`, `result-match-of`, `variant-match` and `option-match`; a sixth
added later would leave a source-chosen name in the body, and
`verify-normalized!` refuses rather than hashing it.
`kir-normalize-alone-leaks-binder-names` pins the measurement, so the day kir
grows de Bruijn normalization the duplication here can be removed on evidence.

**2. Emitted Wasm bytes are invariant under a private rename and are NOT
invariant under a reorder.** Three compiles of the same three-function program,
`--target wasm32`:

| module | `.wasm` sha256 |
|---|---|
| `h1` / `h2` / `main`, exports `[main]` | `d325e408…49170a` |
| the same, `h1` and `h2` renamed `zz1` / `zz2` | `d325e408…49170a` |
| the same, `h1` and `h2` **swapped in declaration order** | `34ae6c50…a40452` |

(With `(:export [h1 h2 main])` the rename changes the bytes — 331 vs 334, the
three characters of the longer name — because an exported name is in the
artifact.) So a cache key built from definition identity must carry the
**ordered** CIDs and the export names, and must not carry private names. It
does: `cache-material` returns exactly those two things.

**3. `scc-v1` is a real rule and it is implementable here.**
`kotoba.codebase.typed-code` already implements it: partition into strongly
connected components, and inside a component choose the member ordering whose
canonical bytes are smallest, trying every permutation up to
`max-recursive-group` (8). That is a canonical choice made from bytes, not from
names, so renaming every member of a cycle leaves the group identity alone —
asserted by `a-mutually-recursive-group-is-hashed-as-a-unit-and-is-rename-invariant`,
with `a-cycle-is-never-hashed-by-name` as the control that swapping which member
holds the base case *does* move both CIDs. A component larger than the bound is
**refused** with `:definition-cid :recursive-group-too-large`; a cheaper
ordering rule would be a different identity wearing the same shape.

**4. `:abort` has no keyword the bridge can seal.** `effect-row-from-hir` admits
`[:cap/call <id>]` and nothing else, and ADR-0294's tracked control effect is a
bare keyword naming no authority. Such a function gets
`:definition-cid :unbridged-effect`, its callers get
`:definition-cid :dependency-unavailable`, and the module yields no cache
material at all. A CID is never invented for a hole.

## What the interface seals

`:definition/interface` is `{:arity n :params [<types>] :result <type> :schemas
{...}}` — arity, the KIR function's `:param-types` when it has them, the result
type, and the **transitive schema definitions those types and the body reach**
via `[:ref <name>]`.

The schemas are there because a schema definition is part of what a function
*means*, not metadata about it: widening a record changes the meaning of every
function that takes one while leaving each body textually identical. Without
sealing them, such a change would move no CID and a cache keyed on those CIDs
would serve the old artifact for the new program.
`a-schema-definition-is-part-of-the-interface` and
`parameter-types-are-part-of-the-interface` pin both halves. They are built
from synthetic KIR rather than from source, because the frontend refuses a
record whose constructor does not exactly match its descriptor — so no *pair of
compilable programs* differs in the schema alone, and a source-level test of
this claim cannot be written.

## Where the two version constants come from

`:definition/profile-version` is **6**, read from the grammar authority
`resources/kotoba/lang/guest-grammar.edn`
`:kotoba.lang.guest-grammar/profile-version`. It is repeated as a constant
because that authority is a JVM classpath resource and the nbb route has no
classpath reader — the same split `kotoba.compiler.frontend` makes for the
capability catalog. `profile-version-matches-the-grammar-authority` reads the
resource and asserts equality, so the constant is a copy rather than a guess.

`:definition/desugar-contract-version` is **1**, and this is a **measured gap**.
Nothing in this repository, in kotoba-sema or in kotoba-lang declares a desugar
contract version: `lang/guest-grammar.edn` versions the grammar and the
profile, `lang/elaboration-pipeline.edn` names the stages, neither numbers the
desugar contract. The only place the number appears is
`lang/code-identity-vectors.edn`, whose frozen vectors carry 1 (and one carries
2 purely to prove that changing it moves the CID). So the value is 1 because the
vectors use 1, not because an authority says so.
`desugar-contract-version-is-pinned-because-no-authority-declares-one` pins that
choice with the gap in its name. **Every definition CID this compiler mints
depends on a number nobody owns.** That is the state of the world, recorded
rather than papered over.

## The cache

The existing cache in `kotoba.compiler.nbb.compile-cache` has two halves: an
**artifact** cache keyed on `[target, source text, policy, emit metadata,
linked?, artifact kind]`, and a **stage** cache with `:hir` and `:kir` entries.
This change adds a third stage, `:wasm`, to the same mechanism. It is not a
second cache.

The artifact entry keeps its source-text key on purpose. It also carries the
`.provenance.edn` sidecar, and provenance seals `:source-sha256`; serving a
rename the previous provenance would be a wrong answer, not a fast one.
Emission has no such obligation — it is a function of the code and the target —
so the `:wasm` stage is keyed on

```
[:kotoba.wasm-emit-cache/v1
 {:definitions [<cid> …ordered]      ; declaration order, from measurement 2
  :exports     ["main" …]            ; export names, from measurement 2
  :profile-version :desugar-contract-version :payload-version}
 target  fuel  value-abi  wasm-features  kir-format
 compiler-contract-version  policy-text  module-lock-cid]
```

A nil material — any definition without a CID — skips the stage entirely rather
than keying on a partial identity.

The metric is **definitions recompiled**, reported as `:definitions-recompiled`
in the compile answer. Never wall clock: this workstation runs many agents at
once, so a duration measures the machine's mood while a count measures the
cache. `:unmeasured` when there was no material, so "the cache was not asked"
and "the cache missed" do not print the same thing.

`scripts/test-definition-cid-cache.cljs`, driving a real worker over its NDJSON
protocol:

| scenario | artifact cache | `:wasm` stage | definitions recompiled | `.wasm` |
|---|---|---|---|---|
| (a) first compile | miss | miss | 3 | — |
| (a) recompile unchanged | **hit** | — | **0** | byte-identical |
| (b) rename two private functions and their call sites | miss | **hit** | **0** | byte-identical |
| (c) change one body | miss | miss | 3 | different |
| (d) bump the sealed profile version (mutated checkout) | miss | miss | 3 | **unchanged** |

(d) is asserted on the **key**, not on a hit/miss verdict: a fresh worker misses
because its cache is empty, which is exactly the check that passes without
discriminating. The test compares the reported `:emit-cache-key` — same for (b),
different for (c) and (d) — which is why the compiler reports it at all.

That (d) leaves the emitted bytes unchanged is the other half: the profile
version is sealed into *identity*, not into the emitter. If that row ever goes
red the key is under-specified rather than over-specified — the safe direction,
but still a lie about what the number means.

## Provenance gains `:definitions`

`kotoba.compiler.provenance/descriptor` now carries the definition graph, so it
is emitted once for every backend on both routes rather than at each call site.
**This changes `.provenance.edn` bytes for every artifact**, deliberately. The
`.wasm` bytes are unchanged, and
`scripts/test-policy-bound-provenance.cljs` — which asserts the JVM and nbb
sidecars are byte-identical — now covers the new key too.

A result whose backend carries no typed KIR gets a named reason
(`{:entries :unavailable :reason :no-typed-kir}`) rather than an empty map. An
empty definition set would say "this artifact has no definitions", which is the
shape of failure where a measurement that could not be taken returns what a
clean measurement returns.

## The npm dependency

`kotoba.kir.definition-identity` requires `multiformats.core`, whose
ClojureScript branch hashes with `@noble/hashes`. `kotoba.compiler.nbb.module-lock`
deliberately avoided that package by assembling a CIDv1 from `node:crypto` and
`multiformats.base32`. That shortcut is right for a four-constant raw CID; it is
wrong here, because avoiding the package would mean re-deriving `normalize` and
`identity-payload` in Amu — a second implementation of exactly the thing
ADR-2608550000 names as the defect it was fixing. `@noble/hashes` (2.0.1, pure
JS, no install scripts, no transitive dependencies) is therefore a dependency.
The nbb route already requires `node_modules/nbb/cli.js`, so this is one more
package in an install that has to happen, not a new class of requirement. The
JVM/nbb parity script is what makes the two hashers' agreement measured rather
than assumed.

## Consequences

- `amu definition-cids <file>` prints the report on both routes: `:lines`
  (`name<TAB>CID`, refusals listed with their marker rather than omitted),
  `:scanned` (`SCANNED<TAB><identified>/<total>`, an evidence floor), `:order`,
  `:entries`. `check --json` carries the same `:definitions` map.
- `definition-cids` runs **no admission**, on either route. A CID is identity,
  never authority. The first version of the JVM command went through
  `check-source` and refused a module naming a capability without `--policy`
  while the nbb twin answered — two answers to one question, caught by the
  parity script.
- A new exit code, **66**, on both routes: no identity could be computed at all.
  A *refused* definition is an answer (listed with its marker, exit 0); without
  a distinct code the two are indistinguishable to a caller.
- An f32 module is refused whole with `:f32-literal-unsupported`. An f32 literal
  is a host `Float` on the JVM and an ordinary JavaScript number under nbb, and
  the identity's admitted domain has one float form (f64 bits); widening would
  give an f32 definition and its f64 twin **one** identity, which is a collision
  rather than a normalization. The refusal is decided by the same module-level
  question (`ir/uses-f32?`) on both routes, rather than by a per-literal test
  only one route can ask.

## What kotoba-lang should record (not edited here)

`lang/code-identity.edn` `:stages` / `:implementation` should gain

```clojure
:ci8 :compiler-emits-definition-cids
```

with

```clojure
:ci8 {:status :implemented
      :evidence ["kotoba-lang/amu src/kotoba/compiler/definition_identity.cljc"
                 "kotoba-lang/amu test/kotoba/compiler/definition_identity_test.clj"
                 "kotoba-lang/amu scripts/test-definition-cid-parity.cljs"
                 "kotoba-lang/amu scripts/test-definition-cid-cache.cljs"
                 "kotoba-lang/amu docs/adr/0295-definition-cids-are-computed-by-the-compiler-and-key-the-cache.md"]
      :note "The compiler mints a payload-v2 DefCID per top-level function on
             both the JVM and the JDK-free nbb route, byte-identical across the
             two (five fixtures: plain, let-binders, mutual recursion, a literal
             past 2^53-1, a capability call). Alpha-normalization is the
             COMPILER's: kotoba.kir.definition-identity/normalize is a canonical
             encoder, not a binder-aware normalization, so two bodies differing
             only in a local name hash differently until Amu renames binders to
             de Bruijn positions. Recursive groups follow scc-v1 -- SCC
             partition, member ordering chosen by smallest canonical bytes,
             groups above 8 members refused with a marker rather than ordered by
             name. The definition-CID closure keys Wasm emission
             (:kotoba.wasm-emit-cache/v1); a private rename with its call sites
             is a cache hit with 0 definitions recompiled and byte-identical
             output."
      :gap "No authority declares :desugar-contract-version. Amu pins 1 because
            lang/code-identity-vectors.edn uses 1, with a test named after the
            gap. Until kotoba-lang numbers the desugar contract, every DefCID
            the compiler mints seals a number nobody owns."
      :residual-risk
      ["Alpha-normalization is implemented twice -- kotoba.codebase.typed-code
        and kotoba.compiler.definition-identity carry the same five-binder walk
        against the same KIR. Neither is the authority; kir is, and kir does not
        do it. The convergence named under :identity-implementations :direction
        should move the walk into kotoba-kir rather than into a third place."
       "An f32 module has no DefCID on either route: the admitted value domain
        has one float form, so an f32 literal and its f64 twin would collide.
        Refused rather than widened."]}
```

`:identities :definition-cid` should also record that `:typed-kir` as the
compiler seals it is an `{:op :kotoba.definition/function :params :body}` node
whose callee references are `[:kotoba.definition/ref <cid>]` and whose
in-cycle references are `[:kotoba.definition/group <index>]` — i.e. that the
sealed body contains no function name at all, on either side of a call — and
that `:interface` carries the transitive schema definitions the signature and
body reach, not only the arity and result type.
