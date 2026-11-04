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
