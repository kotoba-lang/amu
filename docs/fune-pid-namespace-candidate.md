# Rootless PID namespace worker candidate (JUN-777)

The source-pinned ARM64 private-root worker creates a PID namespace after the
original parent installs its single-UID/GID user-namespace maps. The mapping
process creates a child as the namespace's PID 1 and waits for its status;
namespace creation, fork, parent-death setup, or the PID-1 check failing
terminates setup before the ready message. The mapping process holds the write
end of a nonblocking pipe. After installing its parent-death signal, namespace
init checks that the pipe still has a writer before continuing. This closes
the race where its outside-namespace parent dies before the signal is set;
`getppid()` cannot perform that check across a PID namespace boundary.

On the task's ARM64 Linux VM, a host-side observer saw `NSpid` end in `1` for
the worker serving the private root, and a targeted seccomp denial of
`unshare(CLONE_NEWPID)` refused before readiness. Killing either the outer
worker parent or the mapping process left namespace init gone or a zombie.
The observer also saw all three worker-tree processes in the preconfigured
delegated cgroup; runnable and 640-operation stream cases passed under its
limits, and the supervisor death test observed the producer and complete
worker tree terminate. The source-pinned worker factory refused modified
source. Debug-built controls omitting namespace creation were caught by the
PID check; omitting both was caught by the host-side PID observation.

These results do not qualify workload execution, PID-1 signal handling or
child reaping for arbitrary workloads, a private procfs, a complete syscall
policy, crash-safe cgroup lifecycle, or protection from a hostile process with
the same host principal. In particular, the worker still mounts no new procfs
and must not execute an image. A launcher must establish and verify its own
process, filesystem, resource and admission boundaries. The older worker
candidate document's statement that no PID namespace is created is awaiting
owner review for correction.
