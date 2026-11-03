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
