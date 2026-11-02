# Fixed-source private-root worker candidate (JUN-779)

`fune-worker-build aarch64-linux HOST OUTPUT` builds exactly the pinned
`seed/fune/private-root-worker.kotoba` with the Amu native ARM64 backend. The
factory rejects changed host source and existing output paths. It is not a
general facility for arbitrary guest source to access runtime intrinsics.

The current worker accepts **no OCI data and executes no workload**. It has
only a one-byte shutdown protocol: after setup it prints
`fune-private-root-ready`, accepts `X` and exits; every other input refuses.
The parent starts a child and supplies a single-ID user/group mapping through
proc after a pipe handshake. The child installs a parent-death signal and
checks its parent, enters user, mount and network namespaces, makes mount
propagation private, and mounts a 4 MiB, 4096-inode, `nosuid,nodev` tmpfs over
its own `/tmp`. It creates `/tmp/rootfs` there, marks itself non-dumpable and
sets `no_new_privs`. Extra inherited FDs are closed before the child is made.
The worker exits on failed setup rather than falling back to host staging.
The mount is held only by the child namespace; no named host tree is published.

The parent sets itself dumpable to permit proc mapping on some Linux systems
and remains dumpable for its lifetime. This candidate does not establish a
security boundary against a hostile process with the same host principal.
It also does not create a PID namespace, close
all possible race windows, apply a worker seccomp policy, enforce cgroups,
handle multiple layers or implement persistence/recovery. The temporary tmpfs
limit and protocol are diagnostic, not the final image/storage contract.
Never use this worker as a container launcher or an admission decision.

## Local native ARM64 observations

On the task's Fedora 6.15.10 ARM64 VM, a compiler rebuilt from the candidate
sources built and ran this exact pinned worker. `check-fune-private-root.py`
observed the private `/tmp` tmpfs and its `nosuid,nodev`, 4 MiB and inode
limits in the child's mountinfo, with the mount ID absent from the observer's
namespace. It checked `no_new_privs`, refusal of access via `/proc/PID/root`,
closure of an inherited sentinel FD, graceful `X`, refusal of `Z`, and child
death after the parent was killed. It did not independently observe the user
or network namespace identities because proc access was denied. A modified
worker source was rejected by the factory. Root execution refused; a separate
disposable container with an explicit seccomp rule returning EPERM for
`unshare` also refused before readiness. The test-only seccomp profile allowed
other syscalls and is not a production sandbox.
In a disposable container, an independent outer-directory check passed with
the normal worker and failed when a source-pinned test mutant skipped the
tmpfs mount; this checks detection of that particular missing boundary.

The native check requires an ARM64 Linux host on which unprivileged user,
mount and network namespaces are available. It does not use an external shell
or container runtime as the implementation:

```sh
python3 scripts/seed/check-fune-private-root.py \
  --compiler /path/to/candidate-amu \
  --output /path/to/new-task-owned-output
```

The candidate branch regenerates its bootstrap pins for this factory. Native
x86 worker support, exact-head CI, security review, OCI verification/extraction,
lifecycle and release are still open.
