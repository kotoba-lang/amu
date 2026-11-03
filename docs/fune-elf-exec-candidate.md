# ELF preflight on fixed-fixture execution (JUN-777)

The worker's `O` path now runs the bounded ARM64 static ELF preflight on the
retained executable before checking the existing fixture digest and executing
it. The preflight independently reopens the file beneath the frozen root and
checks that it has the same device and inode as the descriptor that is later
executed. A preflight error terminates the worker before execution or a
workload output frame. The existing digest pin, fixed output/status checks,
root, capability and namespace rules remain in force. `A` is still a separate
single-use diagnostic and cannot be followed by `O` in one worker session;
`O` performs its own preflight rather than consuming a previous `A` result.

On ARM64 Linux, a test-only seccomp rule denying `pread64` caused the normal
worker to refuse before execution. A separately debug-built mutant skipping
the preflight executed the same pinned fixture under that denial, establishing
that this control exercises the new gate. The observer in
`scripts/seed/check-fune-elf-exec.py` repeats both cases with supplied images;
it does not authenticate them. The static ELF observer and existing fixture,
worker and driver tests remain separate.

This is not arbitrary ELF admission, a complete ELF verifier, or authorization
to run untrusted workloads. The same-principal race, descriptor provenance,
network/syscall policy and general container boundary remain unqualified. The
ELF preflight subset and exclusions are described in
`docs/fune-static-elf-preflight-candidate.md`.
