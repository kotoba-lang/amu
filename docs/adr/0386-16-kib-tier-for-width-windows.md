# ADR-0386 -- the aiueos object route's u8 / u16 / u64 windows get a 16 KiB tier (JUN-556 C)

- Status: **implemented** (seed/74, `scripts/seed/check-aiueos-object-windows16.py`).
- Date: 2026-10-30
- Tracking: JUN-556 (feature C, "large windows").
- Follows: ADR 0373 (bounded kernel memory windows), JUN-556 B (u8 / u16 / u64 at 512 bytes).

## Context

The u8, u16 and u64 window accesses trap when the region is longer than 512 bytes. Kernel code that walks a TLS record, a
DMA ring or a 4 KiB page cannot address it directly. The only workaround was a one-byte `kernel-subregion` per access,
as `kotoba/bytes.kotoba` does. The u32 pair already had a second tier: `kernel-load-u32-16k`, at 16384 bytes.

## Decision

Six new stubs follow the width block:

- `kernel-load-u8-16k`, `kernel-store-u8-16k`
- `kernel-load-u16-16k`, `kernel-store-u16-16k`
- `kernel-load-u64-16k`, `kernel-store-u64-16k`

They are ids 12..17. Their code is that of ids 6..11 with `cmp rcx,16384` in place of `cmp rcx,512`. Every other check is unchanged and still traps (ud2) before the access:

- base non-null;
- index below length;
- the access fits without wrapping;
- alignment, above one byte.

Like every window, the base must be a rooted region and the length must be that region's own (E7106).

The block is appended only to a source that names one of its stubs. Each 16 KiB name contains the 512-byte name, so the width block is appended too and the ids stay positional. Consequences:

- a source that names no 16 KiB stub compiles to the bytes it always had;
- the gate pins the 512-byte width object's SHA-256.

## Gate

`check-aiueos-object-windows16.py` (Mac fixed point) checks:

- **six-16k:** the six accesses decode in order with bound 16384, every branch lands on the ud2, and no 512-byte window is present;
- **mixed:** a 512-byte and a 16 KiB u8 load in one object keep their own bounds;
- **unchanged:** the 512-byte object is byte-identical (`a8ac4f07`);
- **refused (E7106, nothing written):** an unrooted base and a free length.

It fails on the previous compiler: `E2101 unknown or unsupported form 'kernel-load-u8-16k'`.

`docs/evidence/windows16-20261030/` ran the object under QEMU by hand. Accesses at 600, 8192, 16376, 16382 and 16383 round-trip; index == length raises #UD.

## Non-goals

- No tier above 16 KiB.
- No 16 KiB u32 store; the existing `kernel-store-u32` stays at 512 bytes.
- No change to the locked-project route, which keeps its four memory stubs.
