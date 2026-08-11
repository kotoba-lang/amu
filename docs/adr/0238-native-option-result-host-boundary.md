# ADR 0238: Copy monomorphic option/result across the native process boundary

## Status

Accepted.

## Context

Native code already constructs and consumes `:option-i64` and `:result-i64`
as one-word handles to `(tag,payload)` pairs. Typed capability calls validate
that representation, but exported functions still had no structured host
codec. The KIR producer and hostile-artifact verifier therefore rejected these
otherwise representable types at public function boundaries.

Scalar variant was considered first and rejected as the next increment:
aggregate ABI v2 still marks its boundary held, and native ADR 0015 explicitly
does not define variant parameters or results. Option/result already have the
representation authority that variant lacks.

## Decision

Use the existing public tagged-vector values unchanged:

- option none is `[false]`; some is `[true signed-i64]`;
- result ok is `[true signed-i64]`; err is `[false signed-i64]`.

Tender accepts only those exact vector shapes and lowers them to bounded
loader tokens. The loader allocates one `(tag,payload)` pair before guest
entry. For a selected tagged result it validates the handle, the 0/1 tag, the
signed payload, and option none's unique zero payload, then copies typed fields
into the supervisor report before teardown. Invalid option/result handles trap
with exits 128/129. Raw pair handles never cross the process boundary.

The KIR producer and verifier independently admit the two monomorphic aliases
at exported boundaries. Parametric/nested option/result descriptors remain
closed; this decision does not infer a recursive host ownership protocol.

## Evidence

The signed entryless integration library exercises none/some, ok/err,
`Long/MIN_VALUE`, `Long/MAX_VALUE`, guest construction, guest projection, and
host round trips. Non-vector values, integer tags, missing payloads, extra
slots, and noncanonical option none are rejected. Direct loader tests require
handle zero to trap separately for option and result.

The POSIX loader compiles with both Clang and fortified GCC under
`-Wall -Wextra -Werror`. Reversing only the reported tag produces six failures
and two errors in the native executor suite, proving that the semantic tag is
observed rather than merely accepting a tagged-shaped report.

The Windows loader now also cross-compiles twice byte-identically with Zig
0.15.2 for both x86-64 and Arm64. The gate parses the products independently as
PE32+ and checks their machine fields. The Windows-host conformance program has
the same option/result round trips, signed limits, guest construction and
projection, and invalid-handle exits ready to run. This proves source and
product portability, but not AppContainer/WFP execution: the current murakumo
fleet has no Windows node, so Windows runtime execution remains explicitly
pending.

The final pinned closure passes 956 Amu tests and 7,537 assertions. The native
executor contributes 54 tests and 178 assertions.

## Consequences

Native host boundaries now cover `:i64`, `:bool`, `:string`, bounded scalar
records, `:option-i64`, and `:result-i64`. Scalar variants, parametric ADTs,
vectors, and documents remain explicit gaps. Windows x86-64 and Arm64 loaders
are reproducible cross-build products; neither is counted as runtime-qualified
until the conformance program executes on a Windows fleet node.
