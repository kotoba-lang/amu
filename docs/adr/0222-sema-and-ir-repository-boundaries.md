# ADR 0222: Name source semantic analysis `sema` and extract IR repositories only at stable contracts

**Status:** accepted
**Date:** 2026-08-09

## Context

`frontend` is conventional compiler terminology, but most developers read it
as Web or application frontend. Kotoba also needs names for the boundaries from
source through checked HIR, canonical KIR, generic and target machine IR, MC,
and object packaging. Creating a repository for every arrow before those
contracts are exercised would turn ordinary schema changes into cross-repo pin
churn.

## Decision

Use **sema** for the source semantic-analysis ownership boundary:

```text
source/forms
  -> parse and resolve
  -> type and effect check
  -> capability elaboration
  -> checked HIR
```

After contracts and consumers stabilize, the eventual readable topology is:

```text
kotoba-lang       language specification
kotoba-sema       source/forms -> checked HIR
kotoba-hir        HIR contract
kotoba-kir        canonical semantic IR and DefCID
kotoba-gmir       target-independent machine IR contract
kotoba-mir        target machine IR contract
kotoba-codegen    MIR -> MC/machine bytes
kotoba-wasm       Wasm backend
kotoba-object     ELF / Mach-O / PE
compiler          orchestration and compatibility facade
```

Do not create `kotoba-frontend`. Do not split `kotoba-reader` unless source
bytes/forms gain an independent consumer and release cadence. Do not use a
generic `kotoba-lowering` repository: an extracted transform must name its
boundary (`hir-to-kir`, `kir-to-gmir`, or `gmir-to-mir`) or stay with the owner
of its output contract.

Extraction requires all of:

1. a closed, versioned data contract;
2. fail-closed validation and deterministic golden vectors;
3. more than one producer or consumer, or a demonstrated independent release
   need;
4. no dependency cycle after extraction.

Until then, exercise the boundary in its current repository. In particular,
`kotoba.native.machine-ir` is the in-repo GMIR/MIR/MC pilot and
`kotoba.native.layout` is the production MC/layout seam. Repository creation is
not evidence that the architecture exists; executable contracts are.

## Identity and representation

HIR/KIR/GMIR/MIR are abstract data contracts. EDN is the human/reference form,
JSON is an interop projection, and deterministic DAG-CBOR is the content
identity encoding. `pr-str` and JSON serialization are never IR identity.
SourceCID, DefCID, BuildCID, and ArtifactCID remain distinct identities.
The existing `kotoba-lang` language contract remains the sole DefCID authority
until an explicit, golden-preserving extraction moves it to `kotoba-kir`.

## Consequences

- `sema` is unambiguous to compiler developers without colliding with Web UI.
- Existing internal `kotoba.compiler.frontend` namespaces may remain while
  callers migrate; this ADR governs ownership and future repository naming.
- Repo count follows stable dependency boundaries rather than an aspirational
  diagram.
