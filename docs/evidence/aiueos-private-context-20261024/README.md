# Corrected private context, not device authority

This source-bound full36 ARM candidate removes the retired firmware-type
MMIO constructor before public compiler adoption. The full compiler reaches
F1=F2 and passes all24 runtime cases; all18 adopted core modules remain.
Private metadata copying and the pre-frame stack bound are retained.

Two native producer generations reproduce each image/EFI pair. Unsupported
`kernel-pci-mmio` and the retired `kernel-firmware-mmio` both refuse E2101
without producing an artifact. These are missing-primitive refusals, not
proof that a device resource has been granted. Helper/region/owned-window/
width/lock/ISR packaging regressions pass against this exact source graph.

QEMU observes unchanged private map bytes after public metadata forgery,
the declared deep-function stack halt with private map intact, and shallow
return42 with exact fuel999998. The same shallow image is rejected as a
stack-exhaustion positive; its register snapshot and absence of a pass
receipt are retained. These runs use TCG, not native x86 qualification.

The full15-module AIUEOS kernel still refuses on missing kernel-pci-mmio.
ACPI/PCI device resource handoff, live ValueRuntime context and queue ABI,
native media, full desktop/input and successor native x86/controller
adoption remain open. Public/root pins remain the admitted full31 from
PR1547. Firmware map type11 is reserved for firmware runtime and does not
grant an OS device region. See the corrected integration ledger.
