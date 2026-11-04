# Diagnostic continuous Darwin process watch

The prior `WP01` watcher returned unknown after one timeout (at most 900
seconds), which cannot continuously observe a long-lived process. The
experimental `WP02` request retains the same kqueue registration and repeats
bounded waits when no event arrives. `WP01` keeps its existing one-timeout
refusal. Both protocols retain the same request-bound ready and exit frames;
unknown request versions and zero timeouts are refused. `WP02` emits no
heartbeat: a trusted host must supervise the watcher independently and must
treat helper loss, a stalled helper, or missing/partial frames as unknown.
There is no automatic deadline, workload kill or reservation release.

On one local Apple Silicon Mac, macOS 26.3.1 (a), build `25D771280a`, the
native fixture built with diagnostic compiler SHA-256
`920954769b8fdc51cf50dfcab5c44a4e56cf01f261806a153b21488ba81ac4e6`
and diagnostic packager SHA-256
`f726f9dd8a4f169187275797a74d55ad3c62cc5f681cd31f19e1a28d67834f8d`.
Source SHA-256 was
`3f28b4d28631c175b572d4c0a6cf8490b090bc6911b8aa353fafbec6e8be2823`,
the test observer SHA-256 was
`c65293d81d828c57ff462b3d1b103ffc11be46e94039c143bb9e09eef206cf7d`,
and the strictly verified ad-hoc signed watch image SHA-256 was
`e0dafed1d7f09accb6c1d362d9be3027ebc1acb99fb255fe88cc41c25dd461c3`.

The fixture observed a normal child exit after more than two 1-second timeout
intervals, refused fork and exec events after more than two intervals, and
refused a wrong identity, reaped PID, invalid protocol and zero timeout. The
original mode still refused after its timeout. A separately built mutation
that disabled the `WP02` repeat branch failed the persistent case as expected.
These are short owned-child tests, not a 900-second or production endurance
run. The new image has not been tested on the three target Macs.

This change does not supervise or terminate a process, enforce memory, GPU or
CPU limits, prevent a fork or exec, establish complete descendant termination,
authenticate the helper, recover after a crash, qualify selfhost, or implement
a governor. The Python program only builds and observes native test fixtures.
No model, network service, deployment or persistent process was started.
