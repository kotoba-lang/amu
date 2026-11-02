# Window accesses on an object's own arrays, executed under QEMU (JUN-553, ADR 0387) -- 2026-10-30

A hand check, not a gate.

## Build

1. `pos.kotoba` (the positive source of `scripts/seed/check-aiueos-object-array-windows.py`) was compiled for `x86_64-aiueos-kernel-v1` by this branch's Mac fixed point.
2. It was linked with `driver.c` and the `entry.S` / `link.ld` of `docs/evidence/windows16-20261030/` by `zig ld.lld --oformat binary`.
3. The image was run with `qemu-system-x86_64 -kernel img.bin -display none -no-reboot -m 64 -cpu qemu64 -debugcon file:serial.txt -device isa-debug-exit,iobase=0xf4,iosize=4 -d int -D int.log`.

## Result (`serial.txt`)

| call | result | meaning |
|---|---|---|
| `get(5)` before any store | 0 | the array starts zero-initialised |
| after `put(i, i + 1)` for every i: `get(0)`, `get(63)` | 1, 0x40 | stores and loads at both ends |
| `sum()` | 0x48464442403e3c3a | the u64 at 0 (bytes 1..8) plus the u64 at 56 (bytes 57..64), as computed by hand |
| `part(0)`, `part(15)` | 0x21, 0x30 | a subregion at offset 32 of length 16 |
| `big(4094, 0xbeef)`, `big(100, 0x1234)` | 0xbeef, 0x1234 | the 16 KiB tier on a 4096-byte `.high_bss` array |
| `get(64)` (index == N) | #UD | `v=06` in `int.log` before the access; `NOT-TRAPPED` is never printed |
