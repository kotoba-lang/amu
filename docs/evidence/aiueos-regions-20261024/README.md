# Canonical whole-project provenance candidate

The linker resolves import stubs to the actual global function IDs in a
whole-project SIR ledger, retaining every real function and instruction.
Library exports become internal functions; only the entry module retains
kernel ABI exports. The final pass invokes main's `xk-check` and the same
base/length rule for the new widths. It does not substitute the older AST
origin-mask prototype. Imported calls cannot create fresh ABI roots.

The image profile adds one bounded owner: `kernel-boot-info` reads the
loader-provided pointer from private context+80. The matching native EFI
packager owns the fixed160-byte v5 prefix and16KiB memory map. The checker
binds this constructor to exactly16544 bytes; ordinary object/static
profiles do not acquire this root. Consumers narrow it with checked
`kernel-subregion`. Literals, computed/loaded bases and incorrect lengths
continue to refuse. This is not a grant of arbitrary physical memory.

`arm-bootstrap.json` records the full33 native ARM fixed point and unchanged
core/runtime cases. Native two-generation diagnostics cover locked scalar
projects, import/private provenance with8 refusals,16 scalar arguments,
the fixed boot ABI, all32 load/store operations and5 boot-root refusals.
The canonical object admission corpus still passes all27 cases.

The boot-region and memory-width QEMU receipts bind the exact native-produced
kernel/EFI pairs to actual guest execution:42 with999999 fuel. The width
fixture saves and restores its8-byte boot-prefix workspace. The historical
stack16 receipt precedes the boot constructor; its full three-module scalar
source also executed through the canonical AArch64 backend with the same
result/fuel. QEMU is guest emulation, not native x86 compiler qualification.

No public compiler/root adoption, native x86/CDCI successor qualification,
full kernel, ISR/live runtime, native GPT media, desktop or input is claimed.
The earlier project/memory/CPU evidence directories retain their old source
bindings; literal-root fixtures there are superseded by current hardening.
