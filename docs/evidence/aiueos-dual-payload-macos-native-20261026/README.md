# Mac native AIUEOS font and user-slot EFI (2026-10-26)

The [fixed-point receipt](fixed-point.json) records 47 Amu source modules and
byte-identical F1/F2 Mac native compiler generations. The compiler packaged
one EFI containing a 512 KiB AIUF font followed immediately by a 512 KiB AIUP
v2 user slot. The [native package gate](dual-gate.json) reproduced that EFI,
compared a legacy single-font EFI byte for byte with the prior compiler's
output for the same kernel, and refused changed font magic, user-slot magic,
user-slot version, missing slot and an existing output path. The dual EFI
SHA-256 is `7682a44f81d7b96238ae3ef6f8bb0fd63de7d3ed4693cdbb7feea3805a28edd4`.

To repeat the host-side gate, run
`scripts/seed/check-aiueos-dual-payload-macos-native.py` with the exact
compiler, fixed-point receipt, kernel, font, slot and legacy control EFI
named by the receipt, and a new private `--output` directory. Python stages
and observes; the Mac native Amu selfhost executable builds the EFI. No
Linux, JVM, Node or C compiler was run in this gate. The AIUEOS QEMU boot
and CPL3 readback are recorded in the paired AIUEOS source branch.

This is a local diagnostic image. The slot is checked by a fixed app digest
in the guest; general signed admission, per-operation consent, model/tool
execution, durable turns, release and physical hardware remain open.
