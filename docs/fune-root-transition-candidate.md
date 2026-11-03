# Private root transition candidate (JUN-777)

For the runnable diagnostic terminal `T`, the worker validates and retains
root, cwd and executable descriptors, then freezes the private tmpfs. While
procfs is still reachable, it obtains the supported capability range from its
verified procfs file. It changes to the retained root, calls `chroot(".")`,
opens `/` and compares device and inode to the retained root, changes to the
retained cwd, and compares `.` with that cwd. Any failed operation refuses
before the `D` response. Only then does it drop and verify capability sets and
install the existing narrow namespace filter. `C` is still the data-only
terminal and does not make this transition.

The optional, single-use diagnostic `G` rechecks root and cwd identities and
requires opening `/proc/self/status` to fail with `ENOENT`. It is a useful
probe only for test images that do not contain that path; it is not a general
host-access or workload-safety proof. The existing `J` remount probe now
attempts `/` after the transition, rather than the old `/tmp` path, and
requires `EPERM`.

On the task's ARM64 Linux VM, source-pinned tests passed for `/` and `/bin`
working directories and observed the absent host procfs path; a test-only
seccomp rule denying chroot caused refusal before `D`. The existing readonly
FD, capability, namespace, and PID regressions passed. The delegated cgroup
observer also passed runnable and 640-operation streams. A debug mutant that
skipped chroot failed the root identity check, and another that additionally
skipped the transition's identity checks was detected by `G`. The mutants
were separately debug-built; the unmodified source-pinned worker matched the
debug-compiler worker byte for byte.

After the chroot, `/proc/PID/mountinfo` is relative to the process's new root
and the old `/tmp` entry is no longer available for that observation. The
worker checks tmpfs flags before the transition; `W` tests a write via the
original FD after it. Earlier mountinfo results belong to the previous
pre-chroot worker identity. Correction of the older worker document's wording
is awaiting owner review.

The `T` path still executes no workload. Chroot alone is not a sandbox, and
these tests do not establish protection from hostile same-principal processes,
FD leaks in a future executor, workload PID-1 behavior, complete syscall
filtering, authenticated admission, or crash-safe lifecycle/resource limits.
