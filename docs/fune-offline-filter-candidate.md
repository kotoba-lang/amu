# Offline socket filter candidate (JUN-777)

After the worker freezes and enters its private root and drops capabilities,
it installs a second ARM64 seccomp filter. The filter rejects `socket`,
`socketpair`, and the three `io_uring` syscalls with `EPERM`; a non-ARM64
syscall architecture is killed. Installation failure terminates the worker
before its committed `D` response. Existing namespace restrictions are
retained. The offline profile deliberately rejects Unix-domain sockets too;
applications needing local socket IPC are not supported by this candidate.

The `N` diagnostic checks these refusals in the worker and checks socket
refusal again in an ordinary forked child. On the ARM64 test host, creating
Unix, IPv4 and IPv6 sockets succeeds outside the worker. The source candidate
passed the private-root observer; a separately built debug mutant that omitted
the second filter failed the diagnostic. The io_uring return values were
observed but not independently attributed to this filter, since the outer
environment may also block those operations. The test observer accepts a
separately built mutant and does not authenticate supplied images.

This is defense in depth, not complete network-off enforcement or a general
syscall sandbox. Inherited descriptors, non-socket kernel interfaces,
exec-inherited filtering, packet escape, other architectures and kernels,
and arbitrary workloads remain separate qualifications. The worker still
accepts only digest-pinned diagnostic executables. The original namespace
filter and fixed-fixture documents record earlier observations and do not
establish this newer filter's results.
