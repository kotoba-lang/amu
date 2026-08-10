# ADR 0223: Native string-index is private Kotoba state

## Status

Accepted

## Decision

The compiler admits bounded string-index values on x86-64 and AArch64 only
inside a module and across non-exported Kotoba functions. A kexe entry or
library export may not accept or return the context-owned handle.

The compiler pins the merged KIR admission, shared native lowering, and
independent verifier commits as one dependency closure. The native context
stays at ABI v3.

## Rationale

CID traversal needs a dynamic local key index, but that does not justify a host
graph database or a new runtime language. The native lowering represents the
index over the existing bounded vector arena and implements lookup/update in
emitted Kotoba machine code. It therefore uses no Rust, Durable Object, D1,
PostgreSQL, or host-owned graph callback.

Global scale belongs to content-addressed IPLD page DAGs. The per-execution
index remains bounded to 128 entries and 65536 UTF-8 key bytes.

## Evidence

The shared ISA execution table runs the same construction, lookup, missing-key,
contains, update, private parameter, and private result program as real
x86-64 and AArch64 processes. Both loaders are mandatory; a missing ISA fails
the test rather than being reported as a skip.

## Consequences

- provider-supplied CID inventory can become data-driven instead of fixed to
  eight source constants;
- raw arena handles cannot escape into the official public ABI;
- any future widening of the local bounds or context ABI requires a separate
  decision and qualification.
