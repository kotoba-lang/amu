# ADR 0237: Copy scalar native records across the process boundary

## Status

Accepted.

## Context

Aggregate ABI v2 already defines a scalar record as
`pair(field-0, pair(field-1, ... 0))` in declaration order. Native code could
construct, pass, and project that representation, but the execution host still
rejected records. Returning the arena handle after loader exit would have been
the same false boundary previously closed for strings.

## Decision

Keep the published guest representation. Admit only expanded, named records
with 1–128 unique keyword fields whose values are `:i64` or `:bool`. Tender
requires a host map with exactly those keys, lowers values in declaration
order, and sends one `r:` token. The measured loader parses bounded signed
decimal words and allocates the pair chain before guest entry.

For a selected scalar-record result, derive the descriptor from the sealed KIR
function. Before unmapping the arena, the loader walks exactly the declared
number of pairs, requires terminator zero, and copies the words into the typed
structured report. Tender independently checks the report, field count, i64
range, and bool 0/1 values before reconstructing the host keyword map. An
invalid result chain traps with exit 127.

Nested records and other aggregate fields remain rejected. A `[:ref ...]`
without its expanded field descriptor is not guessed at this boundary.

## Evidence

The entryless integration library exercises host-map ordering, `Long/MIN_VALUE`,
both bool values, guest projection of a host-created chain, and copying a
guest-created record through the signed real process. Missing keys, extra keys,
and integer impersonation of bool are rejected. A direct loader negative test
requires raw result handle zero to become exit 127 with
`:invalid-record-chain`.

The POSIX source compiles under `clang -std=c11 -Wall -Wextra -Werror`. The
Windows source mirrors the protocol and changes runtime identity, but remains
unqualified until exercised on a Windows fleet node.

With the published artifact and tender pins, Amu passes 954 tests and 7,515
assertions. The native executor namespace contributes 52 tests and 157
assertions. Reversing only the loader's reported field order produces two
native executor errors, proving that the integration suite observes the
descriptor order rather than merely accepting a record-shaped report.

## Consequences

`:i64`, `:bool`, `:string`, and bounded scalar `:record` now have native host
boundaries. Nested aggregates, vectors, options/results, and documents remain
explicitly rejected. This advances native maturity without changing Amu's
public execution API or making native the default target.
