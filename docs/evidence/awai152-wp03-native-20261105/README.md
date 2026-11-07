# Experimental native watcher status frame

The diagnostic Darwin watcher now accepts a separate, one-shot `WP03` request.
It requests `NOTE_EXITSTATUS` as well as exit/fork/exec, checks the event's
status flag and conservative terminal status range, and emits `WS01` followed
by a little-endian raw 32-bit wait status and the exact 32-byte request.
Missing status, stopped-style or out-of-range data, fork/exec, timeout, syscall
error and partial/missing output are unknown. `WP01` and `WP02` retain their
prior request and output formats. `WP03` has no heartbeat and is not connected
to the WP02 monitor or a supervisor: the trusted host must bound its lifetime,
authenticate the pipe, bind the request to its own target, and resolve loss.
Even status zero does not prove descendant termination or authorize release.

On 2026-11-05 the current packager source was compiled by a pinned diagnostic
Darwin compiler and FS2 packager, then emitted and signed the watcher. On the
local Mac and on naphtali, benjamin and judah (ARM64, macOS 26.7.2 build
25G332), the signed image observed task-owned children with exit 0, exit 7,
and SIGKILL. Its exact request-bound frame carried 0, 1792 and 9 respectively,
matching the independent parent `waitpid` status. WP03 fork/exec transition
controls returned refusal. On the local host, WP01/WP02 fork/exec refusals and
WP02's repeated-timeout/heartbeat test passed. A live-child WP03 timeout
returned only readiness followed by unknown, and a mutant that omitted the
status request was refused rather than reporting status zero. The earlier
WP03 run attached before the test Python child reached its ready marker and
sometimes refused; the fixture was corrected to wait for the marker before
registering. The refusal's exact event was not established.

Selected-source native reply tests passed for the WP03 ready and status
frames, malformed/foreign requests, absent EOF, watcher failure and nonterminal
status, along with earlier monitor cases and their negative controls. A
separate local run captured real native WP03 frames and replayed their exact
bytes through the compiled reply parser; 0/1792/9 passed and an always-zero
mutant failed. Replay is offline, not an authenticated live host integration.

An independent source-operation encoder produced 316 instruction words that
matched the emitted diagnostic Mach-O at its entry offset. LLDB disassembled
the modeled words and checked instruction operands and branch destinations;
register and branch mutants were refused. This is not a formal verification,
OS ABI qualification or proof of all races. Full product/CI tests have not
run for this change. Target tests used strict Tailscale SSH, task-owned child
and watcher processes, and reported temporary wrapper directories absent.
No model or persistent service was run.

The watcher source SHA-256 was
`1d0d86768f9c5454d0490e47a248ff349f660fc6c1efe839a99d1af2003a589a`;
signed image SHA-256
`df75083415f92ace3f37fffb69115256e184a98b08cbad766ca0dc57306274d7`;
missing-status mutant image SHA-256
`0d7caecdfd7bb5f6614df55601ad7a3e03896c9042e4a211e2e69f6a07596e6a`.
The reply replay source/image hashes were
`d55b7cd300e6ae5e2a4efbe4d5711ecd008ef289ac4c9c543e59689879b73490` /
`06ad480fada6228069c4adb368cd07166e644e9fb55523e6922ab8715bd2b393`.
Native diagnostics used compiler
`920954769b8fdc51cf50dfcab5c44a4e56cf01f261806a153b21488ba81ac4e6`
and an FS2 diagnostic packager, with short CPU limits but no hard memory cap.
The archived scripts refer to task-local paths and are not deployment tools.

Permission to observe another process, process identity, signal/exit races,
target and descendant lifetime, recovery after observer failure, resource
reservation, GPU/unified memory and authenticated bot inference remain
unqualified. The new frame alone is not a native resource governor.
