# Positive ticket-erase evidence for the head observer (2026-10-28)

Review thread on `check-aiueos-entry-qemu.py` (P2, "Refresh the positive ticket evidence for the
full erase check"): the recorded guest left non-zero 72-byte state after consumption, so replaying
the stricter `== bytes(72)` assertion failed. This note pins a matching positive guest and receipts
for the observer of the PR head `eba8e3f5c`.

Observer: `scripts/seed/check-aiueos-entry-qemu.py`, 30587 bytes, SHA-256
`2997261b7c2c3f0950517df33b8052bc0dc36e91207a6961cedeb03a05642345` (the head's file; both receipts record it).

Guest: `os/aiueos/native/llm_v1_digest_probe.kotoba` of kotoba-lang/kotoba main at `be7a83fa0`
(SHA-256 `59a7e921a8f5e86016e397af299e80eab392e8529ba03b48591175eda5d5499a`; its `llm_v1_ticket.kotoba`
is `56e29c1feaf81aae7f5b6d3f0d1d7b63a9db2eccd6b25e5ea1ac4ef9d3e51456`), built with the library's
`build-native-kernel-macos.py`, `--kernel-target x86_64-aiueos-kernel-v1`, 22 locked modules, ELF and
EFI reproduced. It runs the current-request admission flow, so the mode is `--llm-admission`
(the older ticket-only guest cited in the review is not what this head's observer expects; the
flag `--llm-digest` alone reads the ticket at another address and fails on a guest of this version).

Run (Apple Silicon, QEMU 10.0.3 TCG, OVMF `edk2-x86_64-code.fd`):
`check-aiueos-entry-qemu.py --efi BOOTX64.EFI --kernel KERNEL.ELF --qemu ... --firmware ... --llm-admission --remaining-fuel 1073741824`.

Two compilers, same source, same observer, both `PASS_AIUEOS_ENTRY_QEMU`, result 42, 17 checks all 1,
`erasedTicket` = 72 bytes with SHA-256 `834a709ba2534ebe3ee1397fd4f7bd288b2acc1d20a08d6c862dcd99b6f04400`
(the digest of 72 zero bytes):

| Compiler | Mac root SHA-256 | EFI | kernel | receipt |
| -- | -- | -- | -- | -- |
| this head's committed root | `4350f3ba...` | `ccb9789c...` | `cd034997...` | `entry-qemu-admission-compiler-4350f3ba.json` |
| head + kernel-rdrand/rdseed (amu#1637) | `9d023d99...` | `5c715bdf...` | `e4c0ee2d...` | `entry-qemu-admission-compiler-9d023d99.json` |

Negative control already in the observer: the same assertion failed on the older recorded guest
(non-zero words after consumption), and `--llm-digest` on this guest fails on the erased-ticket
read (the bytes are `0xaf`, the observer's untouched sentinel, because that mode reads another address).

Limits: QEMU TCG, diagnostic; no human approval, provider dispatch or user call (`hostAdmission`,
`userCall`, `providerDispatch` are false in the receipts). The guest source lives in kotoba-lang/kotoba,
not in this repository.
