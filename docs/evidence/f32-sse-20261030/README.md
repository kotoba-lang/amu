# Scalar SSE floats executed under QEMU (JUN-633 slice 3, ADR 0391) -- 2026-10-30

A hand check, not a gate.

## Build

1. `fops.kotoba` exports `kotoba_aiueos_fop(op, x, y)`, with x and y as bit patterns. Behind the op selector are all 30 admitted operations:
   - f32 / f64 add sub mul div;
   - the six compares;
   - neg abs sqrt;
   - i64 -> f32 / f64;
   - f64 -> f32 and f32 -> f64.
2. This branch's Mac fixed point (F2-signed.macho) compiled it for `x86_64-aiueos-kernel-v1`, `--fuel 4194304`. The object's SHA-256 is `244a36b1f1d69bbeac82d6aef072ab614a6b6437811e6aaa1cf5851bda6a8f55` and its text is 6642 bytes.
3. `driver.c` computes the same operation in C. It uses zig cc, `-O2 -ffreestanding -mno-red-zone -ffp-contract=off -fno-math-errno`, with SSE and no fast-math.
4. `zig ld.lld -T link.ld --oformat binary` linked it with `entry.S`. entry.S enables OSFXSR / OSXMMEXCPT and clears CR0.EM; MXCSR is left at its reset value.
5. The image was run with `qemu-system-x86_64 -kernel img.bin -display none -no-reboot -m 64 -cpu qemu64|max -debugcon file:serial.txt -device isa-debug-exit,iobase=0xf4,iosize=4`.

## Inputs, per operation

- **Floats:** every pair of the specials (22 f32 / 24 f64): ±0, ±1, ±inf, quiet and signalling NaNs of both signs with payloads, the smallest and largest denormals, the smallest normal, ±max, 0.1, 2^24, -pi, values on the f64 -> f32 rounding boundaries. Then 20000 random pairs and 5000 near-equal pairs.
- **Conversions:** 10 special i64s and 20000 random ones of every magnitude.

## Result (`serial.txt`)

| run | cases | differences |
|---|---|---|
| `-cpu qemu64` | 754860 | 0 |
| `-cpu max` | 754860 | 0 |
| negative control: the object's `addss` patched to `subss` | 754860 | 16868, all in op 0 (f32 add) |
| negative control: the eq `setnp cl` patched to `mov cl,1` | 754860 | 351, all in op 8 (f32 eq) |

Not claimed:
- a physical CPU;
- bit equality with the aarch64 route for generated NaNs (ADR 0391);
- min / max / float -> i64 truncation, which stay refused.
