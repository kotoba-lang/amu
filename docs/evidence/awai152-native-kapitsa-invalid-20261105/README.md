# Native Kapitsa startup failure and FIFO hold diagnostic

On 2026-11-05 a diagnostic Amu emitter produced three profile-specific signed
Mach-O launchers using the pinned bootstrap compiler SHA-256
`920954769b8fdc51cf50dfcab5c44a4e56cf01f261806a153b21488ba81ac4e6`
and FS2 packager SHA-256
`df0e94211a35d84901ebcf2a8620cb653140d957732474ff77bd0cdd5b5bf4c5`.
The emitter source SHA-256 was
`041cfa2954c59d88eb73c1ef3ea0ab1eac2afe49f8663e55821ed67a9459716d`;
unknown profiles and malformed nonces were refused before output. Rebuilding
with the same nonce after comment clarification reproduced all three signed
launcher digests. The helper uses SETEXEC, START_SUSPENDED and a private
256 MiB spawn attribute, and fixed loopback/private/local arguments. The
nonce-derived model path is not inspected by the helper; the caller is
responsible for ensuring its contents are test fixtures, not model files.
An independent test-only encoder and LLDB disassembler matched the emitted
instruction streams (391 instructions for naphtali and benjamin, 388 for
judah); a changed-register mutant was rejected for each profile. This checks
the modeled instructions, not all runtime or private-ABI semantics.

On naphtali, benjamin and judah (macOS 26.7.2, arm64, build 25G332), the
operator used strict Tailscale host keys and verified signed launchers, the
installed Kapitsa 0.2.26 SHA-256
`20db8dadcb79de820d237367ca93d7ac66f8a70d91d5513f6e1ab77253925daa`,
and WP04 watcher SHA-256
`ad32993a07f5e8b3db5d46f695c9d1a2b319974f145f13ebe3406c23810eba6e`.
A new task-owned mode-0700 model directory contained only a one-byte invalid
`config.json`. An allow-default sandbox denied process-fork. The native
launcher replaced itself with Kapitsa and stopped before execution; a Python
operator verified the stopped executable path and registered the watcher.
Each Kapitsa process rejected the invalid configuration, exited 2, and WP04
reported raw wait status 512. A separate run on each host checked loopback
port 42781 was bindable after exit. Task directories were removed and their
absence observed. These tests did not load model weights.

A second diagnostic combined the same startup failure with the existing
native RGQ4 FIFO candidate SHA-256
`e0686d9f82fc3eb5f218a0e716d373ef3a0a9565b0e09f39bef4ce48e0ae9da7`.
A Python coordinator queued two synthetic tickets, reserved the first, waited
for watcher readiness and a heartbeat while the child was stopped, and resumed
it. On all three Macs the watcher returned the matching failure status, and
the FIFO still refused front/dequeue/next reserve until explicit test-only
reconciliation after the direct child was reaped. Task directories were
removed. This coordinator is not the intended native supervisor.

An earlier attempt to block startup with a FIFO `config.json` was inconclusive:
opening a writer did not establish the identity or continued existence of the
reader, and processes could exit while observation was in progress. Invalid
regular configuration was used instead; no FIFO reader ownership is claimed.

The private attribute ABI, process-tree lifetime, parent/watcher death and
recovery, resource admission, Metal and unified/GPU memory enforcement remain
unqualified. `sandbox-exec` here permits other operations and the test does
not prove a service never bound the port transiently. No model inference,
Itonami execution, GitHub state publication or persistent deployment occurred.
