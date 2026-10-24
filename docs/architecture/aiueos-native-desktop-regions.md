# AIUEOS native desktop region contract

The diagnostic desktop extends the v3 private context, without changing
all18 normal adopted core modules or trimming a locked owner graph.

The sealed GOP record at private30416 contains framebuffer base/extent,
width/height/stride/format, readiness and the paired native font pointer.
The initializer requires alignment, bounded dimensions/stride/format,
checked pixel extent and complete containment in one allocated PCI BAR.
Mutable firmware fields and scalar dimension calls grant no memory region.
Failure stops in the local CLI/HLT loop before application code.

The only framebuffer constructor exposes a complete4KiB page, with checked
index/extent. Native font is exactly524288 bytes at the paired v6 payload
offset and must carry a bounded AIUFv1 header. The8192-byte Browser surface
and8192-byte renderer/input state occupy private offsets0x238000 and
0x23a000. These do not overlap domain windows, PML4/PDPT/PD/PT, private IDT,
legacy FPU state, DMA/snapshot pages, queues, capabilities or arenas.

The full30 desktop root registers domain73, enables the v3 private tables
and IDT, then runs a bounded existing Browser-frame2 diagnostic in CPL0.
Keyboard/mouse are polled with interrupts disabled. Native GPT/FAT16 media
boots via QEMU q35 SATA with a temporary overlay. The independent observer
checks actual CR3/WP/NX/SCE, domain73, sealed PCI/GOP/font, completed-frame
state, keyboard open/close, pointer move/click/release, changed screenshots
and unchanged source media bytes. No network device is attached.

Admission/refusal runs with converged native ARM and actual x86 producers;
QEMU guest observation is separate from native compiler execution and the
native CDCI controller verdict. Raw-media/desktop input does not qualify
shared Browser/CSSOM parity, user-mode dapp execution, preemption,
service connectivity, general installer compatibility or physical hardware.
The cards explicitly show unregistered services. The AIUEOS ledger and
JUN-31/JUN-93 track that dependency boundary.
