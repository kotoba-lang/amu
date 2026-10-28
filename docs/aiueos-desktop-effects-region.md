# Native desktop effects candidate (JUN-502 / JUN-505)

The existing closed AIUEOS desktop image exposes a guarded 16 KiB region at
private context + `0x23c000`, through `kernel-desktop-effects`. Its end is
exactly the existing `UV-DATA-SIZE` (`0x240000`); this does not enlarge the
image, user mappings, ordinary region grants or public runtime capabilities.
The first 8 KiB holds effect state, part of the previous retained list and
bounded compositor scratch. Bytes8192..12799 own the finite audio descriptor/PCM
buffer; bytes12800..15943 hold the remaining retained-list cache. Neither
DMA descriptor names cache bytes. Total cache:6216 bytes; blur scratch:3920
bytes; BDL reservation:256 bytes; stereo PCM:4096 bytes.
It is disjoint from the Browser surface (`0x238000`, 8 KiB), Browser context
(`0x23a000`, 8 KiB), IME, draft, retained device key and crypto workspace.

The getter reuses the guarded Browser-context getter (private user profile
and sealed GOP checks), then adds exactly 8 KiB. Consumers must first use the
ordinary desktop/GOP image contract; an unsealed host cannot obtain this
region. Caller-selected addresses and lengths are not accepted. The compiler
records the returned region's maximum extent as 16384; consumers narrow it
before memory access. Region-returning product wrappers are not a substitute
for intrinsic provenance.

`kernel-out-u16(port,value)` emits `66 EF` after loading DX/AX;
`kernel-in-u16(port)` clears EAX and emits `66 ED`, returning a zero-extended
16-bit value. These remain kernel-image intrinsics, not ordinary app I/O or
an end-user capability grant. The GUI consumer requires 16-bit AC97 codec
register access; using 32-bit writes is not an equivalent implementation.

The source is a diagnostic candidate. Its Mac source fixed point and existing
user-target controls, plus the exact GUI consumer's QEMU native audio/pixel
observations, are recorded separately. Review rebuilt the Mac root and deterministic ARM/x86 public candidate images
from this full source, keeping their descriptors and source pins consistent.
CDCI role binaries are unchanged. Independent native Linux/controller CI and
physical hardware/release qualification are separate gates.
