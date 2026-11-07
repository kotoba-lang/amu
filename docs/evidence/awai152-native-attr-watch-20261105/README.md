# Native-built spawn attributes with the sandbox/watcher diagnostic

On 2026-11-05, the current `darwin-spawn-attribute.kotoba` was composed with
the existing attribute-emitter fixture and compiled with a pinned Darwin
diagnostic compiler. The emitter generated 248-byte SETEXEC+START_SUSPENDED
attributes with 64 MiB and 256 MiB active/inactive settings. An independent
byte construction matched each output. This compiles the attribute builder;
it does not compile the Python launcher, sandbox, supervisor or whole Amu
product. The compiler SHA-256 was
`920954769b8fdc51cf50dfcab5c44a4e56cf01f261806a153b21488ba81ac4e6`
and diagnostic packager SHA-256
`df0e94211a35d84901ebcf2a8620cb653140d957732474ff77bd0cdd5b5bf4c5`.
The 64/256 attribute hashes were
`7fb2b3c5cdbff57bdb0945850a4271f5e792903619475dc24a1b81c844b07861` and
`04adb7b2105f6671a0b95a3d48f21a1abd5ce8a0df14b333d3767d8e9eacd4ac`.

Using the prior task-only Python/ctypes sandbox and watcher diagnostic, the
256 MiB bytes were supplied to the private Darwin spawn syscall. On naphtali,
benjamin and judah (ARM64, macOS 26.7.2, build 25G332), an independent root
observer read active/inactive limit and attributes as `[256,1,256,1]` while
the target was stopped after SETEXEC. After watcher readiness and first
resume, the target stopped itself; the observer read the same four values,
then resumed it. Fork and spawn returned EPERM, relink returned EPERM and
exec of the removed launch path returned ENOENT. The direct child exited 0,
and the watcher returned its exact bound exit frame.

A separate memory workload allocated and touched up to 96 MiB on each host.
With the native-built 64 MiB attribute, both stopped readbacks were
`[64,1,64,1]`, and the direct child received SIGKILL after printing 48 MiB.
With 256 MiB, both readbacks were `[256,1,256,1]` and the same workload
completed 96 MiB and exited 0. The watcher returned its successful bound exit
frame in **both** cases: a bound exit frame is not a successful workload
result and the supervisor must separately obtain and validate termination
status. The kernel kill reason was not collected; the 64 MiB attribution is
consistent with the observed settings and control but is not independently
proven. Each run was a single bounded sample, not an exhaustive enforcement
test. No model, GPU allocation or persistent service was run.

An initial post-resume test used signal number 19 rather than Darwin's
`SIGSTOP`, so the child completed before the observer's second stop. That
attempt was rejected; the corrected test used `signal.SIGSTOP` and passed.
Task-owned direct children and watchers were reaped in completed tests and
completed SSH wrappers reported their temporary directories absent. The
scripts and 248-byte evidence artifacts here are diagnostic records with
task-local paths and external tool pins, not operational setup commands.

The tests use root only for the short independent memorystatus readback; the
task is a Python/ctypes launcher and uses a private Darwin ABI and an
allow-default sandbox. The path and peer identity are not fully authenticated,
and no atomic PID handle, process-tree or IPC containment, durable resource
reservation, crash recovery, GPU/unified-memory cap, real Kapitsa startup or
bot/GitHub turn was established. The observed memory limits do not qualify the
native resource governor or authorize deployment.
