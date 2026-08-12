# ADR 0250: Make Amu the single-Node compiler front

## Decision

`bin/amu` is the canonical, plain-Node compiler launcher. It dispatches
directly to the target-specific NBB compiler entrypoint, so a cold compile
starts one launcher runtime instead of loading NBB once to interpret a launcher
which then starts NBB again for the compiler. Direct commands are canonical;
the historical `-M`, `-M:compiler`, and `-M:compile` boundaries remain accepted.

`bin/kotoba` remains an NBB compatibility API. `bin/kotoba-compiler` delegates
to Amu. JVM-only commands keep their existing `clojure -M:run` or
`clojure -M:native-run` implementation. This decision changes process topology,
not the reader, HIR/KIR, admission, backend, verifier, artifact, or provenance
contracts.

The dependency-classpath cache is bound to the exact `deps.edn` bytes and
dependency-store identity. A cache hit must be a regular, non-symlink,
current-user-owned, non-group/world-writable file; entries must exist and
resolve under the repository, Maven repository, or selected Git library store.
The checked-in lock remains the JDK-free primary resolver. Cache publication is
private and atomic, and failure to publish cannot deny compilation.

## Evidence boundary

`npm run test-amu-launcher` compiles through both fronts and requires identical
native artifact and provenance bytes, then exercises Amu's `-M` compatibility.
The clean-clone and JDK-free native suites invoke `bin/amu` directly with JVM
tools replaced by rejecting stubs. Multi-OS CI exercises the same Node entry.

`npm run benchmark-launcher` alternates the two fronts, records every sample,
host and commit identity, and refuses artifact/provenance drift. Its result
measures only removal of the compatibility launcher's extra NBB startup. It is
not a claim that compiler phases or generated-program runtime became faster.
Persistent workers remain the preferred repeated-compilation path.
