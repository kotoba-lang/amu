# Versioned AIUEOS kernel and user layout (2026-10-26)

Amu now exposes `x86_64-aiueos-kernel-v2` for locked project images and
`x86_64-aiueos-user-v4` for the matching CPL3 ELF. The v2 kernel keeps its
entry at 0x101000, allows RX text through the second MiB, and places its RW
data at physical 0x300000. User-v4 code and request pages are 0x320000 and
0x321000. The corresponding fixed slot is version 3. The EFI packager checks
the complete RX/RW file and physical layout when a dual payload is supplied
and refuses mismatched kernel/slot versions.

A signed Apple Silicon Amu image first rebuilt the 47-module full compiler to a
byte-identical F1/F2 container
`3d6d0c8fe8f9c22a99bfd8d03b641004e3e9eb365599c19bfa11147ff8d7a482`.
The signed F2 SHA-256 was
`7851ccdb31d462ba34e2097b58a6a26c5c916e1b3ac58889f18d6ff5b3a0f990`.
This build used no Linux, JVM, Node or C compiler execution.
On head `38e109ed4`, the Mac bootstrap image and descriptor were pinned to
that fixed point. The descriptor-driven Mac gate reproduced F1/F2, then the
signed F2 cross-built
static Linux ARM and x86 compiler candidates with SHA-256
`24557e872f545e3c23311df51024cfb7176ab87869391fa56b105016413b041d`
and `40dedac1e41bd550fda76f864a27d6efbb874d59632c9e7f6bc277ea0522e7a1`.
The independent native ARM and x86 jobs rebuilt these exact candidates byte
for byte in [run 40289258383](https://github.com/kotoba-lang/amu/actions/runs/40289258383).
Those candidate bytes were pinned on head `4e77b6c3e` as the branch's ARM
bootstrap and x86 public image. That head's full selfhost CI stopped at the
selected core source drift described below.

The full ARM bootstrap then exposed a stale selected core receipt inherited
from the parent branch: the `llm-v1` type work had changed five of the 18
core modules after the CCF adoption pin. A new adoption receipt binds the
current core source unity
`a27634518117679f11a9800df2c03ef1566c7e71b25d239db33783b31a811db7`.
The signed Mac F2 and the G1/G2 core compilers generated the same container
`0efb5556475bbf389e56d9f4e15a62df2fdbfa29bdd7f4de55aa242cfdea7780`
and native code
`c5028498ec0020f2d8c65149c07ba794c0df1e53631ac1df5e2924b950acd8f4`.
`check-macos-core-adoption.py` repeated this three-generation check from the
selected receipt. Native ARM/x86, controller, public CLI, cold C0 and current
core performance remain open until their separate gates pass.

Re-pinning the core and CDCI controller changed the full compiler source.
The current descriptor-driven Mac root now rebuilds F1/F2 to container
`81a151707279ddeca3178579cf4cf70ec01c9baa790f195ba9f41356db18f0ca`
from source unity
`5c6a534f758c6711469121d0deea80a19babc23ce2cb7e6aaefb4f61a3044e60`.
Its signed F2 is
`bfce45991cf28e64925089672503fb1414ded6ca74705efebb1ef1a142066e15`.
The new Mac-produced static ARM/x86 candidates are
`a5b1f69ad391eb79c2e79354de569d859afa338e12c199fb5219b100642a6ae7`
and `f5f1121bb5226bd830a99072bc9f1f794728e39e82b7cd2ebce1682eacf050df`.
These new candidates have not yet passed native Linux fixed-point or public
product CI. The core Mac G1/G2/G3, user-v3 regression and native Darwin smoke
pass with this new F2.

On the 35-module AIUEOS source, the first F2 reproduced a 4,456,728-byte kernel
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
