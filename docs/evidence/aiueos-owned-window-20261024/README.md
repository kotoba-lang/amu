# Sealed contiguous scratch windows

`kernel-owned-window(slot, bytes)` derives its base only from the pre-main
sealed allocation. Native guards require slot0..14, positive page-aligned
bytes<=61440 and bytes<=(15-slot)*4096. Its canonical region extent is the
exact source of the length argument. Loaded or computed pointers remain
unrooted; a different access length refuses. The one-page constructor and
all previous scalar/runtime profiles retain their own bounds.

The full35 ARM compiler reaches F1=F2, preserves the complete18 core and
all24 runtime cases. Both generations emit identical image/EFI fixtures.
QEMU verifies a12KiB window after public scratch metadata was overwritten,
a subregion at its last page, aligned64-bit write/read/restore across that
window, and result42/fuel999999. The maximal61440-byte grant also returns42.
Seven invalid slot/length fixtures reach the constructor's exact UD2;
the same guard observer rejects the valid maximal window as a negative
control. Canonical provenance, one-page forgery, all32 widths and typed ISR
regressions pass. This is native ARM compilation with QEMU TCG execution.

Native x86/controller successor adoption, complete kernel and live runtime,
media, desktop and input remain open. The complete15-module kernel with
v5/scratch source migration still refuses E7106 in rtl8125 at global SIR865;
source trimming and literal physical roots are not acceptance mechanisms.
