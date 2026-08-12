# ADR 0254: Commit primary output sets fail-closed

Status: accepted

## Context

ADR 0251 made each Node output durable and atomically replaceable. ADR 0253
made the artifact and sealed provenance policy-identical to the JVM path. The
two final paths still had no shared commit point. A crash between their renames
could leave one new file and one old file, with no machine-readable indication
that the visible pair was not a completed compiler result.

Portable filesystems do not provide one atomic rename over two independent
filenames. Hiding that limitation behind a success-shaped result would be a
weaker contract than making the commit protocol explicit.

## Decision

Every primary Wasm and ordinary-native compile now publishes three files:

1. the artifact;
2. `<artifact>.provenance.edn`;
3. `<artifact>.publication.edn`, a deterministic
   `:kotoba.output-set/v1` commit marker.

All three are created exclusively with mode `0600` in one OS-private staging
directory beside the destination. Every staged file is completely written,
`fsync`ed, and closed before any rename begins. Payloads are renamed first and
the marker last. On POSIX, the parent directory is `fsync`ed after each rename,
so payload directory entries become durable before the marker is published and
the completed marker rename is durable before success is returned. The marker
binds the destination basenames, byte sizes, and SHA-256 identities of the exact
artifact and provenance bytes, plus a deterministic SHA-256 over that marker
payload.

If staging fails, no final path changes. If a crash or rename failure occurs
after a payload rename, the marker is absent or stale and cannot match the
mixed set. `amu verify-output-set <artifact>` reads bounded regular files and
rejects a missing, basename-renamed, stale, oversized, symlinked, or
byte-mutated set.
Worker cache hits regenerate the marker for the requested output basename;
the marker is not cached as though paths were artifact identity.

## Evidence and boundary

The NBB-only I/O regression injects failure at the second rename after the
artifact has changed. It proves the prior marker remains, verification rejects
the mixed version, and shared staging is removed. End-to-end Wasm/native tests
require the compiler result to report the marker, verify a completed set, and
reject post-publication artifact mutation. Worker, launcher, and performance
harnesses require and account for the marker.

This protocol provides a crash-consistent committed-set boundary. It does not
make three filesystem names simultaneously visible, authenticate the publisher,
roll back payloads after a process crash, or replace provenance verification.
Node cannot open directory handles for `fsync` on Windows, so power-loss
durability of directory entries on Windows remains an explicit non-claim; the
marker still detects missing, stale, or mixed members when the process resumes.
