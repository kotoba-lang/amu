# ADR 0235: Copy native strings across the process boundary

## Status

Accepted.

## Context

Native strings already had a checked guest representation: a pair containing
an offset and byte length, addressing either immutable artifact bytes or the
bounded runtime string pool. The execution host nevertheless rejected string
parameters and results because returning the pair handle after process exit
would leave a plausible-looking integer whose arena no longer existed.

## Decision

Keep the existing guest representation. Encode host string parameters as
lowercase UTF-8 hex, validate and decode them into the 65,536-byte loader pool,
and mint ordinary pair handles before sandboxed guest entry. Reject individual
or cumulative input larger than that pool.

For a selected `:string` export, derive the result type from the sealed KIR
function and tell the measured loader to inspect the returned handle. After
the child exits but before the shared arena is unmapped, the supervisor checks
the handle, allocated slice bounds, and canonical UTF-8, then emits bytes as
hex in the structured report. Tender independently validates and decodes that
field. Invalid result handles become an explicit result trap, not an integer.

Use `-(offset + 1)` when decoding negative pool offsets on both loaders so
`INT64_MIN` cannot trigger signed-overflow undefined behavior.

Pin artifact `b50572b51ca95c51c22856ba69a77b7fe6f99790` and
tender-native `a4ffda44db677a0d854468f1080a2095be91eef1`. The reviewed
POSIX/Windows loader source identities are respectively `f536c91e...` and
`e7149090...`.

## Evidence

The entryless integration library exercises five public-boundary cases through
the signed real native process: NUL-bearing UTF-8 input, dynamic concatenation
output, artifact-literal output, empty-string identity, and integer-handle
impersonation rejection. A direct measured-loader negative test requires raw
result handle zero to become exit 126 with `:invalid-string-handle`.

The POSIX source compiles under `clang -std=c11 -Wall -Wextra -Werror`. The
Windows source mirrors the protocol and changes runtime identity, but is not
qualified until executed on a Windows fleet node.

With the published artifact and tender pins, Amu passes 950 tests and 7,491
assertions. The native executor namespace contributes 50 tests and 148
assertions. Moving dynamic-pool result reads one byte forward makes two
integration assertions fail, proving that the suite observes copied content
rather than merely accepting a string-shaped report.

## Consequences

`:i64`, `:bool`, and `:string` now have production-shaped native host
boundaries. Aggregate, vector, option/result, record, and document host values
remain explicitly rejected. Native remains a supported low-level route, not
the default ordinary-application target.
