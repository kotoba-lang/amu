# ADR 0256: Authenticate admitted output-set publishers

Status: accepted

## Context

ADR 0254 provides a crash-consistent output-set marker, and ADR 0255 proves
that its exact artifact and sealed provenance pass target-specific admission.
The result intentionally reported `:publisher-authenticated false`. An attacker
able to replace all three files could still construct another internally valid
set, so consumers had no cryptographic statement connecting an admitted set to
a trusted publisher.

KEXE and release artifacts already use Ed25519 and `:kotoba.trust/v1`, but a
KEXE signature covers only KEXE and a release attestation covers an artifact
plus SBOM. Neither explicitly endorses the provenance and publication marker
used by the primary Node compiler front, and neither covers Wasm output sets.

## Decision

`amu sign-output-set <artifact>` first runs the complete ADR 0254/0255
admission, then emits a detached `:kotoba.output-attestation/v1`. Its closed
statement binds:

- the output-set marker SHA-256, which already commits both basenames, sizes,
  and exact file bytes;
- the sealed provenance SHA-256;
- the primary artifact SHA-256 and declared target;
- the Ed25519 signer/public key and an inclusive not-before, exclusive expiry
  interval.

The signing key must match the existing closed `:kotoba.signing-key/v1`
contract. Signatures use the same canonical bytes and signer fingerprint as
`kotoba.verifier.signing`, so JVM-generated keys and JVM verification remain
byte-compatible.

`amu verify-output-set` remains an unsigned integrity-admission command by
default. Authenticated verification requires `--attestation`, `--trust`, and
`--now` together. It runs output admission first and then checks the closed
attestation schema, signature, trusted signer, signer and output revocations,
time interval, and exact identities of the admitted set. Only that path returns
`:publisher-authenticated true`, together with the signer and validity window.
Partial authentication options fail as usage errors instead of downgrading.

The same `:revoked-artifacts` set may revoke the primary artifact, provenance,
or whole output-set identity. Signer revocation remains independent.

## Evidence and boundary

The publisher-authentication regression generates Ed25519 keys through the JVM
CLI, signs and verifies a Wasm output set through the primary Node front, and
then verifies the Node signature through the JVM canonical verifier. It rejects
expiry, an untrusted signer, output-set-name replay, a modified signed
statement, output-set revocation, a mismatched keypair, and partial verification
options. The existing policy-bound regression continues to prove unsigned and
native admission behavior.

This authenticates a key authorized by the supplied trust policy; it does not
prove a legal or human identity, repository control, source review, reproducible
builds, target equivalence, timestamp-authority participation, or secure key
custody. `--now` is explicit evidence-evaluation input, not a trusted timestamp.
