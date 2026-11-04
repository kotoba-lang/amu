# Native SETEXEC of fixed Kapitsa version profiles

This diagnostic packager extends the fixed-target SETEXEC experiment with
three explicit profiles: the observed Kapitsa path under each of the
naphtali, benjamin and judah home directories. It emits a native helper with
fixed `--version`, an empty environment, START_SUSPENDED and the observed
private 256 MiB active/inactive spawn attributes. It accepts no model,
serving, arbitrary path, or arbitrary workload arguments; unknown profiles
are refused before output. The generated path is bounded below the stack's
PID slot. This is not a production launcher or governor.

On 2026-11-05 the packager was compiled using the pinned diagnostic compiler
`920954769b8fdc51cf50dfcab5c44a4e56cf01f261806a153b21488ba81ac4e6`
and FS2 packager
`df0e94211a35d84901ebcf2a8620cb653140d957732474ff77bd0cdd5b5bf4c5`.
The current packager source SHA-256 is
`2bd9769a812d362ecd45a33d51630651826c4b945f4efcb903a8dfa48f13819b`.
The signed emitted images for naphtali, benjamin and judah hash to
`a7911905ee6a258bf69e07eaf47ad0d02ecc61996ef50822a41d7174d05f9002`,
`0069b7c8ae635a08faf62f2dbb6909bbf985918275e764d06a22b68b1e15cf0b`, and
`51b6e95ddda282928476947943a9ce71008db54fb6d657edfbf88d182f0310e4`.
The path-bound tightening from 240 to 224 bytes was applied after the target
experiments; rebuilding the current source emitted byte-identical signed
helpers for all three fixed profiles. An independent model matched the
emitted words for each image (175, 175 and 172 words respectively); LLDB
operand checks rejected a register mutant. These are limited diagnostic
checks, not proof of the complete private syscall ABI or host safety.

Under a test-only allow-default, fork-deny sandbox on each corresponding Mac
(Darwin ARM64 macOS 26.7.2 build 25G332), a Python observer first verified
the installed Kapitsa hash
`20db8dadcb79de820d237367ca93d7ac66f8a70d91d5513f6e1ab77253925daa`
and signature. It then waited for the task-owned native helper to SETEXEC and
stop; `ps` showed the expected path, and a separate root observer read
`[256,1,256,1]` for active/inactive memory attributes. The experimental WP04
watcher was registered before resume; its exact status-0 frame matched the
child's exit 0 and the captured version output. Completed wrappers reported
their temporary directories absent and the direct children were reaped.
Target hashing, `ps` and signature checks are separate observations, not a
same-FD immutable executable binding.

In a separate test-only Python orchestration with the native RGQ4 FIFO, each
of the same three hosts acquired a synthetic hold before this fixed native
launch, observed a WP04 heartbeat while stopped, then resumed and checked the
exact version output and zero status. The hold remained until explicit
test-only release/dequeue/settle. This tests a real Kapitsa version command,
not a model request or a native supervisor; FIFO does not validate the exit
proof. See Murakumo's corresponding diagnostic evidence for its operator.

These experiments did not load weights, open an inference listener or start
a persistent service. The paths are user-owned and can be replaced between
checks; the sandbox allows default operations besides fork. OS ABI, full
process and IPC containment, privilege separation, memory and GPU enforcement,
durable reservation, crash recovery, real inference and bot/GitHub state are
not qualified. Archived scripts have task-specific paths and external pins;
none is an unattended deployment command.
