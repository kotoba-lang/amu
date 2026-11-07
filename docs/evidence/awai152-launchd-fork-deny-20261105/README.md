# System launchd and fork-deny diagnostic

On 2026-11-05, strict Tailscale SSH and `sudo -n` on naphtali, benjamin and
judah were used to bootstrap uniquely named short-lived system launchd jobs.
Each job's `UserName` was the corresponding logged-in account (observed UID
501, GID 20), not root. The root observer prepared and removed only its own
temporary job and files. Each target reported Darwin ARM64, macOS 26.7.2,
build `25G332`.

With `/usr/bin/sandbox-exec` and `(version 1) (allow default) (deny
process-fork)`, a diagnostic Python process reported that a thread ran but
`fork` and `posix_spawn` returned EPERM. A separate allow-default control on
each host reported successful fork, successful spawn and a working thread.
Each job was stopped using its exact launchd label; the reported job PID was
not observed after bootout. An independent subsequent system-domain listing
found no diagnostic sandbox labels and no recorded parent PIDs. Temporary
wrapper directories were reported absent. The observer checks UID/GID from
inside the process and UID through `ps`; those samples do not independently
attest all process credentials or future executions.

In a separate job, the same launchd user and fork-deny profile executed the
installed Kapitsa `serve --help` without loading a model or starting a server.
The binary's SHA-256 was checked against
`20db8dadcb79de820d237367ca93d7ac66f8a70d91d5513f6e1ab77253925daa`
and its code signature was verified before each run. On each host launchd
reported exit 0; captured help contained `--private` and `--local`. Each
task-only job was booted out, the wrapper directory was reported absent, and
a subsequent system listing found no matching diagnostic labels. This checks
one help invocation, not runtime executable identity against replacement,
the serving path, actual inference, memory, or any network listener.

The first two naphtali Python-job attempts registered the job but failed
before the workload ran with launchd exit 78. After moving stdout/stderr to
the intended user's writable test directory, the corrected test passed. The
first help attempt incorrectly treated `last exit code = (never exited)` as a
completed result; it booted out its task-only job and was repeated with a
completion wait. The cause of the earlier exit 78 is not independently proven.

The restricted, control and help operator hashes were respectively
`c21084252e2ba240d874a8ca30c40dd018921bc6ae4402cf1c560a39a71d45d2`,
`00c872a9b82b4d6211415de1095eff05f5a326fdbe6d35497593f1ed4447d318`, and
`e855ac8dbe1879f62082ab3c5a83468b967c660633b702e183bf045727858e74`.
The remaining files are task-specific SSH/list wrappers with absolute local
paths. CPU limits and fallback lifetimes were used for the Python diagnostic;
no hard memory cap was imposed. The Kapitsa help job was bounded by the
observer's deadline but was not given an independently verified CPU or memory
limit.

The allow-default profile is not a complete sandbox: it does not establish
protection from exec, IPC, network access, external services starting work,
file changes or every process creation path. `sandbox-exec` and Python are
diagnostic instruments, not a native product supervisor. The launcher's exec
is also incompatible with the current watcher's strict exec refusal in the
previous experiment. A trusted bootstrap, process identity and lifetime,
crash-safe reservations, authenticated transport, GPU/unified-memory control,
actual Kapitsa serving and model inference still require qualification. None
of these observations authorizes deploying a workload.
