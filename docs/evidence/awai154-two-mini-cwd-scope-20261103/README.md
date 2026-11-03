# Diagnostic scoped command on two Mac minis

On 2026-11-03, the same signed `fs2-cli-stdio-cwd` probe from the local ACL
test was copied over Tailscale SSH to isolated task-owned temporary paths on
`levi` and `benjamin` and verified with `codesign --verify --strict`. Both
reported Darwin kernel 25.6.0 and the exact image SHA-256
`3d03943226e74c3bf054e9b2cec025b1a220f4d50af7e3e0ee9333d5e66a55fd`.
The image is a synthetic probe built from candidate source at Amu #1796
`26c32cec`, not an installed runtime or bot service.

Direct execution on **each** host gave the following results:

| Case | Exit | Result |
| --- | --- | --- |
| Owner-owned mode 0700, no ACL | 0 | Read the expected synthetic payload |
| Mode 0755 | 70 | Refused before guest output |
| Mode 0700 with a synthetic allow ACL | 70 | Refused before guest output |
| Parent traversal | signal 5 | Refused without returning outside data |
| Symlink to outside | signal 5 | Refused without returning outside data |

The observer restored permissions and removed its own temporary directories
on both hosts. Every probe was capped at three CPU seconds. No actual bot,
model, production credential or existing service was changed.

Separately, attempts to bootstrap unique temporary jobs from the SSH session
failed on both hosts: `gui/<uid>` returned `Domain does not support specified
action` (125), and `user/<uid>` returned `Input/output error` (5). Their
task-owned temp directories were removed and the attempted job labels were
checked absent. These errors describe this SSH-session attempt only, not every
possible login/session or privileged launchd setup. The outer SSH tool returned
0 despite the remote Python traceback in these attempts, so the structured
case results and stderr, not SSH exit 0 alone, are the evidence of failure.
No launchd-resident execution was established on either mini.

## Follow-up: Background session

Both SSH sessions reported launchctl manager `Background` and `/dev/console`
owned by root. Subsequent **task-only diagnostic** jobs were loaded with
`launchctl load -S Background` and `LimitLoadToSessionType=Background` instead
of the failed `bootstrap gui/<uid>` / `bootstrap user/<uid>` attempts. On each
mini, the same signed probe ran through launchd: private 0700 without ACL
returned 0 and the synthetic content; mode 0755 and a synthetic allow ACL
returned 70 with no guest output. Every test label was unloaded, its absence
checked, and its own temporary directory removed. The ACL was removed.

`launchctl list` exposed 70 as raw wait status 17920. The corrected observer
used `WIFEXITED` / `WEXITSTATUS` and waited for both the matching status and
the expected output file. An earlier observer read initial status 0 before
the process output existed, then expected literal 70 instead of 17920; those
attempts are not counted as passing. Its benjamin job and temp directory were
confirmed removed. The initial levi SSH observer timed out; a subsequent
read-only check found no matching temp directory or Background test job before
the corrected levi test was started.

This shows bounded background launchd execution during an SSH session, not
persistence across SSH disconnect, reboot, automatic installation, bot
operation, MTP or production runner qualification. The `launchctl load`
route is a diagnostic use of the legacy OS command, not a new production
orchestration dependency. The exact test observers are
`background-ben-observer.py` and `background-levi-observer.py`.

The attached Python files are one-off test observers, not production or build
tooling. Their paths, exact host names and Tailscale SSH configuration are
specific to this test. A remote session timeout must be reconciled before any
test is restarted. Full scope identity, parent paths and ACL races, process
isolation, resource governance, authenticated GitHub, and ten-node execution
remain unqualified.

Observer SHA-256: direct
`9f89b4868f7c2fe5a260d116507f63e2934ed3d465bea42e3ed1ee8d22283acb`;
GUI domain `3fc40791d9f74ec8b3081491efdaafb8ca8ab22203c8a85ab4589a169983171e`;
user domain `d98c84dbb64b6851931b0cf00681aa8dee9829f91b2b5d5037ada9ed69746daf`.
Background observers: benjamin
`1c0c1b318aef541d03847818be6da3f67f030ab56269778ce63e3953703ba6e2`;
levi `505e14718fde025b631222a5386a831d083a21e302385941666d2b26c8900acd`.
