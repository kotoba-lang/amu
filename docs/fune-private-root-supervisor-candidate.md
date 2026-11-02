# Private-root stream supervisor candidate (JUN-779)

The fixed-source `fune-supervisor-build` factory builds exactly
`seed/fune/private-root-supervisor.kotoba` for ARM64 Linux. The resulting
native supervisor is a diagnostic building block, not a production container
launcher. It accepts already-open executable descriptors for the private-root
worker and the Kotoba stream producer. Both descriptors must be sealed against
write, grow, shrink and further seal changes. It hashes each sealed image with
SHA-256 using offset-based reads and checks it against the caller-supplied
expected digest before starting either process. **The caller must independently
authenticate those expected digests**; a digest supplied by an untrusted caller
is not an authorization policy. Same-host-principal interference has not been
qualified.

The arguments after the supervisor image are: worker fd, worker digest,
producer fd, producer digest, absolute layout root, manifest digest, and the
expected count of worker `K` acknowledgments (1–512). Digests use lowercase
`sha256:<64 hex>`. The root path is bounded, absolute and cannot contain a
colon, empty, dot or dot-dot component. The caller supplies the acknowledgment
count; this candidate does not independently derive that count from OCI.

The supervisor constructs the producer environment (including one scoped FS2
root) instead of inheriting arbitrary caller variables. It connects producer
stdout directly to worker stdin with a pipe, without a Python or shell relay.
The worker output is kept on a separate pipe. Each child is given a parent-death
signal and `no_new_privs`, and descriptors above stderr are marked close-on-exec.
Only if the producer exits zero does the supervisor append the worker's hex
shutdown byte. It then waits for the worker to exit zero and checks the exact
readiness line and caller-supplied count of `K` bytes. Any other result is a
refusal. Each direct-child wait has its own 30-second bound. On ordinary producer
failure, the worker gets EOF and exits; timeout handling kills and waits for the
direct child. A successful diagnostic run also shuts down the worker, so its
private rootfs is discarded; it is not returned or published.

This does not prove executable trust, full descendant cleanup under all races,
worker seccomp/cgroup policy, PID isolation, OCI layout/config admission,
transactional publication, workload execution, or Docker compatibility. In
particular, a malicious executable matching an untrusted digest can disregard
its environment. The test producer is source-composed from Kotoba PR #1174,
and the worker is a candidate from this branch; neither is a released artifact.

## Local native ARM64 observations

On the Fedora ARM64 VM, `check-fune-supervisor.py` staged candidate native
images in sealed memfds, supplied their observed SHA-256 values, and invoked
the native supervisor. The same three-layer stream fixture passed with its
expected three acknowledgments. A corrupt final layer failed even when the
expected count matched the two earlier commands; a wrong count, unsealed image,
wrong image digest, changed sealed image, and broken worker were refused.
Caller environment containing `KEXE_STRUCTURED_REPORT=1` did not change the
producer's configured output. SHA-256 checks passed independently hashed ELF
images with 55, 56 and 63 trailing bytes beyond a 64-byte boundary. A sealed
16 MiB image passed the size bound and a 16 MiB plus one byte image was refused.
A 1 MiB file stream also passed. An intentionally
slow producer was killed on the supervisor's time bound; in a separate SIGKILL
experiment the observed producer, worker parent and worker child all became
gone or zombie. These are local observations, not a proof for arbitrary
process trees or all crash races.

A separately source-pinned test mutant that ignored the producer's exit status
incorrectly reported success for the corrupt-layer fixture; another mutant that
skipped executable-digest checks incorrectly accepted a wrong digest. Both
failed the observer. The verifier/worker pair was independently checked with
private-root file readback in Kotoba PR #1174; this supervisor test checks
statuses and acknowledgments and does not itself inspect the final private file.

The optional `--compiler` and `--output` flags on the observer build the exact
candidate supervisor with Amu and verify that altered supervisor source is
refused. The observer stages images and inspects processes only. A slow native
producer and task-owned test layouts can be supplied with `--slow-producer` and
`--large-digest` to repeat the timeout, parent-death, and large-stream cases.
The optional `--stress` check exercises the executable image size boundary.
Native x86, exact-head hosted CI, an authenticated digest authority, and a
product supervisor integration remain open.
