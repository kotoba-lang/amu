# Bounded general-entry Mac packager

The Kotoba packager now has an explicit
`fs2-cli-stdio-general <main-offset>` build mode. It accepts an extracted
raw code slice of 4 bytes through 4 MiB and a decimal, aligned entry offset
whose first instruction is within that slice. The scoped FD3 FS2 writer and
8 MiB total request/output budget still apply. This is build-tool input
admission; release signing and the provenance of raw code require separate
checks. Existing diagnostic modes keep their exact raw-length allowlists.

The exact version under test is [packager-v2.kotoba](packager-v2.kotoba),
SHA-256
`bdfcaa02041623fca241352a092c5033b74f83faf0209c0fafefeb99278f9a66`.
The Mac F5 full compiler compiled it to a 39,534-byte
`aarch64-macos` container (SHA-256
`bd5a9e2cfcad053023a8c2cb9f059e24f267afc642c37f84d41bdda380c841f1`)
and extracted its 39,505-byte `main` code at offset 35,312
(SHA-256
`85b7eed0a4435e6f6d9a6a305de31c49b069dfe65320223d9286ca908020b8fc`).

An Amu-built ARM Linux root built the first packager image once: static
packager ELF SHA-256
`7bb3b903e4be39cf4e59da1c7bac1bbe3feeeeb2bf3d704d96fbb27c75e1a2f9`.
That producer packaged the Mac code at entry 35,312 into a 65,536-byte
unsigned Mach-O, SHA-256
`14281f2326b7ba115369aa114644bc8e40d41a50032661573c0e87ff36828173`.
The signed bridge SHA-256 was
`5a683407fd72eebd349ffcfa184baf46024743f2cb91a4845e2bcbbe3074a8d1`.

On Mac, the bridge packaged the same raw code to F1. Signed F1 packaged it
again to F2. Both unsigned outputs were byte-identical to the bridge.
Signed F2 packaged the full compiler F5 raw code using entry 0; the
3,293,184-byte unsigned Mach-O SHA-256 was
`40a30d60c8df36d8f72cf1207952a355b1e563e0729fdb02be11b38560b5baa4`,
matching the previous producer. Its signed output passed the passwordless
FS2 check/compile and refusal gate. Nonnumeric, unaligned, out-of-bounds
entry values and a new raw length in legacy mode each returned exit 2
without creating output.

`scripts/seed/check_macos_generic_packager.py` repeats the Mac-only compile,
extract, two self-package generations, full-compiler packaging, negative
controls and sample gate with pinned source/images/raw. The previous fixed
size [packager gate](../mac-packager-selfhost-20261026/README.md) remains
replayable from its source snapshot. The initial generic bridge still used
ARM Linux; subsequent raw code versions can be packaged by this Mac image
without another Linux producer, subject to explicit entry and artifact
admission. Complete FS2/source-lock, AIUEOS build/boot and release
qualification remain open.
