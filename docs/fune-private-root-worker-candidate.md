# Fixed-source private-root worker candidate (JUN-779)

`fune-worker-build aarch64-linux HOST OUTPUT` builds exactly the pinned
`seed/fune/private-root-worker.kotoba` with the Amu native ARM64 backend. The
factory rejects changed host source and existing output paths. It is not a
general facility for arbitrary guest source to access runtime intrinsics.

The current worker accepts **no OCI archives and executes no workload**. After
setup it prints `fune-private-root-ready` and accepts bounded file commands or
`X` to exit. It initially creates directories as 0700 and files as 0600; a
separate finalization command can apply bounded image modes after writes.
The parent starts a child and supplies a single-ID user/group mapping through
proc after a pipe handshake. The child installs a parent-death signal and
checks its parent, enters user, mount and network namespaces, makes mount
propagation private, and mounts a 4 MiB, 4096-inode, `nosuid,nodev` tmpfs over
its own `/tmp`. It creates `/tmp/rootfs` there, marks itself non-dumpable and
sets `no_new_privs`. Extra inherited FDs are closed before the child is made.
The worker exits on failed setup rather than falling back to host staging.
The mount is held only by the child namespace; no named host tree is published.

The binary protocol uses an operation byte `M`, `F`, `U`, `R`, `P`, or `V`, then a
big-endian 16-bit path length, big-endian 32-bit byte count, and path bytes.
`M` creates a directory and requires count zero; `F` creates a new file;
`U` truncates and replaces an existing file; `R` reads the requested prefix.
`F`/`U` are followed by count data bytes. `M`/`F`/`U` write `K` after the
operation. `R` writes `K` before returning the requested bytes; it can still
fail partway through, so `K` is not a successful-read verdict and the caller
must receive every byte. There is no separate final read acknowledgment.
`C` carries a two-byte big-endian operation count; when that count matches the
worker's completed commands, the worker writes `D` and refuses further writes.
Before `C`, `P` uses the count field as a mode from 0000 to 0777 and applies it
to an existing inode. The first `P` begins finalization and rejects all later
file writes; further `P` commands are allowed. The controller is responsible
for applying children before their parents and for sending the complete set.
The worker does not attest that a producer sent every image path: an omitted
`P` is not detectable from the count alone, so producer trust is still required.
For a runnable diagnostic stream, `T` replaces `C` after finalization: it
carries a two-byte command count, a four-byte spec length and `FPS` plus
version-byte `1` process bytes. Before `D`, the worker bounds and validates
framing, absolute paths and NUL exclusion. It resolves cwd and executable
beneath the private root with `openat2`, rejects symlinks, and uses `fstat` to
require a directory cwd and a regular executable with an execute bit. It keeps
the checked `O_PATH` descriptors until worker exit; `/` reuses the root FD.

One diagnostic read is allowed after the terminal frame. `Q` returns the staged
spec; `V` returns an inode mode; `I` checks that both retained process FDs still
support `fstat`. The worker does not validate environment-name syntax,
duplicates, UTF-8, interpreter availability or actual UID/GID access. Retaining
an FD does not make file bytes immutable or authorize execution; a future
executor must bind and revalidate its own target and policy. `X` exits even
before the terminal frame; a supervisor must require `D` for success.
Neither `C` nor `T` publishes or persists the tree. Paths are at most 255
printable ASCII bytes with no empty, dot, dot-dot or whiteout components;
file operations are at most 1 MiB each. A session admits at most 512 ordinary
commands and 128 finalization commands before `C` or `T`, plus one optional
diagnostic read afterward. The candidate supervisor accepts up to 640 acknowledgments,
matching this worker range.
Directory and file access is rooted at the private root directory descriptor.
Intermediate directory and final file opens use `openat2` with
`RESOLVE_BENEATH`, `RESOLVE_NO_SYMLINKS` and `RESOLVE_NO_MAGICLINKS`;
unsupported `openat2`, invalid input and I/O errors terminate the worker and
discard the private mount, with no fallback. Directories must already exist
before their children. A failed update can leave partial data in the temporary
tree until process exit; it must never be published. This is a diagnostic
protocol, not an OCI layer admission or transactional rootfs interface.

For a string-only producer, a literal `H` as the first input byte selects an
ASCII-hex transport: every subsequent protocol byte, including `X`, is sent
as two lowercase hex digits. The worker decodes in bounded chunks; responses
are unchanged. Invalid or truncated hex terminates the worker. This transport
does not authenticate the producer or validate OCI metadata.

The parent sets itself dumpable to permit proc mapping on some Linux systems
and remains dumpable for its lifetime. This candidate does not establish a
security boundary against a hostile process with the same host principal.
It also does not create a PID namespace, close
all possible race windows, apply a worker seccomp policy, enforce cgroups,
handle multiple layers or implement persistence/recovery. The temporary tmpfs
limit and protocol are diagnostic, not the final image/storage contract.
Never use this worker as a container launcher or an admission decision.

## Local native ARM64 observations

On the task's Fedora 6.15.10 ARM64 VM, a compiler rebuilt from the candidate
sources built and ran this exact pinned worker. `check-fune-private-root.py`
observed the private `/tmp` tmpfs and its `nosuid,nodev`, 4 MiB and inode
limits in the child's mountinfo, with the mount ID absent from the observer's
namespace. It checked `no_new_privs`, refusal of access via `/proc/PID/root`,
closure of an inherited sentinel FD, graceful `X`, refusal of `Z`, and child
death after the parent was killed. It did not independently observe the user
or network namespace identities because proc access was denied. A modified
worker source was rejected by the factory. Root execution refused; a separate
disposable container with an explicit seccomp rule returning EPERM for
`unshare` also refused before readiness. The test-only seccomp profile allowed
other syscalls and is not a production sandbox.
The updated worker also created, read and replaced binary files, including a
16,643-byte nested file and a file at the 1 MiB operation limit across
multiple 4 KiB chunks; it rejected absolute,
parent/dot/empty-component and whiteout paths, missing parents, duplicate
creates, missing replacement targets, overlong payloads, truncated headers
and truncated payloads. The observer checked that the outer `/tmp/rootfs`
entry was unchanged. In a disposable container the same nested create passed
with `openat2` permitted and refused before acknowledgment when a test-only
seccomp rule denied it. A separately built mutant that removed exclusive
creation accepted the duplicate and failed its negative control. These checks
do not establish an adversarial same-principal boundary, OCI validation,
cross-process controller authentication, or a secure launcher.
Hex transport round-tripped 10,242 bytes containing every byte value, and
rejected odd-length and malformed hex while preserving the binary protocol.
The terminal-count candidate accepted a zero-operation marker, refused a
wrong count, refused a write after the marker, and allowed only one diagnostic
read after it. A separate test worker with the count comparison disabled
incorrectly accepted a wrong count and failed the supervisor observation.
In another test-only worker with an injected in-root symlink, updating through
the symlink was refused. A separate mutant disabling both the no-symlink
resolution rule and the final no-follow flag accepted that update and failed
the control. The normal worker itself provides no command to create links.
In a disposable container, an independent outer-directory check passed with
the normal worker and failed when a source-pinned test mutant skipped the
tmpfs mount; this checks detection of that particular missing boundary.

The native check requires an ARM64 Linux host on which unprivileged user,
mount and network namespaces are available. It does not use an external shell
or container runtime as the implementation:

```sh
python3 scripts/seed/check-fune-private-root.py \
  --compiler /path/to/candidate-amu \
  --output /path/to/new-task-owned-output
```

The candidate branch regenerates its bootstrap pins for this factory. Native
x86 worker support, exact-head CI, security review, OCI verification/extraction,
lifecycle and release are still open.

## Final mode candidate

The regenerated ARM64 Linux compiler built the fixed-source worker and refused
an altered worker source. On the rootless Fedora ARM64 VM the observer checked
actual `fstat` modes, including 0000, 0751 and 0777, after the bounded `P`
phase; it also checked post-finalization write refusal, special mode refusal,
512 ordinary plus 128 finalization commands, and rejection of a 129th `P`.
The source-composed layout producer passed file-content and mode readback,
repeated-directory and 1 MiB fixtures with this worker. A chmod-disabled
control built with a patched debug-only compiler failed the mode readback.
These observations do not authorize workload execution, verify arbitrary
producer completeness, qualify x86 or establish release readiness.

## Process specification handoff candidate

The regenerated source-pinned ARM64 compiler built the worker and refused
altered source. Local tests observed raw and hex handoff, empty arguments, UTF-8
environment bytes, maximum item counts, 9 KiB and 65,536-byte payloads,
malformed framing/path/NUL and size/count refusals, and a single-read limit.
A debug-built mutant that ignored spec validation accepted malformed magic.
The runnable OCI producer round-tripped config-derived specs through the
worker; the supervisor refused invalid specs. This is not workload execution,
complete process validation or runtime admission.

## Private inode target check candidate

The regenerated source-pinned ARM64 compiler built this worker and rejected
altered source. After finalization, the worker accepted valid private targets
and refused missing, directory-as-executable, no-execute-bit, missing cwd and
file-as-cwd cases. A separately built debug target-check-removal mutant
accepted a non-executable file. Matching source-composed runnable streams
still passed readback/refusal fixtures. This is diagnostic, not permission to
execute; other target hosts and runtime qualification remain open.

## Read-only runnable tmpfs candidate

For `T` only, after validating the process targets and before returning `D`,
the worker remounts its entire private `/tmp` tmpfs read-only with `nosuid`
and `nodev`, then requires `fstatfs` on the held root FD to report tmpfs and
all three flags. Failure terminates the worker without `D`. The pre-existing
root and target descriptors remain on that same mount; a self-bind of only
`rootfs` is insufficient because descriptors held from the original mount
would still have writable access. `C` remains a diagnostic-only logical freeze
and does not perform this remount.

After `T`, the single-use `W` diagnostic attempts a create via the original
root FD and returns `K` only for `EROFS`; it does not authorize execution.
A caller-selected file with the probe's fixed name can cause this optional
check to refuse. On the local ARM64 Linux host, the observer checked the
worker's mountinfo independently and saw `ro,nosuid,nodev`, and `W` observed
`EROFS`. In debug-built controls, skipping the remount was refused before
`D`, bypassing the entire freeze was caught by the write probe, and denying
only the remount syscall caused refusal before `D`. These observations do
not establish immutability against an actor retaining mount authority, a
hostile same-principal process, or any workload isolation. A future launcher
must drop the relevant authority and qualify its own confinement.

## Runnable worker capability-drop candidate

After the `T` read-only remount and before `D`, the worker drops its
capability bounding set, clears ambient capabilities, clears effective,
permitted and inheritable capabilities, and checks every kernel-supported
capability reported by `/proc/sys/kernel/cap_last_cap` plus `no_new_privs`.
The range must come from procfs and be representable by the v3 capability ABI;
missing, invalid or unsupported information fails closed. An error refuses
without `D`; `C` remains unchanged. The single-use `J` diagnostic attempts
to remount the tmpfs read-write and
returns `K` only when that attempt fails with `EPERM`.

On the local ARM64 Linux host, an outside observer saw all five capability
sets become zero while `no_new_privs` remained set, and `J` observed
`EPERM`. A test-only seccomp filter denying `capset` caused refusal before
`D`. Debug-built controls that skipped `capset` or bypassed the whole drop
were detected. These checks apply to this worker, not to a future executor:
without its own namespace, syscall and lifecycle policy a program may create
new user namespaces or acquire other authority. They do not establish
isolation from a hostile process with the same host principal.
A separate disposable namespace probe on the same host created a new user
namespace after capability sets were cleared and `no_new_privs` was set; the
child gained capabilities in that new namespace. Consequently the capability
drop alone must not be treated as preventing namespace-based reacquisition.

## Runnable worker namespace-filter candidate

After dropping capabilities and before `D`, the worker installs a narrow
ARM64 seccomp filter and checks that filter mode is active. It rejects
`unshare`, `setns`, and namespace flags on legacy `clone`. It returns `ENOSYS`
for `clone3` so software can fall back to legacy `clone`; ordinary legacy
clone remains allowed. The filter kills a process using a different syscall
architecture. If installation or verification fails, the worker refuses
before `D`. The single-use `N` diagnostic checks those namespace operations
and verifies ordinary clone/wait still works.

A local ARM64 Linux observer saw the filter count increase and `N` passed.
A test-only filter denying the installation syscall prevented `D`.
Separately built debug controls that bypassed the filter, removed the user
namespace clone mask, allowed clone3, or used the wrong architecture were
caught. The filter is inherited by descendant processes, but it covers only
these specific namespace syscalls; it is not a full seccomp sandbox, a PID
namespace, a cgroup controller, or authorization to execute an OCI image.
The actual workload and host escape boundaries remain unqualified.
The filter's syscall numbers and namespace flag mask follow the Linux
[generic syscall table](https://github.com/torvalds/linux/blob/master/include/uapi/asm-generic/unistd.h)
and [clone flag definitions](https://github.com/torvalds/linux/blob/master/include/uapi/linux/sched.h).
