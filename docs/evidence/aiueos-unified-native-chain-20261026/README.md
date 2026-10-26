# One Mac selfhost compiler for AIUEOS user-v2 and dual EFI (2026-10-26)

The [47-module fixed-point receipt](fixed-point.json) records F1=F2 Mac
native compiler generations. Its signed F2 SHA-256 is
`e4c2e427b7c37651e313d5980fe449d1a577dae044182e8b45abf29d659122fd`.
The [user-v2 gate](user-v2.json) used that F2 to compile the bounded Goal
ELF, reproduce an AIUP v2 512 KiB slot, and refuse seven invalid source
programs, two mutated images, a wrong ELF entry, unsupported slot version
and an existing output. The ELF SHA-256 is
`d1cd47b63ec90df52f6763f63c9410d2a032266412be3dd49238db8ecdf61248`;
the native slot SHA-256 is
`b88caa63c3b782a550f4aefdb84e8ad47be0c6f578cb58352a50573bc05e9b23`.
The prior v1 scalar ELF remains byte-identical at
`a4c9232290f5c172de67411a20bd292ad703865ce69f2fdb66136140508376f8`.

The [dual EFI gate](dual-efi.json) then used the **same F2** to package the
AIUF font, native AIUP v2 slot and AIUEOS kernel in one EFI. It reproduced
the exact EFI SHA-256
`7682a44f81d7b96238ae3ef6f8bb0fd63de7d3ed4693cdbb7feea3805a28edd4`,
kept the legacy font-only EFI byte-identical, and refused changed font/slot
headers, a missing slot and an existing output.

Python staged inputs and checked outputs. Amu selfhost native images
compiled and packaged them; this local gate launched no Linux, JVM, Node or
C compiler process. The paired AIUEOS QEMU receipt proves the resulting
image booted and accepted live Itonami Goal input at CPL3. Signed general
app admission, fresh approval, model/tool operations, durable recovery,
release and physical hardware remain open.
