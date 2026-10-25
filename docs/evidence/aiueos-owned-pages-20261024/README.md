# Sealed loader-owned scratch pages

The full35 ARM candidate rebuilds to byte-identical native generations and
retains all24 runtime cases and the complete18 compiler core. The public
full31 compiler and native CDCI successor adoption remain separate.

`kernel-owned-page(slot)` returns one 4096-byte region from the loader's
exact fifteen-page allocation. A hidden native initializer snapshots the
base/page count into private image context before guest main, after checking
boot magic/version, alignment and overflow. It preserves the 77-byte entry
shim and post-return PC. Slot selection cannot supply an arbitrary address.

The QEMU fixture first overwrites the public scratch base with zero, then
obtains slots0 and14, verifies their61440-byte allocation boundaries, writes,
reads and restores a byte in slot0, restores metadata and returns42 with
999999 fuel. Invalid slots15 and-1 produce #UD at the constructor's exact
UD2, rather than an arbitrary loader failure. The guard observer rejects
valid-slot0; the ordinary entry observer independently confirms result42.

Native two-generation diagnostics refuse loaded/computed roots, wrong
extent and forged page-fault recovery pages. Regression gates retain the
locked project, scalar16 calls, eight canonical provenance refusals,
CAS/XCR, all32 memory operations, typed ISR table and seven ISR refusals.
An initial positive fixture used the512-byte instruction on a4096-byte
region and correctly trapped; the corrected fixture uses4KiB instructions.

This is native ARM compilation plus QEMU TCG guest execution. Native x86
successor/controller adoption, full kernel, live runtime, native media,
desktop and input are open. The full kernel's old physical-window and
helper-length ABI must be reconciled without admitting literal roots.
