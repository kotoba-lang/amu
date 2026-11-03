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
producer fd, producer digest, absolute layout root, and manifest digest. Digests use lowercase
`sha256:<64 hex>`. The root path is bounded, absolute and cannot contain a
colon, empty, dot or dot-dot component. The producer's bounded planner counts
the filesystem commands it emits and sends that count in a terminal `C` frame.

The supervisor constructs the producer environment (including one scoped FS2
root) instead of inheriting arbitrary caller variables. It connects producer
stdout directly to worker stdin with a pipe, without a Python or shell relay.
The worker output is kept on a separate pipe. Each child is given a parent-death
signal and `no_new_privs`, and descriptors above stderr are marked close-on-exec.
Only if the producer exits zero does the supervisor append the worker's hex
shutdown byte. It then waits for the worker to exit zero and checks the exact
readiness line, up to 640 `K` bytes, and a final `D`. The worker emits `D` only
when the producer's count matches the worker's completed operations, and then
refuses further writes. A missing or mismatched terminal frame is a failure.
The supervisor trusts the selected producer and worker to implement this
protocol; the marker is not a cryptographic attestation. Any other result is a
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
expected three acknowledgments and a terminal `D`. A corrupt final layer failed;
a wrong terminal count, missing terminal frame, unsealed image,
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

A prior-version test mutant that ignored the producer's exit status incorrectly
reported success for the corrupt-layer fixture; another mutant that skipped
executable-digest checks incorrectly accepted a wrong digest. Both failed the
prior observer. The verifier/worker pair was independently checked with
private-root file readback in Kotoba PR #1174; this supervisor test checks
statuses and acknowledgments and does not itself inspect the final private file.
With the terminal-count protocol, separately compiled producer fixtures with an
incorrect count or no terminal frame were refused. A worker mutant that ignored
the count and a supervisor mutant that ignored the final `D` each incorrectly
reported success and failed the observer. These checks do not prove that an
untrusted producer emitted the entries required by a manifest.

The optional `--compiler` and `--output` flags on the observer build the exact
candidate supervisor with Amu and verify that altered supervisor source is
refused. The observer stages images and inspects processes only. A slow native
producer and task-owned test layouts can be supplied with `--slow-producer` and
`--large-digest` to repeat the timeout, parent-death, and large-stream cases.
The optional `--stress` check exercises the executable image size boundary.
Native x86, exact-head hosted CI, an authenticated digest authority, and a
product supervisor integration remain open.

## Acknowledgment boundary candidate

A separate OCI fixture has four layers of 128 regular files. It produces 512
create/update commands and 128 final-mode commands. On ARM64, the previous
supervisor refused this fixture while direct producer/worker streaming
completed and checked the mode. The source-pinned supervisor built by the regenerated ARM64 compiler
accepted it; a debug-built worker that emitted one extra `K` was refused.
The extra-ack worker was independently observed emitting 641 `K` bytes,
and a debug supervisor mutant with its bound increased by one accepted it. The supervisor still trusts its authenticated worker and producer;
the count is not a proof that a producer emitted all image entries.

## Optional delegated cgroup for the worker tree

A caller may append four arguments after the six diagnostic arguments: an
already-open cgroup-v2 directory FD, memory bytes, process limit, and CPU
quota in microseconds per 100000-us period. The caller must provide an empty,
exclusively owned subtree already configured to those exact finite limits.
The fixed cgroup helper can configure it separately; this supervisor does not
create or configure cgroups. With the extension present, the worker-side
supervisor child checks the FD's cgroup-v2 type and owner, subtree population,
and all three exact kernel values, moves itself into `cgroup.procs`, and
verifies membership before executing the worker. Thus worker initialization
and its descendants begin inside the cgroup; the supervisor and producer stay
outside it. A failure refuses the run. The original six-argument diagnostic
mode still runs without a cgroup and does not qualify resource enforcement.

The owner must keep the cgroup exclusive and the limits stable throughout the
run and dispose of the owned subtree afterward. The checks are not atomic
against a hostile process with the same host principal. This does not provide
workload execution, CPU time or output deadlines, PID-namespace isolation,
recovery after a controller crash, or a complete security boundary.

On the local ARM64 Linux host, an observer saw the worker parent and child in
the target cgroup while the supervisor and producer remained outside, and
observed a nonzero memory charge there and no cgroup directory FD in the
post-exec worker parent. Both the data stream and a runnable
image stream through `T` and a 640-operation stream completed under the
configured limits; a non-executable target was refused. Mismatched values, a
non-cgroup FD and a populated target
were refused without killing the existing test process.
With `pids.max=1`, the worker could not fork its child and the kernel's
`pids.events` recorded the refusal; a four-process limit was a passing
control. Killing the supervisor left this test's cgroup unpopulated. Debug
controls bypassing the join or pids comparison were detected; omitting the
move write failed the membership check. These are bounded observations, not
proof of adversarial race resistance or crash-safe cgroup ownership.
