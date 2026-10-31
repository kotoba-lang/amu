# 4 KiB window tier and fences executed under QEMU (JUN-708, ADR 0401) -- 2026-10-31

A hand check, not a gate.

## Build

1. The sources are those of the gates:
   - `w4k.kotoba` is `SOURCE` of `scripts/seed/check-aiueos-object-windows4k.py`: eight exports over
     `kernel-<load|store>-<u8|u16|u32|u64>-4k`;
   - `fence.kotoba` and `driver.kotoba` are `SOURCE` and `DRIVER` of `scripts/seed/check-aiueos-object-fence.py`.

   This branch's Mac root (F2-signed.macho) compiled them for `x86_64-aiueos-kernel-v1`.
2. `run.sh OUT COMPILER` links them with `driver.c`, `guard.S` and `entry.S` (`zig ld.lld -T link.ld --oformat binary`) and
   runs the image with `qemu-system-x86_64 -kernel img.bin -m 64 -cpu qemu64|max` (QEMU 10.0.3, TCG, zig 0.15.2).
   `guard.S` is the MSR check's guard, passing four arguments. It resumes after a #UD and records the vector, so a trap
   is observed rather than fatal.

## The reference model

`driver.c`'s `ref_trap` follows kotoba-native machine-ir's `x86-kernel-bounds-check` for `[:gmir/kernel-<op>-<w> 4096]`,
aligned. These are the semantics of kotoba-compiler/1's 4 KiB windows, whose guard bytes ADR 0401 shows in the committed
objects. It traps, in this order, when:
- length > 4096 (unsigned);
- base = 0;
- index >= length (unsigned);
- length - index < width;
- index % width != 0.

Otherwise:
- a load is the zero-extended little-endian value;
- a store writes the low `width` bytes and answers the value untruncated.

Each call runs through the guard against an 8 KiB page-aligned buffer, and is compared with the model on three things:
the answer, whether a #UD occurred, and the whole buffer afterwards. A trap must leave the buffer unchanged.

## Cases

Each of the eight forms is called with:
- lengths 0..16, 511..513, 2048, 4088..4097, 4104, 8192, 65536, 2^63 - 1, 2^63 and 2^64 - 1;
- indices at 0..8 and at length - 9 .. length + 1, plus 4088..4096, 2^63 and 2^64 - 1;
- the buffer base, base + 1 (a misaligned base: the reference checks the index only), a base near the page end, and
  null;
- 4000 random tuples clustered on the boundaries.

The fences are called directly. The driver shape is run 64 times:
- `submit` is u32 store, sfence, u8 doorbell store;
- `poll` is u32 load, lfence, u64 load;
- `submit` with length 4097 must trap before any store.

## Result (`serial-qemu64.txt`, `serial-max.txt`, identical)

| | count |
|---|---|
| admitted accesses, answer and buffer equal to the model | 13391 |
| traps, #UD with the buffer unchanged | 40241 |
| -- length > 4096 | 9861 |
| -- null base | 4340 |
| -- index >= length | 9675 |
| -- tail (length - index < width) | 4045 |
| -- misaligned index | 12320 |
| fence calls (3 direct, 128 in the driver shape), each answering 0 without a trap | 131 |

`DIFFS 0000` on both models.

**Negative control.** A mutant compiler built from this branch with the 4 KiB bound changed to 8192 gives `DIFFS 0361`.
Lengths 4097..8192 are admitted where the reference traps.

Not claimed:
- any physical CPU;
- the ordering effect of the fences: QEMU TCG does not reorder, so only their presence, place and answer are shown.
  The bytes are the reference's.
- that kotoba-compiler/1 itself was run. The model is its machine-ir guard, and the guard bytes were compared with its
  committed objects (ADR 0401).
