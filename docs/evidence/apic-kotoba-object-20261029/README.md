# kernel/apic.c as a Kotoba object (JUN-556, 2026-10-29)

`apic.kotoba` is `lib/kotoba.aiueos/os/aiueos/kernel/apic.c` written against the object route's D1 (extern calls), D3/D3b (data
cells exported by name) and D4 (fixed-address MMIO) features. It compiles on a Mac with the compiler built from this branch:

    amu compile apic.kotoba --target x86_64-aiueos-kernel-v1 --output apic.o --fuel 1000000

The object (4570 bytes, SHA-256 63107b8353047647e167a9298fe007a3a9f47c6f1e7dfcd0483a1fbd7492ae0e) has exactly the surface of apic.c, read back with an independent ELF parser:

| | apic.c | apic.o |
|---|---|---|
| functions | aiueos_apic_timer_mask / _unmask / _initialize | the same three, GLOBAL FUNC |
| globals other objects link to | aiueos_apic_timer_ticks (u64), aiueos_apic_mmio_base (pointer) | GLOBAL OBJECT, size 8, in .data (80 and 88) |
| calls into other objects | kotoba_aiueos_msr_read / _write | undefined GLOBAL NOTYPE, two PLT32 -4 relocations |
| register access | volatile MMIO at 0xfee00000 + 0x20, 0xf0, 0x320, 0x380, 0x3e0 | immediate-address movabs sequences |

## What this does not show

* Nothing linked or ran this object. The replacement is not behaviour-equivalent until it boots: the interrupt path
  (entry.S increments the tick and reads the MMIO base by name) and the timer need the QEMU/OVMF gate on a Linux host.
* `volatile` is not an instruction-level notion here: each access is its own load or store in program order, which is what the C
  needs, but nobody compared disassembly with the C compiler's output.
* The C exports return void/int in the C ABI; these return an i64 in rax, which a caller of `int` and `void` functions ignores
  or truncates identically. The export shims replenish a fuel word and set r9 as every aiueos object does.
* The kotoba-side verifier does not accept cells, data symbols or MMIO yet, so this object cannot enter the image.
