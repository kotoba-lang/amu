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
