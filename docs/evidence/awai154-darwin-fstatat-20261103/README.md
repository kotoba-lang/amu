# Darwin no-follow metadata syscall control

An Amu-built Linux ARM64 packager compiled from
[`macos-fstatat-control-packager.kotoba`](../../../seed/macos-fstatat-control-packager.kotoba)
emitted three arm64 Mach-O programs; each was ad-hoc signed and executed on
macOS 26.3.1. The small packager compiled in a disposable 1 CPU / 2 GiB VM.
The raw `fstatat64` program uses an explicitly inherited directory FD 3 and
flags `AT_RESOLVE_BENEATH | AT_SYMLINK_NOFOLLOW_ANY | AT_SYMLINK_NOFOLLOW`
(`0x2820`), then returns the two `st_mode` bytes. The checked-in assembly is a
one-time instruction derivation record, not an input to the packager build.

The [receipt](receipt.json) records normal 0644 and 0755 files, and separate
setuid, setgid, and sticky files; their complete mode bits were distinct.
It records the final symlink as a symlink, rejects an intermediate symlink
with `ELOOP`, and rejects `..` and absolute paths with `ENOTCAPABLE`. Missing
file and grant return `ENOENT` and `EBADF`. Removing `AT_RESOLVE_BENEATH`
allowed the parent escape; removing `AT_SYMLINK_NOFOLLOW_ANY` allowed the
intermediate symlink. These are distinct negative controls, not production
variants. A one-time Python observer created and removed task-owned files,
signed images, passed the descriptor and checked outputs; its digest is in the
receipt. The product image and packager do not depend on that observer.

The first diagnostic image crashed inside dyld before its entry point on this
host. Adding an empty `LC_DYLD_INFO_ONLY` load command allowed the tested
images to run; the failed image is not evidence of syscall behavior. This is
a syscall control, **not an FS2 wire-35 provider or a Mac selfhost compiler**.
It does not cover frame parsing, all metadata fields, unavailable roots,
concurrent rename, permission denial under another identity, Git operations,
the full checkpoint, governor or bot execution. An owner-controlled tree and
revalidation remain necessary to address metadata/use races. No existing
service or workload was modified.
