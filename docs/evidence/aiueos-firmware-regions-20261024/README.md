# Firmware catalog and bounded native stack

The full36 native ARM candidate preserves all18 core modules, reaches F1=F2
and passes all24 runtime cases. Before main, the closed image validates map
size/stride/pointer and copies firmware descriptors into private context512..
16895. A ready marker is written after the copy. The image profile reserves
low20KiB for context/catalog. This is the non-live layout; ValueRuntime queue,
capability-table and arena ownership require a separate reconciled ABI.

`kernel-firmware-mmio(base,bytes)` admits at most64KiB contained within one
sealed EfiMemoryMappedIO(type11) descriptor, with alignment/page count,
non-wrapping bounds and the original512GiB ceiling. Reserved/RAM descriptors
are not MMIO grants. Writable public metadata cannot add authority.

All profile2 function prologues check their proposed stack frame before
writing it. Exhaustion disables interrupts and halts directly, avoiding a
recursive #UD callback on the exhausted stack. The floor/padding protects the
catalog. Other native/object profiles retain their existing prologue behavior.

QEMU TCG verifies public-map forgery does not change the sealed first record;
forged-map/RAM/zero-length/oversized/overflow requests reach the constructor's
exact UD2. A deep non-tail recursion halts at its declared guard with the
catalog intact; shallow recursion returns42/fuel999998 and is rejected as a
stack-exhaustion positive. Typed INT3 callback/IRETQ still returns42 with
fuel999999. Native two-generation fixtures and helper/region/window/width/
lock/ISR regressions and all27 original object admission conditions pass.

This OVMF map contains no type11 descriptor. Actual platform MMIO positive
qualification remains OPEN, as do native x86/controller adoption, live ABI,
media and desktop/input. The complete15-module kernel moves past mmio-window
and now refuses E7106 at rtl8125/mmio-load-u32, SIR924. No full kernel artifact
or hardware/network pass is claimed; source declarations are retained.
