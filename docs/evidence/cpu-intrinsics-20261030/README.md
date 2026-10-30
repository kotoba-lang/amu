# CPU feature reads executed under QEMU (JUN-633, ADR 0389) -- 2026-10-30

A hand check, not a gate.

## Build

1. The source `SOURCE` of `scripts/seed/check-aiueos-object-cpu.py` defines six exports, `ca cb cc cd ts rr`, over `kernel-cpuid-<eax|ebx|ecx|edx>`, `kernel-rdtsc` and `kernel-rdrand`. This branch's Mac fixed point (F2-signed.macho) compiled it for `x86_64-aiueos-kernel-v1`.
2. `zig ld.lld -T link.ld --oformat binary` linked the object with `driver.c` and `entry.S` into a flat Multiboot image.
3. The image was run on two CPU models:

```
qemu-system-x86_64 -kernel img.bin -display none -no-reboot -m 64 -cpu qemu64|max \
  -debugcon file:serial.txt -device isa-debug-exit,iobase=0xf4,iosize=4
```

## Result (`serial.txt`)

| check | qemu64 | max |
|---|---|---|
| cpuid: 4 registers × 9 leaves (0, 1, 7.0, 7.1, 0xd.0, 0xd.1, 0x80000000..2) against inline-asm `cpuid` | 36 equal | 36 equal |
| rdtsc over 1000 reads | monotonic | monotonic |
| rdrand | absent (CPUID.1:ECX[30] = 0), not called | present, non-zero |

The first `qemu64` run called rdrand unconditionally and stopped on the #UD a CPU without RDRAND raises. The driver now checks CPUID first, as `device_result.c` does, and the ADR records that as the caller's duty.

Not claimed: any value that differs between CPUs (vendor, family, feature bits, entropy) beyond these two QEMU models.
