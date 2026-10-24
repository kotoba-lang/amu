# Native AIUEOS entry candidate, 2026-10-24

`qualification.json` binds the exact full30 source graph, fixed-point
compiler generations, generated kernel/EFI pair, diagnostic sources and
QEMU/firmware to the results. `entry-registers.txt` is the actual QMP readback.

* The adopted native root688324e0 builds full30 F1=F2 `2ebb99ba0dee2be4`;
  the unchanged adopted core image and all24 native runtime cases pass.
* Six images across both generations pass the ELF/entry/context ABI;
  34 source/flag/output refusals and72 corrupted-image controls reject.
  Eight object fixtures retain the original ABI and byte equality with the
  previous **native** root's output. No hosted oracle was invoked.
* Six EFI images across both generations pass ordinary/payload/512KiB
  boundary checks.44 corrupted-kernel, payload, mode and overwrite controls
  reject, including a physical overlap with equal virtual/physical addresses.
* The final generated pair boots in QEMU10.0.3/OVMF. The literal42 kernel
  reaches RIP0x10104b/RAX0x2a with fuel1024. Guest memory confirms boot-info
  v5, a bounded firmware map and GOP1280x800 metadata. The AIUEOS boot ABI
  verifier also accepts scratch15pages/GOP/imports0.
* A separately native-produced literal43 kernel reaches the same halt;
  the entry check rejects its RAX0x2b, exits1 and emits no pass receipt.

All compiler/packager execution was native ARM64 Linux in the local VM.
QEMU TCG is the declared guest execution host. Python orchestrated and
inspected; it did not emit guest machine code or package the image.

This is **not complete-kernel acceptance**. The unchanged real kernel's
source-path command refuses usage; module-lock refuses E6015 with no output.
Full project linking, multiple exports/ISR/live runtime, remaining kernel
intrinsics, native media and actual desktop/input still need integration.
GOP metadata is not a rendered desktop. Browser/CSSOM and Itonami remain
above these dependencies in JUN-93; JUN-31 remains In Progress.

The installed public product, adopted root, native-controller artifacts and
their pins are unchanged. Actual native x86 qualification and current
root/product/controller adoption remain open; these Python diagnostics do
not qualify or restart CDCI.

Diagnostic reproduction on native ARM64 Linux uses the current repository:

```
python3 scripts/seed/selfhost-bootstrap.py --tier pr --output BUILD
python3 scripts/seed/check-aiueos-image-native.py --build BUILD --output IMAGE_CHECK
python3 scripts/seed/check-aiueos-boot-native.py --build BUILD --output BOOT_CHECK
```

Then run `scripts/seed/check-aiueos-entry-qemu.py` with the generated
`BOOT_CHECK/F2/plain.EFI`, `BOOT_CHECK/F2/KERNEL.ELF`, local QEMU/OVMF paths
and a new scratch output directory. Compiling the same declared program
with43 instead of42 and packaging it through the same compiler supplies
the wrong-result control; the check must fail.
