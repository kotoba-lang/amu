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

The readable topology and current extraction state are:

```text
kotoba-lang       language specification
kotoba-sema       source/forms -> checked HIR            (deferred)
kotoba-hir        HIR contract                            (deferred)
kotoba-kir        canonical semantic IR and DefCID
kotoba-gmir       target-independent machine IR contract (extracted)
kotoba-mir        target machine IR contract              (extracted)
kotoba-codegen    MIR -> MC/machine bytes                 (deferred)
kotoba-wasm       Wasm backend
kotoba-object     object-container record contracts       (extracted: ELF64)
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

The first extraction wave completed after the in-repository pilot became an
executable contract:

- `kotoba-gmir` owns GMIR v1 validation and has no repository dependencies;
- `kotoba-mir` depends only on `kotoba-gmir` and owns target selection,
  explicit virtual/physical allocation state, and deterministic allocation;
- `kotoba-native` depends on both and retains KIR-to-GMIR lowering, MC/layout,
  byte encoding, ABI integration, and target-specific ELF layout/emission;
- `kotoba-object` owns validated, target-neutral ELF64 headers, segments,
  sections, symbols, RELA records, endian encoding, and bounded padding;
- `kotoba-native` consumes `kotoba-object` while retaining image addresses,
  relocation selection, entry shims, fuel, capability, and aiueos policy.

The dependency graph is therefore acyclic:

```text
kotoba-native -> kotoba-mir -> kotoba-gmir
kotoba-native -> kotoba-kir
kotoba-native -> kotoba-object
```

`kotoba.native.layout` remains the production MC/layout seam. Repository
creation alone is not evidence that the architecture exists; each extracted
repo has a closed validator, failure tests, CI, ownership rules, and a real
production consumer.

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
- `kotoba-sema`, `kotoba-hir`, and `kotoba-codegen` remain deferred until their
  code can move without creating a compatibility-only empty repository.
- `kotoba-object` is now a real dependency of `kotoba-native`, and therefore of
  the compiler closure; target policy did not move with the record encoders.
