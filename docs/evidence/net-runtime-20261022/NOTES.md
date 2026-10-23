# Native TCP wires 43..47 in the static runtime

Linear JUN-292. Status: measured and passing.

Host: arm64 Linux (6.15), a podman machine (applehv) on macOS arm64. The
x86_64 row ran under qemu-user binfmt with `KEXE_SECCOMP=if-available`,
because qemu-user has no seccomp. No C compiler or loader was used.

## The re-pin

`seed/76` and `seed/77` change the runtime text embedded in every static
image, so the static root was re-pinned C-free, from `98d4bcb7` to
`b2f96378dbf9`.

`selfhost-bootstrap.json` records the result:
- root = S1 = S2 = S3;
- adopted G1 = G2 = G3;
- all 24 cases pass.

The adopted closure does not include the runtime, so the adopted image is
unchanged. This round re-measured no other receipt. The receipts in the
other evidence directories keep the root they name.

## Files

| file | result |
| --- | --- |
| `aarch64-linux.json` | `scripts/seed/check-net-runtime.py`, native, seccomp enforced: 13 start-up cases and 29 wire cases |
| `x86_64-linux.json` | the same gate on x86_64 images under qemu-user: 13 start-up cases and 27 wire cases; the two seccomp controls are `notCovered` |
| `selfhost-bootstrap.json` | `scripts/seed/selfhost-bootstrap.py` on the re-pinned root |

The 29 wire cases on aarch64:
- a loopback round trip: listen, dial, accept, write, read, close, then end
  of file;
- the `timeout` and `refused` answers;
- 20 refusals by name, each exiting 126;
- a request over 65536 bytes;
- a wire that is not granted;
- a missing scope;
- two seccomp controls: a filter without the net rules, and `socket` asked
  in another form. Both die of SIGSYS.

The checker does not admit wires 43..47 yet (E2115). The wire cases use a
test-only compiler with an in-memory admission placed next to wire 42's; it
is never written to `seed/`. `.github/workflows/selfhost-native.yml` runs
the gate natively on the arm64 and the x86_64 runners, so native x86_64
seccomp enforcement is measured there.

## Not covered

- Admitting 43..47 in the checker, a frontend change with an adoption round.
- The capability catalog's `:answered-by` for 43..47. The catalog belongs to
  kotoba-lang/kotoba-lang; amu carries a copy and an embedded resource.
