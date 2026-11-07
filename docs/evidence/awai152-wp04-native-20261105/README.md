# Experimental watcher with heartbeat and exit status

The diagnostic watcher adds `WP04`: it keeps one kqueue registration across
bounded idle intervals, emits request-bound sequenced `WH01` heartbeats, and
emits `WS01` with the observed raw wait status on exit. Existing WP01, WP02,
and WP03 formats and behavior are retained. Missing status and observed
fork/exec remain unknown; a watcher failure or missed heartbeat is not proof
that the workload stopped.

The selected Kotoba monitor accepts WP04. Its active state stores the exact
request and has a 38th field set to -1; after a validated terminal frame and
EOF that field contains raw status. WP02 retains its 37-field layout. Invalid
state, request mismatch, clock rollback, deadline expiry, repeated sequence,
malformed frame or missing EOF returns unknown. The host must still enforce
the monotonic clock and I/O deadline, authenticate process/pipe identity,
and separately retain a durable reservation. Neither a zero status nor phase 2
proves descendants stopped or permits release.

On 2026-11-05, the signed diagnostic watcher ran locally and over strict
Tailscale SSH on naphtali, benjamin and judah (Darwin ARM64, macOS 26.7.2,
build 25G332). On each target the request-bound status frames for owned
children exiting 0, exiting 7 and killed with SIGKILL matched their parent's
wait status (0, 1792, 9). A separate sleep case produced at least two
sequenced heartbeats before its zero-status exit. Exec/fork cases triggered
after heartbeats were refused on all three targets. Task-owned children and
watchers were reaped and completed wrappers reported their temporary
directories absent. Each case is a bounded sample, not an endurance test.

On the local Mac the WP01/WP02 transition controls and WP02 heartbeat case,
WP03 status/transition cases, and WP04 status/heartbeat/transition cases
passed. A missing-status registration mutant and a repeat-disabled mutant
were refused. Selected-source native monitor tests passed including WP04
status 9, mismatched request, missing EOF, repeated heartbeat, timeout and
state-status corruption; the existing rollback and request-binding mutants
were detected. A separate local observer captured a four-second WP04 stream
(four heartbeats and twelve polls) and replayed it through the native selected
monitor; the terminal state retained status 0. This replay is offline, not a
live native supervisor or authenticated clock.

An independent source-operation model matched 326 instruction words against
the emitted diagnostic Mach-O; LLDB checked operands and branch targets and
rejected register/branch mutants. This does not qualify all ABI or concurrency
behavior. Full CLI product and CI tests have not been run for this change.
The watcher source hash was
`550d7a968df4d9e6c9359d4cbf77fc96ddb6162cc5038d9c9b37fefd340e9623`,
signed watcher hash
`ad32993a07f5e8b3db5d46f695c9d1a2b319974f145f13ebe3406c23810eba6e`,
and recorded replay source hash
`aaf150c9e90e8529e96a00051f3ccde295af6b5971eb9e85c8d26022b17eba1b`.
Diagnostics used short CPU limits without a hard memory cap. Archived scripts
use task-local paths and external pins; they are not deployment tooling.

This remains a watcher candidate, not the resource governor. Process-tree and
IPC containment, durable reservation and crash recovery, permission and PID
reuse races, trusted native supervisor, GPU/unified-memory limits, actual
Kapitsa serving and Itonami/GitHub state integration remain unqualified.
