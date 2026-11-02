# Fixed-fixture argv, environment and cwd candidate (JUN-777)

The worker's output diagnostic `O` still accepts only its fixed `/app` ELF
digest and its fixed exit status. It now passes the validated FPS1 argument
and environment entries into the child instead of requiring an empty
environment and no extra arguments. It runs in the already retained and
validated cwd. The worker bounds the source frame to 256 arguments, 128
environment entries, 65,536 aggregate string bytes and 67,500 frame bytes.
The child copies them into its private mapping, adding one NUL per string and
separate NULL terminators for both pointer arrays before `execveat`.

On native ARM64, the original output fixture ran with added arguments and
environment. A separate **debug-built** worker pinned to the test-only
`seed/fune/fixtures/argv-env-stack-probe.kotoba` ELF printed the actual child
stack and cwd: mixed empty and UTF-8 arguments, environment values, `/work`,
256 arguments with 128 environment entries, and a 65,000-byte argument were
observed. A separately built mutant dropping extra arguments and environment
was detected. `scripts/seed/check-fune-process-spec.py` repeats that
observation with supplied test artifacts; it does not build or authenticate
them. The stack fixture deliberately limits its output for large inputs.

This does not admit arbitrary executables, prove general OCI compatibility,
or qualify the security of untrusted workloads. Worker framing does not by
itself authenticate the producer or prove environment policy. The producer's
config validation and the retained-root, filesystem, capability, namespace,
filter and cgroup qualifications remain separate. The older fixed-fixture
documents describe the prior version that refused extra arguments or
environment; those historical statements have not yet been revised.
