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

On 2026-11-04 a separate Python/ctypes diagnostic called the existing macOS
`fstatat64` library entry on all three Macs, using flags `0x2820` and a
task-owned mode-0700 temporary directory. For an ordinary child, the returned
directory mode and device/inode at the expected stat64 offsets matched the
held child FD. Replacing the parent entry with another directory produced a
different identity. For a final symlink, the call returned success and the
metadata identified a symlink, not a directory; it did not return an error.
The candidate's explicit directory-type check is therefore necessary for
this case. The test checked the type condition in Python, not in the candidate
machine code. It closed FDs and removed only task-owned temporary objects.
The initial diagnostic expected the syscall itself to fail for the symlink;
that assertion failed on all three hosts and was corrected before rerunning.
The checked-in `awai149-flint-fstatat-probe.py` was then run on each host and
reported `PROBE_END` with all three conditions true; its SHA-256 is
`dd9398f50918b7c7d8d5673204bf7f18f3d428de6f0f30c426934e98e5834aa4`.

This is stacked on the closed draft #1810 and does not fix its dependencies.
It cannot prevent a later rename, bind snapshots or file reads to held FDs,
establish host ownership, block aliases or concurrent writes, or qualify a
resource governor. A trusted host must retain the FDs, validate this exact
helper's artifact and successful exit, bind all other observations to them,
and enforce isolation throughout use. A match is not permission to publish or
load a model. Real artifact generation and high-load work require the
qualified native governor.
