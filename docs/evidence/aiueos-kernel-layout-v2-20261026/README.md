# Versioned AIUEOS kernel and user layout (2026-10-26)

Amu now exposes `x86_64-aiueos-kernel-v2` for locked project images and
`x86_64-aiueos-user-v4` for the matching CPL3 ELF. The v2 kernel keeps its
entry at 0x101000, allows RX text through the second MiB, and places its RW
data at physical 0x300000. User-v4 code and request pages are 0x320000 and
0x321000. The corresponding fixed slot is version 3. The EFI packager checks
the complete RX/RW file and physical layout when a dual payload is supplied
and refuses mismatched kernel/slot versions.

A signed Apple Silicon Amu image rebuilt the 47-module full compiler to a
byte-identical F1/F2 container
`3d6d0c8fe8f9c22a99bfd8d03b641004e3e9eb365599c19bfa11147ff8d7a482`.
The signed F2 SHA-256 was
`7851ccdb31d462ba34e2097b58a6a26c5c916e1b3ac58889f18d6ff5b3a0f990`.
This build used no Linux, JVM, Node or C compiler execution.

On the 35-module AIUEOS source, that F2 reproduced a 4,456,728-byte kernel
ELF `12397461b3a6ee6ec998ff9bd9a2dc9a838575db65696f84e015cece4185d0a8`,
an 8,280-byte user-v4 ELF
`68ccbb8fee87c9bc25d46765f34b825003c7d49eecd07ea75ffbffad2c46632a`,
and EFI `08d1c651dcd8de336bd2edbe470a83469ba3179813c3d1f7d0c3edc8b16c4065`.
Old kernel-v1 plus slot-v2 and new kernel-v2 plus slot-v3 packaged; both
crossed pairs, a changed ELF entry, a changed RW address and a shortened RW
segment refused with E7111. The old 31-module source still reproduced its
original kernel-v1 ELF
`93b8f315aa564610d423ded13a136d4ceb3a0222afafe1d5114dbab682b4cd15`
and EFI `5e0dd35830ac0893b0163a2c36b3ef1be79392acce1b922694bc4d2e5c5111c1`.

The matching AIUEOS branch records raw GPT/FAT16 and private-QMP QEMU
evidence. This source change alone does not qualify a release or hardware.
