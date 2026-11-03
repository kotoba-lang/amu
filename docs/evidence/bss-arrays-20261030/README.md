# .bss / .high_bss array addresses on QEMU (JUN-556 C, ADR 0385) -- 2026-10-30

A hand check, not a gate.

## Build

* `arrt.kotoba` was compiled for `x86_64-aiueos-kernel-v1` by the Mac fixed point of this branch (F2-signed.macho).
* `build4.py` linked it with `harness4.S` into a flat Multiboot image at 0x100000. Each harness reserves 8 KiB for `.bss` and 8 KiB for `.high_bss`, and defines `memset` and `sumbytes`.
* Each image was run with:

```
qemu-system-x86_64 -kernel image.bin -display none -no-reboot -debugcon file:serial.txt \
  -device isa-debug-exit,iobase=0xf4,iosize=0x04 -m 64
```

## Results

The linker placed `.bss` at 0x100890 and `.high_bss` at 0x102890.

| export | returned | expected |
|---|---|---|
| `a0` (`bss-addr-0-1280`) | 0x100890 | `.bss` + 0 |
| `a1` (`bss-addr-1-24`) | 0x100d90 | `.bss` + 1280 |
| `h0` (`highbss-addr-0-1536`) | 0x102890 | `.high_bss` + 0 |
| `fill` | 0xc28ccc398 | 1280*0x5a + 24*0x11 + 8 padding zeros = 115608, plus 1536*0x22 = 52224 times 10^6 |

The stack was balanced after every call (`01`).
