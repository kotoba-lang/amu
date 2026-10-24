# Scoped native filesystem locks

AWAI-81 adds two wire-35 string operations to the Linux static runtimes:
`pathFLOCK_SEP` acquires a nonblocking exclusive kernel flock, and
`pathUNLOCK_SEP` releases it. Both return `1` on success and `0` on refusal,
contention or filesystem failure. The existing filesystem capability and
root grant are required. This does not introduce a new authority or wire.

The provider holds one lock per process. A second acquisition is refused;
an unlock must match the normalized path of the held lock. Paths are opened
beneath an admitted root with no symlink following. The runtime stores its
canonical path in a reserved part of the fixed RW map, so lock acquisition
does not request mmap after seccomp installation. The kernel releases the
lock when the process exits or is killed. A cooperating store must retain a
fixed lock-file inode and never replace or unlink that file.

Atomic durable publication uses a separate data file: write a pending file,
fsync it, rename it over the state file, then fsync the directory before an
acknowledgement. A crash after rename and before directory fsync is an
unacknowledged, uncertain durability window. flock is not distributed
consensus, malicious-writer protection or a hardware rollback anchor.

The [native receipt](evidence/awai81-native-lock-20261024/receipt.json) records
three selfhost generations, F2=F3, identical compiler payloads, and a 9/9
static native gate covering acquisition, reentry refusal, wrong unlock,
release/reacquisition, normalized paths, scope and symlink refusal. Kotoba VM
also exercises this provider in its separate process crash/publication gate.
No C loader, JVM, Node or host implementation is used for execution.

These are local candidate gates. Default bootstrap artifacts, release/CDCI
selection and x86 host execution are not promoted by this change.
