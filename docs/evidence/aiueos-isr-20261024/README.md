# Native interrupt entry candidate

The full35 native ARM compiler retains the complete18 core, i64 AOT and
the whole-project region checker. The native interrupt mechanism ports the
fixed owner ABI from kotoba-native39190953:64 vectors,128-byte stride,
15 saved registers, normalized error frame, context from the image, per-call
fuel4096 with the interrupted fuel saved/restored, then IRETQ. Canned handlers
derive context from the checked GDTR and retain their distinct failure tails.

The project image admits main plus correctly named/typed four-i64 interrupt
callbacks. Hardware arguments do not become memory-region roots, and ordinary
guest calls cannot remint that ABI. Recovery/DF configuration requires owned
4KiB frame and stack regions. No-handler table requests, invalid vectors,
leading zero names, wrong parameter types and callback misuse refuse.

Two native generations produce byte-identical image/EFI pairs. The structure
observer verifies all64 slots, callback/context displacements, replenish and
restore, absent handlers and padding. QEMU loads the generated IDT and executes
INT3, the Kotoba callback and IRETQ back to main. Its marker and result42 pass,
with the original999999 fuel restored. Changing only the callback marker to43
returns0; the same observer rejects it. The QEMU pair is byte-identical to the
formally checked F2 pair, not a hand-written or foreign object.

An initial table build refused a stale resolved label. The fix clears each
newly reserved assembler label, including the new table phase. Regression
diagnostics retain locked projects, private/import provenance, CAS lock/XCR,
all32 memory-width operations and the canonical27 object admission cases.

This is native ARM compilation and QEMU TCG guest execution. Native x86/CDCI
successor adoption, error-code interrupt execution, full kernel, live runtime,
native media, desktop and input remain separate. The full15-module kernel
now reaches the canonical region refusal in rtl8125, rather than an unknown
interrupt intrinsic. Its physical/length ABI still needs reconciliation.
