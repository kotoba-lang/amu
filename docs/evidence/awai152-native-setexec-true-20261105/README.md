# Fixed native SETEXEC diagnostic

`seed/macos-setexec-true-packager.kotoba` emits an experimental Darwin ARM64
Mach-O that uses the previously observed private spawn attribute to SETEXEC
only `/usr/bin/true`, initially stopped, with 256 MiB active/inactive memory
attributes. It accepts no workload parameters. It does not install its own
sandbox, authenticate its target or host, supervise itself, or handle a
reservation. It is a diagnostic fixture, not an inference launcher. A caller
must resume or reap its task-owned stopped process.

The fixture packager was compiled with the pinned diagnostic compiler
`920954769b8fdc51cf50dfcab5c44a4e56cf01f261806a153b21488ba81ac4e6`
and FS2 packager
`df0e94211a35d84901ebcf2a8620cb653140d957732474ff77bd0cdd5b5bf4c5`.
Packager source SHA-256 was
`4b45c452b3b63bfa722baee6796bb06f66c8f176d7e4f9fa48cbe32ea2390e8d`,
and signed emitted helper SHA-256 was
`49a7b8c80c83730448b6465b06063abf01b4e6c573b0e87114483c2f516afa2b`.
An independent source-operation model matched all 110 emitted instruction
words; LLDB checked their operands and a register mutant was rejected. A
locally built test mutant targeting a nonexistent `/usr/bin/truf` exited 1.
These checks do not establish the full syscall ABI, OS compatibility or host
security. Compiler and observer processes had short CPU caps; the launcher
test did not impose an independently verified whole-host memory cap.

On 2026-11-05 the signed helper was launched under a diagnostic allow-default,
fork-deny sandbox. On a local Mac and, via strict Tailscale SSH, naphtali,
benjamin and judah (ARM64, macOS 26.7.2 build 25G332), the observer saw the
same task-owned PID stopped with `ps` command `/usr/bin/true`. On each target,
a separate root observer read `[256,1,256,1]` from memorystatus while stopped.
The signed WP04 watcher was registered before resume and returned request-bound
status 0, matching the direct child's exit 0. This sampled `ps` command and
readback do not attest immutable executable identity, later memory use or GPU
accounting. No model or persistent service was started.

Benjamin's first target attempt timed out waiting for the stopped process;
its cause was not established. The observer's failure path killed and reaped
its owned process; the named wrapper directory was later independently found
absent. A separate retry and the judah case succeeded with an eight-second
stop deadline. Completed wrappers reported their task directories absent.

A separate test-only Python observer also reserved a synthetic RGQ4 FIFO
ticket, started this native helper under the fork-deny sandbox, waited for
WP04 readiness and a heartbeat while the target was stopped, then resumed it.
On the local Mac and all three targets, the status-0 frame matched the reaped
direct child; the FIFO hold remained until the fixture explicitly released,
dequeued and settled it. That observer does not constitute a native
supervisor, and the FIFO does not verify the status or entire process tree.

The scripts in this directory use task-specific paths and external pinned
artifacts. The sandbox is allow-default, Darwin SETEXEC/memory ABI is private,
and process identity, fork/IPC escape, launch ownership, safe memory
enforcement, watcher failure, durable reservation and crash recovery remain
unqualified. This fixture does not run Kapitsa, an Itonami bot or GitHub
state, and does not qualify or authorize a resource governor.
