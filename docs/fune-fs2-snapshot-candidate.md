# fune: sealed FS2 input snapshot candidate (JUN-779)

This candidate adds three Linux wire-35 FS2 forms. It is a primitive for
verifying and later consuming the *same* OCI layer bytes; it does not itself
verify a digest, extract a layer, create a rootfs or run a container. Each
process owns at most one snapshot. Existing FS2 authority and no-follow scope
checks still apply. An absent or outside-scope path does not create a snapshot.

All requests use the existing `NUL FS2 NUL` prefix, one operation letter,
UTF-8 scoped path, NUL, then the tail. Responses use the FS2 acknowledgement.

| Form | Request shape | Tail | Result |
| --- | --- | --- | --- |
| V | string -> string | exact decimal byte size, at most 268435456 | `1` after the regular file is copied and all four seals are applied |
| W | string -> string, bytes or byte segments | decimal `offset:count`, count at most 1048576 | exactly that range from the snapshot; string replies require valid UTF-8 |
| X | string -> string | empty | `1` after closing the snapshot |

V requires no active snapshot and requires the open regular file's size and
the copied length to equal the supplied size. W and X require the same
normalized scoped path as V. They do not reopen the source. Invalid state,
size, range, failed copy or failed seal exits with FS2 refusal stage 15.
An anonymous close-on-exec memfd is sealed against writes, growth, shrinkage
and additional seal changes; the kernel closes it on process exit. No input
path is removed or changed. A caller must hash the complete snapshot and
compare it to its trusted descriptor, then consume only that snapshot. Source
changes while it is copied can affect the copy and are detected only by that
digest comparison. Opening the same inode once without copying is insufficient
because other writers can modify it in place.

The runtime copies in 32 KiB chunks. W returns at most 1 MiB at a time; callers
must bound the lifetime of each returned value. The memfd itself consumes
kernel-managed memory up to the 256 MiB cap. There is no persistent image
cache, independent transaction, multiple concurrent snapshots, decompression,
OCI whiteout/link handling, cross-layer quota, or extraction authority here.
The forms and seccomp changes require an explicitly rebuilt native compiler;
they are not present in the previously pinned bootstrap or public product.

`scripts/seed/check-fs2-snapshot.py` compiles the native fixture with a supplied
candidate compiler. The fixture checks stable bytes after rewriting the source,
binary reads across copy-buffer boundaries, an empty input and state/range
refusals. An independent Linux observer inspects the live memfd's seals, tries
a write, and mutates the source before asking the guest to read. A locally
rebuilt ARM64 candidate passed; a compiler rebuilt with the sealing call
removed failed the observer with seal bits 0. The existing
`check-native-fs2.py` matrix also passed on the same ARM64 candidate. The
candidate compiler image SHA-256 was
`0da6af45521d7ffc4cfcebee2ea56cb5655e3bc15763069a9d21a9d2f8adafd0`.
This is not x86 native, fixed-point, complete security or release qualification.
Exact-head compiler rebuilding and the remaining native gates are required.
