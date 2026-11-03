# Rootless worker network namespace observation (JUN-777)

On native Linux ARM64, the source-pinned private-root worker exposes only a
loopback interface, no IPv4 routes and no IPv6 addresses through its
`/proc/<pid>/net` view. In the same observation, the host had a non-loopback
interface and an IPv4 route. A separately debug-built negative-control worker
with `CLONE_NEWNET` removed exposed the host's network view. A test-only
seccomp rule denying the worker's combined network/mount `unshare` caused
refusal before the ready message. The ordinary worker was independently built
by the current source-pinned factory and matched the previously tested image.

`scripts/seed/check-fune-network-namespace.py` repeats these observations on
a rootless ARM64 Linux host. It requires a source-pinned worker, a separately
built no-network-namespace control and an unused output path. It refuses to
qualify when the observer's own namespace has no non-loopback interface or
IPv4 route, because then the negative control would not be discriminating.
It inspects only its own child workers, makes no network configuration changes,
and records the worker and control image hashes. It does not authenticate those
caller-supplied images or build the negative control itself.

This observes a particular startup network view, not a complete network-off
security guarantee. It does not test packet escape, Unix-domain sockets,
loopback interface flags, inherited sockets, later namespace changes, a full
syscall filter, arbitrary workloads, or other hosts and kernels. The previous
worker observation did not independently observe the network view; this is a
new, separately controlled observation rather than a retroactive claim.
