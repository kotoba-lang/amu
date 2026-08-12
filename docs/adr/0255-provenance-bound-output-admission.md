# ADR 0255: Verify provenance-bound output admission

Status: accepted

## Context

ADR 0254 introduced a crash-consistent commit marker for the primary artifact
and its provenance sidecar. `amu verify-output-set` proved that the visible
bytes were the set committed by one completed publication. The marker is
unkeyed, however: any writer able to replace the payloads can recompute it.
The command did not decode the provenance, validate its seal, bind its primary
identity to the artifact, or verify that the artifact was executable in its
declared format.

A consumer could therefore mistake "committed" for "integrity admitted", or
worse, for publisher trust. Those are three different assurances and need a
machine-readable boundary.

## Decision

`amu verify-output-set <artifact>` retains the marker check as its first gate,
then performs a second, fail-closed integrity-admission gate:

1. Decode the provenance through the bounded EDN reader and require the exact
   closed `:kotoba.provenance/v1` schema, builder, output shape, SHA-256 fields,
   and valid self-seal.
2. For Wasm, require a declared Wasm target, exact byte size and SHA-256, and
   `WebAssembly.validate` success.
3. For ordinary native output, bounded-decode the KEXE, require its target and
   sealed identity to match provenance, and run the independent native
   verifier, including KIR/code regeneration.
4. Return `:kotoba.output-admission/v1` with distinct fields for committed,
   provenance-sealed, artifact-identity-verified, target verification, and
   publisher-authenticated. The last is always `false` on this command.

The two gates stay separate internally. Low-level output-set verification
continues to mean commit consistency only; the CLI composes it with provenance
and artifact admission.

## Evidence and boundary

The policy-bound provenance regression admits real primary Wasm and AArch64
KEXE outputs. It also rewrites provenance, recomputes both the member digest
and unkeyed marker seal, and requires the new semantic gate to reject the set.
Existing artifact mutation and malformed-marker cases continue to fail at the
earlier commit gate.

This decision authenticates no person, organization, key, build service, or
distribution channel. Consumers requiring publisher trust must use the signed
KEXE/release trust commands and current revocation policy. It also does not
claim Wasm semantic equivalence to source; the Wasm gate proves format validity
and exact provenance identity.
