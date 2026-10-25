# Native PCI resource collector candidate

The full37 ARM compiler retains all18 adopted core modules and reaches
F1=F2 (b482a0738a1c17e6...), with all24 runtime cases. Both generations emit
identical kernel and EFI bytes for explicit `--pci-resources v1`, including
payload placement and3 unsupported-option refusals. Existing v5 packager
positive/corruption controls pass. Public/root pins remain the admitted
full31 from PR1547; successor native x86/controller adoption is open.

The native EFI producer enumerates PCI I/O handles and BAR0..5, checks the
ACPI QWORD descriptor, and stores exact segment/bus/device/function/BAR and
vendor/device identity with host base/bytes. Its v6 catalog starts after the
unchanged160-byte prefix and16KiB firmware map. The closed collector profile
is segment0, <=256 handles, <=128 memory records, zero address translation,
positive nonwrapping extents below512GiB. Other descriptors/overflow refuse.
Pool/protocol cleanup precedes the final memory map/ExitBootServices.

QEMU/OVMF executes the native-produced EFI, publishes3 memory BARs, and
reaches the native entry result42/fuel1024. The catalog exactly matches
independent QMP PCI identity/address/size observations. This qualifies raw
resource collection for this virtual platform, not OS ownership, physical
RTL8125 access or the complete kernel. Empty/error/limit firmware execution
controls and the private runtime ownership consumer remain open.

The v5 behavior remains explicit/default. A v6 catalog is not a grant from
a firmware memory type. The whole kernel/live, live ABI, native media and
desktop/input gates remain open in JUN-31.
