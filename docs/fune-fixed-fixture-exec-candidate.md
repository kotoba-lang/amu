# Fixed fixture execution candidate (JUN-777)

This is an execution smoke test, not the fune workload admission or CLI. After
`T`, the single-use diagnostic `E` accepts only a process spec containing
`/app` as the sole argument, `/` as cwd, and an empty environment. It reopens
`app` under the retained root, checks the reopened and previously validated
executable descriptors identify the same inode, and requires exactly 320000
bytes with SHA-256
`bb4aef9071c2a402b36c72012e89e166aaedb44cc811e05e4cdef9e150063b09`.
This is the static ARM64 ELF compiled from `fixtures/exec-probe.kotoba`, whose
main returns zero. The root was remounted read-only before the check. No other
image or command is accepted by this diagnostic.

The PID-namespace init forks one child. It duplicates the retained executable
FD, closes all other descriptors including stdio, and uses
`execveat(AT_EMPTY_PATH)` with a fixed argv and empty environment. The child
inherits the already established root, namespaces, capability reductions,
`no_new_privs`, and narrow namespace filter. The init waits at most five
seconds, kills and reaps the child on wait failure or timeout, and returns
`K` only for a zero exit status. The diagnostic cannot run twice, before `T`,
or after the data-only `C` terminal. It emits no workload output or exit code.

In the local ARM64 VM, source-pinned worker observations passed for the exact ELF,
rejecting changed, shortened and extended bytes, a different argv or env,
early or repeated use, a test-only `execveat` denial, and a denied clock.
The test detects a debug mutant that bypasses the hash check. A separate
systemd-owned cgroup with memory and CPU limits admitted this diagnostic with
`TasksMax=5`; `TasksMax=4` refused the fork and incremented `pids.events`.
Those counts include the Python test observer and are not fune's cgroup
admission policy.

A test observer created a local OCI layout containing this ELF, then ran the
existing native runnable producer against its pinned manifest. It passed the
producer's hex stream to the worker and appended the `E` and `X` diagnostics;
the worker executed and reaped the fixed ELF. A wrong manifest digest and a modified layer were
refused by the producer before any stream. This is Python orchestration of
native components, not a fune CLI run, a registry pull, a supervisor launch,
or an authenticated runtime-admission decision. The same OCI observer also
passed within the separate systemd scope with 64 MiB memory, 50% CPU and five
tasks; that scope includes the observer and producer. The producer binary is an
existing task artifact, not a new independent implementation.

The source-pinned worker matched the debug-compiler build byte for byte; the
hash-bypass mutant was separately debug-built. These observations do not
qualify arbitrary executables,
stdout/stderr capture, nonzero exit reporting, PID-1 workload supervision,
full seccomp policy, network/host escape resistance, enforced fune cgroup
admission, recovery, or lifecycle operations. The older worker document and
factory comment stating that no code can execute are awaiting owner review.
