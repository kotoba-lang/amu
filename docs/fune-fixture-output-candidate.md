# Fixed fixture output and exit candidate (JUN-777)

The single-use `O` diagnostic executes only the 320000-byte static ARM64 ELF
compiled from `fixtures/output-probe.kotoba`, with SHA-256
`e0e1ca9321c42adfff1f7e9fe490a5750310b89bf9a9b0b577dcef9563ec57a7`.
It retains the same exact `/app` argv, `/` cwd and empty environment checks as
`E`, and verifies the executable inode and digest after `T`. The prior `E`
zero-exit fixture remains supported separately. Neither admits arbitrary
images or authenticates a producer.

The namespace init creates a nonblocking close-on-exec stdout pipe and forks.
The child sends only stdout to the pipe, closes stdin and stderr and all other
inherited descriptors except the close-on-exec executable FD, then calls
`execveat`. The parent drains at most 4096 bytes while checking `wait4` and a
five-second monotonic deadline. It kills and reaps the direct child on timeout
or failure; it does not signal the PID again after reaping. On successful
normal exit 7 and pipe EOF, it returns `K`, one exit-code byte, a big-endian
32-bit output length and the captured bytes. Overflow, a signal, an unexpected
exit, a clock failure, or an execution failure causes refusal without a
success frame. This fixed fixture writes `fune-smoke\n` and exits 7.

On the local ARM64 VM, source-pinned worker tests captured the expected bytes
and status, including after the native runnable producer streamed a locally
constructed fixed OCI layout. The OCI observer passed in a separate systemd
scope with 64 MiB memory, 50% CPU and five tasks; four tasks denied the fork
and incremented `pids.events`. These counts include the Python observer and
producer, and do not qualify fune cgroup admission. Changed bytes, the other
fixture, denied `execveat`, denied clock and a repeated `O` were refused. Separately debug-built
controls pinned to known test programs confirmed that 5000 output bytes were
refused by the 4096-byte bound; widening the bound in a control accepted all
5000 bytes. A busy-loop control was killed and reaped after approximately five
seconds. Killing the outer worker while that busy-loop child ran left the
mapper, namespace init and workload child gone or zombies. Those controls are
not source-pinned product qualification; the unmodified source-pinned worker
matched the debug-compiler worker byte for byte.

This is not a general process runner: status 7 and output are tested for one
fixed image, stderr and stdin are closed, the producer/worker handoff is driven
by a Python observer, and the supervisor does not invoke `O`. Child-tree
reaping, output flow control for arbitrary programs, authentication, full
syscall policy, network/host escape resistance, mandatory fune cgroup limits,
CLI lifecycle and crash recovery are unqualified. The original `E` document
still correctly describes the separate zero-exit, no-output diagnostic.
