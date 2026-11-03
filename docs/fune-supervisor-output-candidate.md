# Fixed output through the supervisor candidate (JUN-777)

The fixed-source ARM64 supervisor accepts a final `O` argument only with the
existing four delegated-cgroup arguments. The caller supplies sealed worker
and producer memfds and expected digests, a local layout root and manifest
digest, and a caller-owned, empty cgroup already configured with the exact
memory, pids and CPU limits. The supervisor validates the inputs and attaches
the worker-side child before exec as in its existing diagnostic mode. It does
not create the cgroup or authenticate the caller's image digests.

Only after the native producer exits successfully does the supervisor send the
hex-encoded `O` and `X` commands to the worker. The worker's `O` still admits
only the fixed SHA-256-pinned output fixture described in
`fune-fixture-output-candidate.md`. The supervisor waits for worker exit,
checks readiness, up to 640 command acknowledgments, `D`, and exactly the fixed
17-byte stdout/status frame. It releases the frame only after the producer and
worker both exit successfully. A malformed frame or any failed prerequisite
returns an error with no stdout. Existing modes without `O` retain their prior
behavior; `O` without the cgroup arguments is refused.

On the local ARM64 VM, a test observer passed sealed source-built worker and
producer images to the source-pinned supervisor and supplied the fixed OCI
layout. The native producer, supervisor and worker completed the stream, ran
the fixed fixture and returned exit 7 with `fune-smoke\n`. A separate layout
with four layers produced exactly 640 worker operations and still completed
with the same result; `make-fune-output-max-layout.py` can recreate it.
Missing cgroup arguments, malformed mode, mismatched limits, wrong manifest,
wrong executable fixture and a malformed worker output
frame were refused without stdout. A test-only producer that emitted a
complete valid stream but then exited unsuccessfully also released no stdout.
With `pids.max=3`, the fixture child could not fork and the kernel recorded a pids limit event. The test also checks that
its own cgroup is empty after each run. A debug worker emitting a wrong exit
byte was refused; a debug supervisor mutant that skipped the frame comparison
incorrectly accepted it and was detected by the observer.

The source-pinned supervisor and worker each matched their debug-compiler
builds byte for byte; the malformed worker, failing producer and skipped-frame
mutant were separately built controls. The observer creates and cleans its
own delegated cgroups and stages memfds; it does not perform a fune CLI or registry pull.
The mode is limited to one fixed executable and fixed output; it does not
qualify arbitrary process execution, stderr, general exit codes, complete
sandboxing, authenticated admission, cgroup ownership/recovery or container
lifecycle. The older supervisor document's no-execution wording remains
pending owner review.
