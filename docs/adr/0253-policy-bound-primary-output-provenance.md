# ADR 0253: Bind primary output and provenance to policy

Status: accepted

## Context

`bin/amu` is the primary compiler front, but its JDK-free Wasm path stopped
after admission, lowering, and byte emission. It deliberately omitted the
provenance sidecar emitted by the JVM compiler. More seriously, it admitted
the parsed policy but called the Wasm emitter without the policy's
`:budgets :fuel` value. A build could therefore be policy-admitted while its
generated module retained the default fuel ceiling.

The persistent worker cache preserved Wasm bytes only. Consequently a cache
hit could not reproduce or integrity-check the supply-chain evidence that the
primary compiler is expected to publish.

## Decision

Compiler policy is partitioned before admission exactly as on the JVM path:
`:budgets` and `:language-profile` are compiler controls, not capability
grants. The language profile is passed into semantic analysis and forms part
of the HIR cache key, preventing a default-profile HIR from satisfying a
restricted-profile request.

The primary Wasm path constructs the same checked result identity as
`kotoba.compiler.core/compile-source`: target profile, HIR, KIR, admission,
compatibility descriptor, value ABI, feature set, resource limits, and emitted
bytes. The effective fuel value is taken from `[:budgets :fuel]`, defaulting to
512, and is passed to the emitter as well as recorded in the result.

Every primary Wasm compile emits `<output>.provenance.edn` using the shared
`:kotoba.provenance/v1` descriptor. The process-local artifact cache stores
both Wasm and provenance, includes both in byte accounting, verifies both
SHA-256 digests on every hit, and evicts a corrupt pair fail-stop.

The Node and JVM paths are required to produce byte-identical Wasm and sealed
provenance for the same source, target, and policy. CI also requires a changed
fuel policy to change both the module bytes and provenance.

The ordinary native path applies the same policy partition and language-profile
cache identity. Its declared fuel is sealed into `:fuel-abi` and `:limits`
instead of the historical fixed default. Bounded EDN represents that integer
as BigInt on Node; after checking the verifier's closed 1..1,048,576 range, the
compiler converts it to an exactly representable JavaScript integer for the
native ABI and KIR oracle. The original policy remains unchanged for provenance.

## Evidence boundary

`test-policy-bound-provenance` compares the primary Node compiler with the JVM
compiler using an explicit fuel budget, validates the resulting module, and
requires byte-identical Wasm, ordinary-native artifacts, and provenance. It
also requires a pure-product profile to reject a capability-bearing source and
the native path to reject fuel above the verifier's closed bound.
The compiler-worker and performance harnesses require cache hits to preserve
the new Wasm provenance bytes.

This proves policy-bound identity for the single-file Wasm and ordinary-native
slices. ADR 0254 later adds a crash-consistent committed-set marker around the
artifact and sidecar; it does not make their filesystem names simultaneously
visible, sign the provenance, or extend the Node front to Component/JVM-only
packaging commands.
