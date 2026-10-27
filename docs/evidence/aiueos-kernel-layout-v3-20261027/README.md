# AIUEOS kernel-v3 layout candidate (2026-10-27)

`x86_64-aiueos-kernel-v3` keeps the kernel entry at `0x101000` and its
2 MiB RX text limit, but moves RW data to physical `0x400000`. The resulting
gap separates kernel text from the candidate user-v5 code at `0x420000` and
RW region at `0x421000`. Kernel-v1/v2 output for the same locked fixture is
byte-identical under the previous and current signed Mac Amu compilers.

The Mac selfhost compiler rebuilt all 48 modules to identical F1/F2 container
`c7018219ebfb0771846e15bd09acc9d917960b706a42918b8ad51` from source
unity `d5a3556d124ab94402076278a7e65df617c36f6c8c50066e8b869a8d79ee4415`.
The descriptor-bound F2 is `532b900cd8d123fc6674251a5f45838ee4b0542075f3fc7ae83b82fbbe54b8a4`.
The new Mac native layout gate emitted kernel-v3 ELF
`d0b67e0370df798fed4497fba19187b33637530ebee01c464440a152edb41f7e`
and EFI `899593051f075da9099e9d6e8ed9aa3393d54a39b9cb6ecc5c0dd2cc0192ead1`.
It rejected the new target with the older compiler and rejected a kernel-v3
plus user slot-v4 dual package with E7111. The gate is
`scripts/seed/check-aiueos-kernel-v3-layout-macos-native.py`; its receipt is
`workspaces/codex/jun450-kernel-v3-layout-gate-2-20261027/mac-aiueos-kernel-v3-layout.json`.

Separately, the same signed F2 built the historical 35-module AIUEOS source
lock `7f8415fcea1e8f88190c0bf0e398ec4d05c90ca7da5243893506e1dbae0bc08f`.
Kernel-v2 ELF/EFI and kernel-v3 ELF/EFI were admitted as single images. The
v2 plus slot-v3 dual package was admitted, and v3 plus old slot-v3 was
refused. The v3 ELF is
`b8bb4668998805745b8a7b42d83d91398387b60d3da9cd0d86c9431c735515be`.
Receipt: `workspaces/codex/jun450-kernel-v3-probe-20261027/run/receipt.json`.

The signed Mac F2 cross-built static ARM candidate
`24851d1f4e93715a841694dcad067323e91827ddd008325ab181eec8d3b40f62`
and x86 candidate
`2d142697e75fa6b5ec5530c631f85486e357bf904f0c06ec9261ae066ef98428`.
Those bytes are pinned on this draft branch as **candidates**; independent
native ARM/x86 fixed points, full exact-head CI, guest user-v5 mapping,
typed `llm-v1` call, QEMU positive, release, and physical qualification
remain open. The guest still refuses slot-v4. No Linux, JVM, Node or C compiler
was executed to produce the Mac kernel candidate or EFI. Linux hosts used for
independent Amu compiler verification remain a separate proof surface.
