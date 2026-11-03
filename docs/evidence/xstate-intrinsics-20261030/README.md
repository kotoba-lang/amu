# Extended-state setup executed under QEMU (JUN-633 slice 2, ADR 0390) -- 2026-10-30

A hand check, not a gate.

## Build

1. The source `SOURCE` of `scripts/seed/check-aiueos-object-xstate.py` defines four exports over `kernel-cr4-set-bits 0x40600`, `kernel-xcr0-set-bits 7`, `kernel-read-cr4` and `kernel-xgetbv`: `cr4on xcr0on rc xg`. This branch's Mac fixed point (F2-signed.macho) compiled it for `x86_64-aiueos-kernel-v1`.
2. `zig ld.lld -T link.ld --oformat binary` linked it with `driver.c` and `entry.S`.
3. The image was run with `qemu-system-x86_64 -kernel img.bin -display none -no-reboot -m 64 -cpu qemu64|max -debugcon file:serial.txt -device isa-debug-exit,iobase=0xf4,iosize=4`.

## Result (`serial.txt`)

| check | qemu64 | max |
|---|---|---|
| `rc` against `mov %cr4` | equal (0x620) | equal (0x620) |
| XSAVE (CPUID.1:ECX[26]) | absent: the writes are not attempted | present |
| `cr4on`: returned value, C read-back | -- | 0x40620, 0x40620 (0x620 \| 0x40600) |
| `xg` against `xgetbv` | -- | equal (0x1) |
| `xcr0on`: returned value, C read-back | -- | 0x7, 0x7 (0x1 \| 0x7) |

Not claimed: any physical CPU.
