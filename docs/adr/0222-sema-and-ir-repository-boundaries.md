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
kotoba-sema       source/forms -> checked HIR             (extracted)
kotoba-hir        checked HIR envelope contract           (extracted)
kotoba-kir        canonical semantic IR and DefCID
kotoba-gmir       target-independent machine IR contract (extracted)
kotoba-mir        target machine IR contract              (extracted)
kotoba-codegen    MIR/MC final layout contract            (extracted)
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

- `kotoba-sema` owns the admitted reader, schema validation, type/effect
  checking, capability elaboration, and the grammar/capability catalogs;
- compatibility namespaces remain under `kotoba.compiler.*`, but the compiler
  consumes them from the pinned sema dependency and carries no duplicate source;
- `kotoba-hir` owns the closed v2/v3 checked-module envelope, function
  annotations, entry/export/effect invariants, and portable form boundary;
- the compiler frontend validates every produced HIR and `kotoba-kir` validates
  the same value again before HIR-to-KIR lowering;
- `kotoba-gmir` owns GMIR v1 validation and has no repository dependencies;
- `kotoba-mir` depends only on `kotoba-gmir` and owns target selection,
  explicit virtual/physical allocation state, and deterministic allocation;
- `kotoba-codegen` owns canonical label/relative-branch tokens and deterministic
  final layout, including range, alignment, and encoder-width validation;
- `kotoba-native` depends on the three IR/codegen contracts and retains
  KIR-to-GMIR lowering, instruction selection/encoding, ABI integration, and
  target-specific ELF layout/emission;
- `kotoba-object` owns validated, target-neutral ELF64 headers, segments,
  sections, symbols, RELA records, endian encoding, and bounded padding;
- `kotoba-native` consumes `kotoba-object` while retaining image addresses,
  relocation selection, entry shims, fuel, capability, and aiueos policy.

The dependency graph is therefore acyclic:

```text
compiler -> kotoba-sema -> kotoba-kir -> kotoba-hir
compiler -> kotoba-hir
kotoba-native -> kotoba-mir -> kotoba-gmir
kotoba-native -> kotoba-kir
kotoba-native -> kotoba-codegen
kotoba-native -> kotoba-object
```

`kotoba.codegen.layout` is the production MC/layout seam used by the x86-64,
AArch64, and explicit machine-IR paths. Repository
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
- `kotoba-sema` is now a real source-to-HIR producer boundary. Its legacy
  namespaces preserve compatibility while `kotoba.sema` provides the canonical
  public entry; the compiler pins and consumes the repository without a cycle.
- `kotoba-hir` is now a real producer/consumer boundary shared by the compiler
  frontend and `kotoba-kir`; expression type checking remains a sema proof and
  was not duplicated in the envelope validator.
- `kotoba-codegen` is now a real dependency of all native production emitters;
  target opcode encoding and ABI policy did not move with final layout.
- `kotoba-object` is now a real dependency of `kotoba-native`, and therefore of
  the compiler closure; target policy did not move with the record encoders.
