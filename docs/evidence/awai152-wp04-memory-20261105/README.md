# WP04 with sandboxed memory-limit diagnostic

On 2026-11-05, the experimental signed WP04 watcher was connected to the prior
task-only sandbox/SETEXEC test using the 64 MiB and 256 MiB attributes emitted
from Kotoba source. Strict Tailscale SSH executed the short Python/ctypes
diagnostic on naphtali, benjamin and judah (Darwin ARM64, macOS 26.7.2,
build 25G332). A separate root observer read the active/inactive memory
attributes while the workload was stopped before and after the first resume.

On each host, the 64 MiB case read `[64,1,64,1]` both times and its Python
child printed 48 MiB before SIGKILL. The watcher returned an exact
request-bound `WS01` status 9, matching the parent's child exit. The 256 MiB
case read `[256,1,256,1]`, touched 96 MiB and exited 0, and its exact watcher
frame carried status 0. This confirms the tested watcher distinguishes those
two observed outcomes; the kernel kill reason was not collected, so the
cause of SIGKILL is not independently proven. Memory use was bounded to the
short synthetic workload and no GPU, model or service was started.

Benjamin's first 64 MiB attempt timed out before watcher readiness. The test
observer's failure path killed/reaped its owned child and watcher; an
independent later strict SSH check found that attempt's named wrapper
directory absent. A separate retry succeeded. The timeout's cause was not
established. Completed wrappers on all three reported temporary directories
absent; the recorded watchers and direct children were reaped.

The signed watcher SHA-256 was
`ad32993a07f5e8b3db5d46f695c9d1a2b319974f145f13ebe3406c23810eba6e`.
The 64 and 256 MiB attribute hashes were
`7fb2b3c5cdbff57bdb0945850a4271f5e792903619475dc24a1b81c844b07861` and
`04adb7b2105f6671a0b95a3d48f21a1abd5ce8a0df14b333d3767d8e9eacd4ac`.
The task-specific operators are archived here and require external pinned
artifacts and local paths. The diagnostic launcher and monitor are Python,
the Darwin ABI is private, and the test imposed short CPU limits but no
separate hard whole-host memory cap.

One sample per mode and host does not establish memory enforcement under all
loads, real Kapitsa behavior, GPU/unified memory accounting, process-tree or
IPC containment, safe PID identity, watcher/host crash recovery, durable
reservation or authenticated inference. A status frame is not permission to
release resources. The native governor and end-to-end bot remain unqualified.
