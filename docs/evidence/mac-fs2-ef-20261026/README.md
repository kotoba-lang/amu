# Scoped Mac FS2 metadata and range reads (2026-10-26)

This is a diagnostic Apple Silicon runtime component for JUN-417 and
AIUEOS JUN-89. The canonical implementation is
`seed/macos-fs2-runtime-packager.kotoba`, SHA-256
`b4ddb98304a22bf7df320179580c621c4bfad77bb647249176cb475aa6a7efc8`.
The checked-in AArch64 assembly is a one-time word derivation record;
the packager emits the reviewed Kotoba vector without invoking an assembler.
`check_macos_fs2_derivation.py` compares all 293 F/E words and their
two relocation sites with that record.

The callback handles FS2 F metadata and E range reads in an FD3-scoped
regular-file directory. It refuses traversal and symlinks, bounds E to
262,144 bytes and a 32-bit offset, and traps on invalid E requests. Missing
or inaccessible F metadata returns an empty acknowledgement. The separate
diagnostic pair arena is 512 MiB and the vector item arena is 1 GiB;
these are VM test capacities, not release limits.

Evidence:

- [Packager build](packager-build.json): Mac Amu compiler
  `78a006e488b72ea75542bfc592bf80c9a31f9be441df8e98ddb41950ca373717`
  produced the signed packager
  `45febd669218fd74c032a0a86a8dd03504311e2d2bf55b02c206ca60822e751c`.
- [Self-package](selfpack.json): the packager reproduced its unsigned
  Mach-O byte for byte.
- [FS2 gate](fs2-ef.json): a signed Mac native probe passed metadata,
  range read, missing F, and eight negative controls. The gate pins the
  compiler, packager, fixture, EFI and program bytes.
- The unmodified AIUEOS Kotoba media builder compiled and ran on Mac using
  this runtime. Its [media receipt](https://github.com/kotoba-lang/aiueos/pull/509)
  records native build, reproduce, independent GPT/FAT16 readback and ten
  named refusals. The 8 MiB image SHA-256 is
  `dcbb5274789f345d20519aa61137166085fe511d5ad6ec7b42f02bca5ef6b60a`,
  byte-identical to the exact-source Linux arm64 comparator.
- That Mac image passed AIUEOS's QEMU TCG desktop input gate using private
  QMP stdio; it opened Itonami, entered Goal `ab`, and captured the
  framebuffer without a VNC login or manual key press.

This component does not qualify the complete FS2 wire-35 provider,
Mac full-compiler F1=F2=F3 fixed point, signed release or physical AIUEOS
boot. Python only staged and observed these native executions.
