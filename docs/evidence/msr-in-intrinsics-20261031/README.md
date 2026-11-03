# Bounded MSR and port-input accesses executed under QEMU (JUN-600, ADR 0399) -- 2026-10-31

A hand check, not a gate.

## Build

1. `msr.kotoba` is the source `SOURCE` of `scripts/seed/check-aiueos-object-msr.py`. It exports
   `kotoba_aiueos_msr_read [i]` and `kotoba_aiueos_msr_write [i v]`, which select one of the five literal indices by the
   run-time index (as kotoba's msr-read / msr-write objects do), and `pcr [a]`: `kernel-out-u32 0xcf8 a`, then
   `kernel-in-u32 0xcfc`. This branch's Mac root (F2-signed.macho) compiled it for `x86_64-aiueos-kernel-v1`.
2. `run.sh OUT COMPILER` links it with `driver.c`, `guard.S` and `entry.S` (`zig ld.lld -T link.ld --oformat binary`) and
   runs the image with `qemu-system-x86_64 -kernel img.bin -m 64 -cpu qemu64|max` (QEMU 10.0.3, TCG, zig 0.15.2).
   `guard.S` resumes after a #UD (vector 6) or #GP (vector 13) and records the vector, so a trap is observed rather than
   fatal.

## Result (`serial-qemu64.txt`, `serial-max.txt`, the same on both models)

| check | count | result |
|---|---|---|
| read of each admitted MSR against `rdmsr` | 5 | equal (APIC_BASE 0xfee00900, EFER 0x500, STAR / LSTAR / FMASK 0) |
| an index not in the list (0, 0x10, 0x277, 0xc0000083, 0xc0000085, 0xc0000100, 0x1a, 0x1c, -1, 2^40 + 0x1b): read and write | 10 | the object answers 0, no trap, STAR unchanged |
| write, then read back with `rdmsr`, against the same write done by inline-asm `wrmsr` | 606 | equal, the object answers the value, no trap. STAR: 200 random 64-bit values; LSTAR: 200 canonical addresses, half in the upper half; FMASK: 200 random 32-bit values; EFER: unchanged, \| SCE, \| NXE, \| SCE \| NXE; APIC_BASE: unchanged, \| global enable |
| write the run-time bound refuses: EFER clearing SCE, clearing LME, setting FFXSR, 0, all ones, and 64 random values with a bit outside SCE \| NXE; APIC_BASE moving the window, clearing the enable, setting x2APIC enable | 72 | #UD before the `wrmsr` every time, the register unchanged |
| PCI configuration dword through `kernel-in-u32 0xcfc` against `outl 0xcf8` / `inl 0xcfc`: bus 0..1, device 0..31, function 0..7, every dword offset | 32768 | equal (0:0.0 reads 0x12378086, the i440FX host bridge) |

`DIFFS 0000` on both models.

A mutant source that writes STAR's value to LSTAR and adds 1 to the configuration read gives `DIFFS 80c8`.

Not claimed: any physical CPU; the guard's behaviour for a value whose write the CPU itself would refuse with #GP (the
bound runs first, so such a value outside the admitted bits reaches #UD, and one inside them reaches the CPU's check).
