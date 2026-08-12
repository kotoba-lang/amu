# ADR 0251: Make primary Node output publication durable

Status: accepted

## Context

`bin/amu` is the primary compiler front. Its NBB implementation emits Wasm,
KEXE, extracted native bytes, and KEXE provenance without starting a JVM.
However, its output helper still described that route as a development-only
compiler and used a `Math.random` temporary filename followed by
`writeFileSync` and `renameSync`.

That was weaker than the public compiler invariant. A pre-created temporary
symlink could be followed during the write, and a successful write could be
renamed without first flushing the complete file. Atomic namespace replacement
alone does not prove that the published bytes reached stable storage.

## Decision

Every NBB compiler output is staged in an OS-exclusively-created private
directory beside the destination. The file itself is opened with
`O_CREAT | O_EXCL | O_WRONLY` and `O_NOFOLLOW` where the host exposes it, with
POSIX mode `0600`. Publication writes the complete value, calls file `fsync`,
closes the descriptor, and only then performs a same-filesystem atomic rename.
All failure paths close the descriptor and remove the staging directory.

Replacing an existing destination symlink replaces the link itself; the
compiler never opens its referent. Windows private-key/ACL provisioning remains
on the JVM signing path because this Node route does not emit private keys.

## Evidence and boundary

The NBB-only regression suite proves byte-exact publication, replacement,
failure preservation, staging cleanup, destination-symlink non-following, and
owner-only POSIX mode. Workflow wiring makes that suite mandatory on all three
full test hosts and the Windows ARM host; the symlink fixture may report an
explicit skip when the Windows runner does not grant symlink privileges.

This decision provides durable publication for each output file. It does not
claim that a KEXE and its provenance sidecar are a multi-file transaction; each
file retains an independent atomic publication boundary.
