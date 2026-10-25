# Native private-store provider

JUN-299 / JUN-360. Candidate in the two loaderless Linux runtimes, seeds
76 and 77. Existing wire-35 text forms keep their behavior. This adds a
bounded byte frame for a trusted signer host; app/LLM/browser scopes must
never include the signer's private directory.

The frame is `NUL KPV1 NUL OP PATH [NUL VALUE [NUL SUFFIX]]` on wire 35
with `:bytes` request/response. `OP` is one ASCII byte:

| Operation | Request | Successful response |
| --- | --- | --- |
| R | `R PATH` | byte 1 followed by the file bytes |
| C | `C PATH NUL VALUE` | byte 1 after exclusive create, write, file fsync and parent fsync |
| A | `A PATH NUL EXPECTED NUL SUFFIX` | byte 1 after locked comparison, append and file fsync |

Refusal is one byte 0. Fields cannot contain NUL. The normalized path is
beneath an explicitly granted wire-35 root. The immediate parent must be
owned by the effective UID with exact mode 0700. `openat2` uses
`RESOLVE_BENEATH | RESOLVE_NO_MAGICLINKS | RESOLVE_NO_SYMLINKS` and no-follow
opens. Files must be regular, owned by the effective UID, mode 0600, with
one link. Metadata is checked again after acquiring a nonblocking flock.
The read/expected/result file budget is 1 MiB. Unknown operations, malformed
frames, public modes, symlinks, hardlinks and out-of-scope paths refuse.

C uses `O_CREAT | O_EXCL`; existing files are never truncated. It does not
chmod or adopt an existing key. A holds an exclusive flock on the same FD
through compare, append and fsync; readers use a shared flock. A concurrent
writer loses the comparison or lock and receives refusal. No guest-supplied
boolean substitutes for the kernel checks.

An interrupted create/append can leave a partial file. The caller must
validate the entire journal and fail closed, publish configuration only
after initialization completes, and return no signature until commit
succeeds. This interface does not repair, truncate or roll back a journal.
Resolve a lost reply from the verified audit before signing again.

The trust boundary includes the host administrator and filesystem. These
checks do not provide hardware custody, secure erasure, constant-time
signing or resistance to an administrator restoring an older disk image.
Fsync acknowledgements and process-restart checks are distinct from a
physical power-loss experiment. No WASM/browser provider or old vault
compatibility is introduced.

## Native gates

Use a fresh output directory and an explicitly verified Amu selfhost
compiler. The Python files orchestrate native processes and hash receipts;
they are not a qualified native CDCI controller.

```sh
python3 scripts/seed/check-private-store.py --compiler /verified/native-root \
  --output /new/task-output/private-store
```

The 19 cases include exclusive creation, readback, compare/append/fsync,
refusals and eight concurrent writers with exactly one success. A separate
native x86 probe can be checked with `--probe`; this records cross-compilation
separately from native execution.

`seed/tests/clock-sleep-resume/probe.kotoba` and
`scripts/seed/check-sleep-resume.py` cover SIGSTOP/SIGCONT while sleeping.
Linux restarts `clock_nanosleep` through `restart_syscall`; seccomp admits
that syscall only with wire 7 granted. The prior runtime is a negative
control: it terminates with SIGSYS, whereas the candidate resumes normally.
Without this rule, pausing an otherwise valid long-running watcher kills
it on resumption.

Compiler fixed points, the adopted core route, runtime boundary refusals,
24 runtime cases and the private-store/sleep gates are recorded separately.
A source candidate and a locally built root do not replace the admitted
bootstrap root or complete CDCI qualification automatically.
