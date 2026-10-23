# Wire 20 :process/spawn through the spawn helper

Linear JUN-292. Status: measured and passing.

Host: arm64 Linux (6.15), a podman machine (applehv) on macOS arm64. The
x86_64 rows ran under qemu-user binfmt with `KEXE_SECCOMP=if-available`,
because qemu-user has no seccomp. No C compiler or loader was used. Paths
under a gate's output directory are written as `OUT`.

## The re-pin

The spawn helper in `seed/76` and `seed/77` changes the runtime text embedded
in every static image. The static root was re-pinned C-free, from
`b2f96378dbf9` (the native TCP root, `../net-runtime-20261022/`) to
`48994a9dbf64`.

`selfhost-bootstrap.json` records the result:
- root = S1 = S2 = S3;
- adopted G1 = G2 = G3;
- all 24 cases pass.

The adopted closure does not include the runtime, so the adopted image is
unchanged. No other receipt was re-measured.

## Files

| file | result |
| --- | --- |
| `aarch64-linux.json` | `scripts/seed/check-spawn-runtime.py`, native, seccomp enforced: 18 grant cases and 21 wire cases (below) |
| `x86_64-linux.json` | the same gate under qemu-user: 18 grant cases and 20 wire cases; the control is `notCovered` |
| `net-runtime-*-linux.json` | wires 43..47 on the new root: 29 wire cases on aarch64, 27 on x86_64 |
| `selfhost-bootstrap.json` | `scripts/seed/selfhost-bootstrap.py` on the re-pinned root |

The 21 wire cases on aarch64:
- answers: arguments, an exit code, and `-1` for a signal;
- the child's surroundings:
  - stdin at end of file;
  - only the granted variables;
  - only fds 0..2 open;
  - `NoNewPrivs: 1`;
  - `ulimit -v` unlimited, so the image's 64 MiB limit does not reach the
    child;
  - the scope-35 root as its working directory;
- lookup by name;
- the refusals, each exiting 126: `program-not-granted` (three ways),
  `path-lookup-denied`, `argv-budget` (by count and by bytes),
  `output-budget`, `timeout` and `exec-failed`;
- plain traps: an empty program, a request over 65536 bytes, a wire that is
  not granted;
- a control compiler whose filter has no read rule for the helper's answer
  fd. It dies of SIGSYS, which shows the guest itself stays sandboxed.

## Not covered

- No case makes `close_range`, `prctl`, `dup3` or `fchdir` fail in the child.
  `spawn/isolation-unavailable` and `spawn/setup-failed` are therefore not
  driven by any case.
- The helper is not sandboxed. It runs the granted programs as ordinary
  processes with the host's uid, as the catalog's `:child` states. What keeps
  the guest from widening it is the helper's own copy of the grant, taken
  before the guest runs.
