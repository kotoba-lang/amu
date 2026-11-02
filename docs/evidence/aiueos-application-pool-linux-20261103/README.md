# Native Linux application-pool readback — JUN-757

Source commit `35f252993564478df1a4a8d0143c6e2cdc394a70`, PR #1793,
workflow [41504494179](https://github.com/kotoba-lang/amu/actions/runs/41504494179).
The exact-head PR checks and complete workflow succeeded. The unmodified
native producer loader checked the actual ARM/x86 generation receipts.
Each of two producers per ISA compiles/packages the full v4/v7 fixture and
refuses the old target, missing PCI grant, wrong lock and literal region.
The complete ELF and EFI match the Mac/QEMU execution evidence.

The two original CI receipts and exact workflow/check readbacks are retained.
All 62 graph records (61 source modules plus manifest), each route's full
ELF/EFI bytes and all exits were independently read back locally. This is
compiler/artifact evidence; no Linux guest execution, physical allocation,
CPL3 pool denial, live Kekkai app connection, native SSH or release is claimed.
Descriptor release/qualification flags remain unchanged.
