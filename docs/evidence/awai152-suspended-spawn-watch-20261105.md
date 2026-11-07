# Suspended spawn and the experimental Darwin watcher

On 2026-11-05 JST, a low-load local diagnostic on Darwin ARM64, macOS
26.3.1 (a), build `25D771280a`, tested whether the existing watcher can be
registered before a task-owned child is resumed. Python 3.14.5 used libc's
`posix_spawn` with `POSIX_SPAWN_START_SUSPENDED` (`0x0080`) and
`POSIX_SPAWN_CLOEXEC_DEFAULT` (`0x4000`), as declared by the installed
Darwin SDK. This is diagnostic host orchestration, not the native product
supervisor or a resource governor.

The observer checked the watcher's SHA-256 and strict code signature, staged
its own copy, created its own short-lived children, observed each child in a
stopped state with `waitpid`, and required the exact request-bound WP01 ready
frame while the watcher was alive before sending SIGCONT. It then required
the expected response and independently waited for each direct child.
Each process inherited a 3/4-second soft/hard CPU limit. Temporary files
were removed and children reaped. No model or persistent service was started.

| Child | Observed after resume |
| --- | --- |
| `/bin/sleep 0.2` | Watcher returned the matching exit frame with status 0. |
| `/bin/sh` writing a private marker | Marker was absent before ready and contained `ready` afterward; watcher refused with status 1 and no exit frame. |
| `/bin/sh` writing a marker and spawning `sleep` | Marker was absent before ready and present afterward; watcher refused with status 1 and no exit frame. |

An earlier attempt assumed the marker-only shell would be accepted; the
watcher refused it, so that assumption was removed. A separate kqueue
diagnostic registered the same event types on separately spawned suspended
children and observed EXIT only for `/bin/sleep`, EXEC then EXIT for a
marker-free shell, and EXEC, FORK, EXIT for a shell that started a child.
This is consistent with the watcher refusing the shell's EXEC event; the
watcher does not report the specific refusal cause, and the two observations
were separate runs. The event may be a legitimate part of starting the shell;
do not simply ignore EXEC, since later exec transitions also matter.

`scripts/seed/observe-macos-suspended-watch.py` SHA-256:
`7c801f6b891f34580e8807d95a93f338c8d246fcc5cdfc62d53bcef37e447090`.
`scripts/seed/observe-macos-suspended-kqueue.py` SHA-256:
`31338a1a28adb969e8105daf8288130f9556b74185d68f59249ee0c555d81214`.
The imported existing helper SHA-256 was
`eadae9fd7485780fe30fc0cd7bfd877dadac3ea0f54309dff3e3f174317e3f03`.
The signed experimental watcher, from Actions run
[41793197780](https://github.com/kotoba-lang/amu/actions/runs/41793197780),
had SHA-256 `0c7d6496a9b25ca9781152e6046751d259ee67433d87e92fb7d3ce5b04ff6dbf`.
A mismatching watcher hash was refused before child creation.

This demonstrates a possible registration ordering for these two observed
programs, not a proof that arbitrary code cannot run before observation, an
authenticated initial-exec transition, process-tree containment, workload
termination, GPU/CPU/memory enforcement, durable reservation recovery, or
governor qualification. It has not been tested on the target Mac minis or
integrated with the actual host launcher or FIFO. The CPU limit does not bound
memory or establish that descendants are contained.

## Direct Bash and three target Macs

The observer was extended with three `/bin/bash` cases: writing a private
marker, writing a marker then forking a child, and writing a marker then
executing `/bin/sleep`. On the same local Mac, direct Bash marker-only
completed with a watcher exit frame; its fork and exec cases were refused.
Each marker was absent before watcher readiness and present after resume. The
`/bin/sh` cases above continued to refuse. Separately inspecting `/bin/sh` on
the local Mac found strings referencing `/bin/bash`, `/bin/zsh` and an exec
failure; this is consistent with a wrapper transition but does not identify
the exact event that caused the watcher's refusal.

On 2026-11-05 JST, the updated observer, kqueue diagnostic, existing helper
and the same signed watcher were copied to task-owned temporary directories
on naphtali, benjamin and judah over Tailscale SSH. Each connection used
strict host-key checking against that peer's advertised SSH host keys; the
remote scripts checked transferred SHA-256 values and the watcher checked its
signature. All three hosts reported Darwin ARM64, macOS 26.7.2, build
`25G332`. On each host:

* The kqueue diagnostic observed EXIT for direct sleep, EXEC then EXIT for
  `/bin/sh`, and EXEC, FORK, EXIT for the shell fork case.
* The watcher accepted direct sleep and direct Bash marker-only exits, while
  refusing the `/bin/sh` marker and fork cases and direct Bash fork and exec
  cases. The markers were absent before readiness and present after resume.
* The direct children were reaped and each remote temporary directory was
  confirmed absent. No model or persistent service was started.

The updated observer SHA-256 is
`c8b74d4c81bcb99c6abea6e555e1b226e27fb1e137f04ff0540e645299bd02a8`;
the archived task-specific orchestration script
`awai152-suspended-spawn-three-macs-20261105.py` has SHA-256
`6b2e22ff9dc4c19ddfaf20bccaa247c3e1afe6ef8d4b8f837914e3e35a40c65d`.
It contains local artifact paths and host names and is evidence of this run,
not an unattended deployment command.

Directly selecting a known executable avoided the observed shell-wrapper
transition in these tests; it is not a general executable identity or launch
policy. The watcher observes and refuses transitions after they occur and
cannot prevent the child or a descendant from already performing side effects.
It does not establish tree containment, resource limits, durable recovery,
an authenticated supervisor, model compatibility or governor qualification.

## Combining the sandbox diagnostic with suspended spawn

On 2026-11-05 JST, the same observer was extended with two short-lived
`/usr/bin/sandbox-exec` cases using `(version 1) (allow default) (deny
process-fork)`. Each process was spawned suspended, its WP01 watcher ready
frame was checked, and only then was it resumed. In one case the target Bash
wrote a private marker; in the other, the target Python attempted `fork` and
`posix_spawn` and wrote `ready` only if both returned `EPERM`. Both markers
were absent before readiness and read back as `ready` after the child exited.
The watcher returned status 1 without a final exit frame in both cases.

The same cases passed on the local Mac and on naphtali, benjamin and judah
using the same strict Tailscale SSH and digest/signature checks described
above. Each test-owned direct child was reaped and each remote temporary
directory was confirmed absent. The watcher reports no reason for refusal;
these observations do not by themselves prove that its refusal was caused by
the sandbox launcher's exec. They do show that the marker was written despite
the watcher refusing: this diagnostic observer waited for the child and did
not terminate it when the watcher refused. A production host cannot treat a
watcher failure alone as proof that the workload stopped or had no effects.

The observer script SHA-256 for this run was
`abf44aa6d69b02eacece24a79c08398b4ab0b7b16272c20a4d7b7e731436d7d1`;
the unchanged three-Mac orchestration script hash is recorded above. The
Python, sandbox-exec and allow-default policy are diagnostics, not a native
implementation, a comprehensive process-creation restriction, an I/O or
GPU/memory limit, an authenticated supervisor, or governor qualification.
No model, real workload or persistent service ran.
