# Fixed-source cgroup-v2 limit candidate (JUN-777)

`fune-cgroup-build aarch64-linux HOST OUTPUT` builds only the pinned
`seed/fune/cgroup-limits.kotoba` using the native ARM64 backend. This is a
configuration primitive, not a workload launcher or an isolation boundary.

The caller passes FD 3 for a newly created, empty, caller-owned delegated
cgroup-v2 workload subtree. The helper requires a non-root UID and matching
real/effective UID and GID, verifies the
FD's filesystem type, directory type and owner, and checks the `populated 0`
line of `cgroup.events` (including descendants). It takes three big-endian
u32 values from stdin: memory bytes (at least 1 MiB), maximum processes
(1–4096), and CPU quota in microseconds (1000–1000000 per 100000-us period).
It sets and reads back `memory.max`, `pids.max`, and `cpu.max`, using fixed
filenames resolved by `openat2` without symlinks. `K` on stdout and exit 0
mean all three values were written and read back; errors refuse with exit 2.
K is not authorization to launch or proof of lasting enforcement.

The caller must provide the trusted FD to an exclusively owned subtree and
keep other writers out. Checking `populated` is not atomic with configuration;
a same-UID process can race or later change the subtree or its settings. The
helper does not enable controllers, inspect effective ancestor limits, attach
processes, impose a wall-time or output limit, or remove any cgroup. A failure
can leave partially changed limits, so after any refusal, interrupted setup or
uncertain result the caller must discard its owned subtree. This candidate
never modifies unrelated cgroups by design, but it cannot establish ownership
of the FD on the caller's behalf. It does not provide crash recovery.

For an isolated ARM64 Linux test, launch `scripts/seed/check-fune-cgroup-limits.py`
as a non-root user in a fresh delegated systemd scope, passing a source-matched
native compiler and a new output directory. The observer creates and removes
only its own test cgroups and checks filesystem, bounds, controller refusal,
nonempty and populated-descendant refusal, source pinning, readback, and
kernel-observed pids, memory, and CPU controls. It uses host Python as an
observer, not as the product implementation, build fallback, or CI runtime.
The test requires delegation and is not a substitute for workload lifecycle,
concurrency, recovery, or platform qualification.
