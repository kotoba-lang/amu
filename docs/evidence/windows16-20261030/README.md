# 16 KiB window accesses executed under QEMU (JUN-556 C, ADR 0386) -- 2026-10-30

A hand check, not a gate.

## Build

1. The source `SOURCE16` of `scripts/seed/check-aiueos-object-windows16.py` defines six exports: `ld8 st8 ld16 st16 ld64 st64` over `kernel-<load|store>-<u8|u16|u64>-16k`. It was compiled for `x86_64-aiueos-kernel-v1` by this branch's Mac fixed point (F2-signed.macho).
2. The object was linked with `driver.c` and `entry.S` by `zig ld.lld -T link.ld --oformat binary` into a flat Multiboot image.
3. The image was run with:

```
qemu-system-x86_64 -kernel img.bin -display none -no-reboot -m 64 -cpu qemu64 \
  -debugcon file:serial.txt -device isa-debug-exit,iobase=0xf4,iosize=4 -d int -D int.log
```

## Result (`serial.txt`)

The driver passes a 16 KiB static buffer with length 16384. All five accesses past the old 512-byte tier read back what was stored, and C reads the same bytes:

| access | result |
|---|---|
| u8 at 600 | 0x5a |
| u8 at 16383 | 0xa5 |
| u16 at 16382 | 0xbeef (the high byte, read from C at 16383, is 0xbe) |
| u64 at 16376 | 0x1122334455667788 |
| u64 at 8192 | 0x0123456789abcdef |

A u8 load at index 16384 (== length) raises #UD (`v=06` in `int.log`) before the access, so `NOT-TRAPPED` is never printed.
