# ADR 0239: Copy closed scalar variants across the native process boundary

## Status

Accepted.

## Context

Amu could already lower non-escaping scalar variant construction and dispatch,
but ADR 0238 correctly withheld parameters and results: aggregate ABI v2 did
not own a variant representation. Aggregate ABI v3 now does. The KIR producer,
native emitter, hostile-artifact verifier, tender, artifact identity, and both
loader sources have independent responsibilities in that closure.

## Decision

The public value remains canonical KIR data:
`[type case-keyword payload]`. An admitted descriptor has a qualified name,
one through 32 uniquely named cases in declaration order, and only `:i64` or
`:bool` payloads.

Tender encodes each argument as
`v:<case-count>:<zero-based-ordinal>:<i|b>:<word>`. The loader allocates the
ordinal and payload as a context-owned pair. The selected result profile is
`variant:<case-count>:<bool-mask>`; before teardown the loader validates the
handle, ordinal range, and 0/1 boolean payload, then emits a typed supervisor
report. Tender uses the sealed descriptor to recover the case keyword. Invalid
result handles trap with exit 130. No raw handle or case-name spelling is
accepted as public identity.

## Evidence

The signed real-process integration covers the minimum signed i64, both boolean
values, host echo, guest construction, and guest dispatch. Missing cases,
integer impersonation of booleans, malformed descriptors, and invalid result
handles fail closed. KIR admission separately rejects unqualified, empty,
duplicate, nested, non-scalar, and 33-case descriptors; changing its bound to
33 makes the width negative fail.

Both loader sources compile warning-free. Windows x86-64 and Arm64 products are
cross-built and parsed as PE32+; this is product portability evidence, not a
claim of Windows runtime execution, because the fleet still has no Windows
node.

## Consequences

Native host boundaries now cover scalar variants without replacing Kotoba's
canonical value model. Case order is sealed ABI data. Nested/recursive variants,
non-scalar payloads, more than 32 cases, and Windows runtime qualification
remain explicit gaps.
