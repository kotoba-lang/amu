# ADR 0248: Make persistent compilation transparent without weakening source integrity

Status: accepted

Date: 2026-08-11

## Context

The bounded compiler worker reduced a loaded AArch64 compile to milliseconds,
but users still had to invoke the NDJSON protocol explicitly. Ordinary
`bin/kotoba -M compile` paid for the outer NBB launcher and a new compiler
runtime. Target bundles reduced the cold cost, but did not remove it.

Keeping an old in-memory compiler after `src`, resources, or dependency locks
change is not an acceptable speed trade. Treating compiler diagnostics as a
daemon failure and silently compiling twice is also incorrect.

## Decision

`bin/kotoba` is a pure Node launcher. Ordinary NBB-eligible `compile` and
`check` commands connect to a checkout-specific local daemon. The daemon owns
one existing bounded, target-locked worker per backend and serializes requests
to each worker. A transport failure falls back to the one-shot path; a valid
worker response, including a compiler error, is returned without retry.

The daemon generation binds the protocol, checkout realpath, optional bounded
test namespace, daemon bytes, and launcher bytes. It hashes the compiler source closure when it starts. Each
request compares device, inode, size, mode, mtime, and ctime and hashes changed
files. A changed tree closes the generation before forwarding the request.

Unix sockets and launch locks are owner-only. Stale endpoints are replaced only
after validating type, ownership, and that the recorded daemon PID no longer
exists. Existing worker request and cache bounds remain authoritative.

## Consequences

Repeated ordinary CLI builds reuse verified HIR, KIR, artifact, and provenance
state without changing CLI output or artifact bytes. The first request still
pays worker startup. Daemons stop after an idle interval and do not provide a
durable or cross-checkout cache.
