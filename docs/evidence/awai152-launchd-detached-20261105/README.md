# launchd stopped-job descendant diagnostic

On 2026-11-05 JST, a diagnostic on one local Darwin ARM64 Mac, macOS
26.3.1 (a), build `25D771280a`, created a uniquely named task-only user
launchd job. The job's Python parent forked two short-lived children; the
second successfully called `setsid`, and the observer verified that its
session and process-group IDs matched its own PID. The plist specified
`AbandonProcessGroup=false` and `RunAtLoad=true`. All processes had short CPU
limits and each test process had a 15-second fallback lifetime; this did not
impose a hard memory limit.

In each of two runs, `launchctl bootstrap` and `bootout` returned zero. After
bootout, the direct parent and the same-group child were no longer observed;
the separate-session child remained live and was reparented to PID 1. The
task-only cleanup compared the recorded PID start time before killing that
child. Independent subsequent `ps` checks did not show the three PIDs, and
the temporary job label was not listed. The second run explicitly checked
the detached child's session and group identity before bootout. No model,
existing service, or other process was intentionally stopped.

The exact task-specific observer is `probe.py`, SHA-256
`00c9b480b5168daaab9e5f12728c163dab25e0f8f94bab738f9a5b6242598200`.
Python and shell are diagnostic tools, not an operational supervisor. A
`launchctl print` failure is not by itself proof of a nonexistent service;
the successful bootout, process observations, and later label listing are
separate observations. Cleanup's PID/start-time check is not an atomic
process handle and is not a production termination mechanism.

This is a counterexample to assuming launchd bootout alone terminates every
descendant. It does not establish behavior on the three target minis, for all
launchd configurations, or under power loss. It does not test a fork-denied
sandbox, PID reuse races, GPU memory, resource enforcement, reservation
recovery, actual Kapitsa, an authenticated native supervisor or the governor.
In particular a job's disappearance is not sufficient evidence for releasing
its workload reservation.

## Three target hosts: bootstrap did not succeed

The same task-only GUI-domain diagnostic was attempted over strict Tailscale
SSH on naphtali, benjamin and judah, each reporting Darwin ARM64 macOS 26.7.2
build `25G332`. All three `launchctl bootstrap gui/501` calls returned 125,
`Domain does not support specified action`; the workload did not reach its
PID files. A variant targeting `user/501` instead returned 5, `Input/output
error`, on each. These outcomes do not establish the underlying cause and are
not target-host descendant tests. The observer prints a cleanup success line
even with an empty PID set; that line is vacuous in these failed bootstraps.

An independent follow-up listed `user/501` on each host successfully and
found no label with the task prefix. `launchctl print gui/501` returned 125
on each, so absence from that GUI domain could not be independently listed.
Remote wrappers reported their task-owned temporary directories absent. These
are limited post-attempt observations, not a general launchd cleanup proof.
No inference or persistent service was intentionally started.

`three-hosts.py`, `user-domain-probe.py`, `user-three-hosts.py` and
`list-hosts.py` are archived task-specific operators. They contain local paths
and rely on current Tailscale host keys, SSH access and the diagnostic Python
environment; they are not unattended setup commands. The first wrapper's
`VERIFIED False` and the captured nonzero probe codes are expected records of
failure, not successful launch evidence. A supported remote launch and
supervision boundary remains to be designed and qualified.
