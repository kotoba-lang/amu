# Suspended SETEXEC, sandbox and watcher diagnostic

On 2026-11-05, an operator-only Python/ctypes diagnostic explored the earlier
incompatibility between sandbox-exec's initial exec and the strict WP01
watcher. It first installed a sandbox denying process fork and restricting
process exec to a task-owned hard-link path. It then used a hand-built Darwin
spawn attribute with SETEXEC and START_SUSPENDED to replace itself with the
test Python image. The observer waited for the task-owned PID to stop,
registered the signed experimental watcher and required its exact ready
frame before unlinking the allowed launch path and resuming the process.

On one local Mac and, over strict Tailscale SSH, naphtali, benjamin and judah
(Darwin ARM64, macOS 26.7.2 build 25G332), the resulting child printed its
start and finish markers, reported EPERM for fork, posix_spawn and relinking
the removed path, and ENOENT when it tried to exec that removed path. It
exited 0; the watcher exited 0 and returned the exact request-bound final
frame. The observer reaped the owned direct child and watcher. This sample is
consistent with the initial replacement already being complete when the
watcher is attached; it does not establish that identity or timing for every
launch.

A separate control allowed later exec, resumed the stopped test image, and
executed `/usr/bin/true`. On each of those hosts and locally, the child exited
0 while the watcher returned status 1 without a final frame. The watcher does
not report a refusal reason; this control demonstrates an observed refusal
for that run, not prevention of the later exec or its effects.

In the first fleet run, benjamin timed out waiting for watcher readiness; a
fresh run succeeded. A subsequent judah run timed out at the same wait and a
fresh judah run succeeded. The timeout causes were not established. Failure
paths killed and reaped the owned child/watcher in the probe's `finally`, but
the interrupted wrappers did not produce their completion marker, so their
remote temporary-directory removal is not independently attested by that
marker. Completed wrappers reported their temporary directories absent.
An independent strict SSH follow-up then checked the two named interrupted
wrapper paths on benjamin and judah; both were absent at that later sample.
The initial local probe also failed before watcher launch because the source
image lacked execute permission; subsequent runs used a task-owned signed
copy with mode 0700.

The fleet positive and later-exec control source hashes were respectively
`8b2396856805858e22b0ce76ddaea5daf64af8a205555104700b65f0444bc397` and
`185e7e71925c15aca263f314c6536afcdd63b9ed7c63d16d86c77e094a61cc2f`.
The imported signed watcher SHA-256 was
`0c7d6496a9b25ca9781152e6046751d259ee67433d87e92fb7d3ce5b04ff6dbf`.
Each test process inherited a 3/4-second CPU limit, without a hard memory
limit. The archived scripts are task-specific and reference local paths or
external pinned artifacts; they are not deployment commands.

This is not an Amu-built supervisor. It uses private sandbox and spawn ABI,
an allow-default policy, a manually constructed attribute, a Python worker,
and a path temporarily owned by the same account. It does not authenticate
the target executable, prevent another actor from restoring that path, bind
the observation to a durable reservation, handle PID reuse or supervisor
death, limit GPU/unified memory, or verify Kapitsa serving. The watcher may
refuse only after effects occur. No actual model, inference or persistent
service ran, and the governor remains unqualified.
