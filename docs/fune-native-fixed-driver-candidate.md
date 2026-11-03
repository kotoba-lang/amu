# Native fixed-fixture driver candidate (JUN-777)

The source-pinned `fune-driver-build aarch64-linux HOST OUTPUT` factory builds
only `seed/fune/fixed-fixture-driver.kotoba`. Its output is a diagnostic
building block, not a general fune CLI or release admission. The driver is
invoked with a caller-opened, exclusively delegated, empty cgroup-v2 parent as
FD 3, followed by supervisor, worker and producer image paths, a local OCI
layout root, and manifest digest. The caller must enable the CPU, memory and
pids controllers on the parent and exclude concurrent writers. The driver
never changes the parent controller setup.

It refuses closed standard descriptors and closes other inherited FDs. It
opens each candidate image without following the final symlink, requires a
regular file, copies at most 16 MiB into a memfd, seals against write/grow/
shrink/further seals, and hashes that immutable snapshot. It accepts only the
three hard-coded candidate digests for the source-built supervisor and worker
and the existing native producer. These are fixed test identities, not an
authenticated release distribution mechanism. The OCI producer independently
checks the caller's manifest and layer digests; the worker admits only its
separately pinned output fixture.

The driver verifies the delegated parent type, owner and unpopulated subtree,
creates a PID-named child exclusively, configures and reads back 64 MiB,
`pids.max=4`, and `cpu.max=50000 100000`, then starts the sealed native
supervisor in its fixed-output mode. The worker enters the child cgroup before
exec. The supervisor receives an EOF stdin pipe and no other inherited host
FDs except the required snapshots, child cgroup and stdout/stderr. The driver
captures at most the fixed 17-byte response, verifies supervisor status and
frame, checks that its child cgroup is unpopulated and still has the same
inode, removes it, then releases the response. Failures release no stdout;
if it cannot prove and remove its own child it reports cleanup pending and
preserves it. It does not kill other processes to make cleanup succeed.

Source-pinned ARM64 observations covered the fixed OCI output/status,
malformed image hashes, symlink and FIFO refusal, denied seals, close_range
and execveat, closed standard descriptors, a populated parent whose occupant remained alive,
ordinary and foreign-owned cgroup FDs, a PID-name collision preserved without
removal, denied clock, missing controllers, cleanup obstructed by a test-owned
child, and SIGKILL leaving an empty stale cgroup that the observer removed. The observer also saw a different stdin pipe in the
supervisor from the driver's input pipe. An initial ARM64 flag error left a
test-owned cgroup pending; systemd removed the disposable scope and its
absence was verified. A debug mutant that skipped the supervisor
digest check accepted a one-byte-modified supervisor that the normal driver
refused. Closing stdin outright then caused a producer runtime regression;
passing EOF on a valid pipe fixed it. The driver, worker,
supervisor and producer were each rebuilt with the current native compiler;
the latter three matched the fixed candidate digests byte for byte. The
producer source is an existing generated task artifact, not a packaged release.

After building the pinned driver and preparing the delegated parent, an
operator can invoke the diagnostic without Python as follows (paths and digest
are examples; the three binaries must match the fixed candidate hashes):

```sh
./fune-fixed-driver /absolute/supervisor /absolute/worker /absolute/producer \
  /absolute/oci-layout sha256:MANIFEST_DIGEST 3</sys/fs/cgroup/DELEGATED_PARENT
```

Successful stdout is a 17-byte binary frame, including exit 7 and the 11-byte
fixture output; the driver itself exits 0. This is not a shell-compatible
workload exit-status interface.

SIGKILL can leave a stale cgroup: no crash/restart collector is implemented.
The parent and child ownership checks are not atomic against a hostile
same-principal process. This does not qualify arbitrary OCI images, network or
filesystem escape resistance, a full syscall policy, stderr, general exit
codes, registry pulls, image authentication, lifecycle operations, or a
user-facing Docker-compatible command.
