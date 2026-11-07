# Darwin process-fork sandbox diagnostic

On 2026-11-04 a small diagnostic on jacob (arm64, build `25D771280a`)
and the three target Macs naphtali, benjamin and judah (arm64, build
`25G332`) applied `(version 1) (allow default) (deny process-fork)` using
`/usr/bin/sandbox-exec` to a short-lived Python fixture. The fixture's SHA-256
was `c9ad3004ed72ae01513e2722dca655302864b14685076a6cccdaae8b0d409cfb`.
With no profile, its owned fork and `posix_spawn` children exited normally.
Under the profile, both returned `EPERM`, and a thread completed. A separate
case successfully exec'd a fresh Python interpreter and observed the same
fork/spawn refusals and successful thread there. No workload or inference
server was started. The target fixture was hash-checked in a private temporary
directory, and the harness checked its removal; SSH output was checked for a
complete in-band result because SSH exit status is not trustworthy here.

The Python and sandbox-exec invocation are test instruments, not operational
implementation or a selfhost qualification. This checks selected libc paths,
not all possible process-creation or brokered launch mechanisms. It does not
show that a child cannot ask another service to start work, that Flint can
load or answer under this profile, or that sandbox-exec/profile behavior is a
stable supported production contract. It grants all other sandbox operations,
including network and file access. It does not constrain memory, GPU, CPU or
I/O, bind process identity, prove shutdown on supervisor loss, fence an
external effect, or provide reservation release. Do not use it as a qualified
governor. The next integration test must exercise the actual signed Flint
artifact under a trusted native supervisor, including process creation and
brokered launch attempts, workload lifecycle and resource budgets; any
uncertain or unsupported result must fail closed.
