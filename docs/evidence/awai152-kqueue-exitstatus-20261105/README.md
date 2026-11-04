# Observing a process exit status with kqueue

The existing WP01/WP02 watcher reports an exit event but not the workload's
wait status: the preceding memory diagnostic showed a successful watcher
frame for both a zero exit and SIGKILL. Apple's XNU source describes
[`NOTE_EXITSTATUS`](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/event.h)
and checks target-observation permission in
[`filt_procattach`](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_event.c).
Those links are current upstream source, not proof of the installed kernel's
exact source or the behavior of all macOS versions.

On 2026-11-05, a low-load Python/`select.kqueue` diagnostic registered
`NOTE_EXIT | NOTE_EXITSTATUS` before releasing or terminating task-owned
children. On the local Darwin ARM64 Mac and naphtali, benjamin and judah
(macOS 26.7.2, build 25G332), an independent sibling observer running as the
same user obtained data values 0, 1792 and 9 for exit 0, exit 7 and SIGKILL.
Each matched the corresponding parent's `waitpid` result, with the expected
PID/token and flags `0x84000000`. Each test process and observer was reaped;
the strict Tailscale SSH wrappers reported their temporary directories absent.
These are one sample per case and host. Same-user signal permission, exact
kernel behavior, permission refusal for other identities, crash recovery and
full process-tree behavior need independent qualification.

The source now includes an opt-in status-request event and a conservative
raw-status parser. The parser requires exactly one accepted exit event, the
status flag, matching PID/token, a zero high data word and a 16-bit raw value;
stopped-status encoding returns unknown. It does not issue kqueue syscalls or
authenticate its input. It returns a raw status, not an authorization to
release a reservation or evidence that a workload succeeded. Existing
`darwin-proc-watch-event` and WP01/WP02 protocols remain unchanged.

A local signed native selected-source fixture passed the existing event cases
plus 0/1792/9 and refusal cases. A mutant accepting events without the status
flag failed. A separate diagnostic captured the local sibling observer's
event fields, reconstructed 48-byte kevent64-shaped records in Python with
zero extension words, and replayed them through the selected Kotoba parser;
all three statuses passed and an always-zero mutant failed. This was an
offline conversion of Python `select.kevent` fields, not raw `kevent64`
bytes, a native watcher request, or a production host integration. The replay
uses the 25G332 parser profile with observed fields from the local 25D host;
it is not evidence that the local OS is 25G332.
The CLI product test driver was extended with a missing-status mutant and
syntax checked; the full product test was not run for this change.

The native fixtures used the pinned compiler
`920954769b8fdc51cf50dfcab5c44a4e56cf01f261806a153b21488ba81ac4e6`
and diagnostic packager
`df0e94211a35d84901ebcf2a8620cb653140d957732474ff77bd0cdd5b5bf4c5`,
with a 3-second CPU limit but no hard memory cap. The positive unit source
and image hashes were
`cfd2400e20327dec6fd66085a104ac0956569e68984b4ec6047e90da85d008aa` and
`0de5b4cb48fbd721a7aac317de03cf7f0d5a61ee1d84f8e71ddc167792a628fe`.
Archived Python scripts and `events.json` are task-specific evidence with
absolute paths and temporary process IDs, not product or deployment tools.
No inference, model, or persistent service was run. Native watcher protocol,
host-owned identity, termination/reaping, descendant containment, durable
reservation, resource limits and governor qualification remain open.
