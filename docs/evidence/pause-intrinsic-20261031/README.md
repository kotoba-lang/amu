# The spin-wait hint executed under QEMU (JUN-633 slice 5, ADR 0393) -- 2026-10-31

A hand check, not a gate.

1. `(defn kotoba_aiueos_spin [] :i64 (kernel-pause))` was compiled for `x86_64-aiueos-kernel-v1` by this branch's Mac
   fixed point. The object carries `pause; xor eax,eax`.
2. `driver.c` calls it 100000 times. Each call must return 0 with RFLAGS.IF as it was.
3. The image was linked with `entry.S` / `link.ld` (the halt evidence's) and run with `qemu-system-x86_64 -kernel
   img.bin -display none -no-reboot -m 64 -cpu qemu64 -debugcon file:serial.txt -device isa-debug-exit,iobase=0xf4,iosize=4`.

Result (`serial.txt`): 100000 of 100000 calls returned 0 with IF unchanged. `pause` has no architectural effect, so this
shows only that the stub executes and returns; it is a hint, and nothing here measures its timing.
