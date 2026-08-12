# ADR 0252: Gate the JDK-free dependency lock on Amu CI

Status: accepted

## Context

The primary Node compiler resolves its pinned source closure from
`deps-lock.edn` without a JVM. The lock is bound to the SHA-256 of `deps.edn`
and fails closed when that digest is stale.

Amu main advanced `kotoba-native` in both files but changed only the lock entry,
not the lock digest. The existing NBB classpath test detected the mismatch and
the real JDK-free conformance refused to compile, but neither command was wired
into Amu's required workflows. JVM-backed CI prefetched the same dependency
graph independently, so all 13 jobs could be green while `bin/amu` was broken.

## Decision

Every full CI host must run two distinct gates before compiler conformance:

1. `test-nbb-classpath-hermetic` validates the checked-in lock schema and exact
   `deps.edn` digest without requiring network access.
2. `test-jdk-free-native` removes JVM executables from `PATH`, resolves the
   checked-in lock, compiles representative AArch64 artifacts, independently
   extracts them, and executes them through the W^X loader.

Workflow lint requires both commands, preventing a later edit from silently
removing the property. Dependency pin changes continue to require running
`nbb scripts/lock-classpath.cljs`; hand-editing one lock entry is insufficient.
The generator also canonicalizes GitHub HTTPS origins with a trailing `.git`,
so lock bytes do not depend on which resolver first populated `~/.gitlibs`.

## Evidence boundary

The hermetic test proves lock consistency and local fail-closed behavior. The
JDK-free conformance additionally needs its pinned git closure to be present or
fetchable and proves a bounded native compilation/execution slice. Neither is a
claim that arbitrary dependency sources are available offline.
