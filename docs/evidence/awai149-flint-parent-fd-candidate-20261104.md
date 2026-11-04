# Flint parent/child FD helper candidate

`seed/macos-flint-parent-fd-packager.kotoba` is a source-only Darwin ARM64
diagnostic candidate, based on the existing directory identity helper. Its
intended fixed target accepts inherited parent directory FD 3 and child FD 4,
requires both to be directories on the same device with distinct nonzero
inodes, and compares FD 4 with `fstatat64` of the fixed `.kapitsa` entry
relative to FD 3. The intended flags combine `AT_SYMLINK_NOFOLLOW`,
`AT_SYMLINK_NOFOLLOW_ANY` and `AT_RESOLVE_BENEATH`. On success it intends to
write one hex-encoded `ADP1` frame containing the parent and child identities;
it intends to refuse without a frame otherwise.

The existing Amu CLI `check` accepted the source. A separate byte-level check
confirmed the fixed-name, frame-magic and flag constants. Neither confirms the
generated instruction stream or its behavior: no image has been generated,
signed or executed, and there is no independent instruction derivation yet.
The previous three-Mac Python FD diagnostic is not a test of this source.

This is stacked on the closed draft #1810 and does not fix its dependencies.
It cannot prevent a later rename, bind snapshots or file reads to held FDs,
establish host ownership, block aliases or concurrent writes, or qualify a
resource governor. A trusted host must retain the FDs, validate this exact
helper's artifact and successful exit, bind all other observations to them,
and enforce isolation throughout use. A match is not permission to publish or
load a model. Real artifact generation and high-load work require the
qualified native governor.
