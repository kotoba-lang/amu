# Halt-until-interrupt executed under QEMU (JUN-633 slice 4, ADR 0392) -- 2026-10-31

A hand check, not a gate.

## Build

1. `(defn kotoba_aiueos_wait [] :i64 (kernel-wait-interrupt))` was compiled for `x86_64-aiueos-kernel-v1` by this
   branch's Mac fixed point (F2-signed.macho). The object carries `sti; hlt; cli; xor eax,eax`.
2. `driver.c` does the setup:
   - remaps the PIC to vectors 32..47 with only IRQ0 unmasked;
   - programs the PIT for 100 Hz;
   - installs an IRQ0 gate that counts the ticks and sends EOI.
   It then calls the wait 20 times. Each call must return 0 after at least one tick has been taken, with RFLAGS.IF
   clear before and after.
3. The image was linked with `zig ld.lld -T link.ld --oformat binary` against `entry.S` (the xstate evidence's entry)
   and run with `qemu-system-x86_64 -kernel img.bin -display none -no-reboot -m 64 -cpu qemu64 -debugcon file:serial.txt
   -device isa-debug-exit,iobase=0xf4,iosize=4`.

## Result (`serial.txt`)

| run | waits | returned after a tick, IF clear | ticks |
|---|---|---|---|
| the wait object | 20 | 20 (each after exactly one tick) | 20 |
| negative control: an object that returns 0 without waiting | 20 | 0 | 0 |

Not claimed: a physical CPU, or the drivers' use of the wait (kotoba-lang/kotoba, JUN-598).
