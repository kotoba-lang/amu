# ADR-0401 -- the aiueos object route gets the 4 KiB window tier and the three fences (JUN-708)

- Status: **implemented** (seed/74, `scripts/seed/check-aiueos-object-windows4k.py`,
  `scripts/seed/check-aiueos-object-fence.py`).
- Date: 2026-10-31
- Tracking: JUN-708 (moving the AIUEOS kernel objects off kotoba-compiler/1).
- Follows: ADR 0373 (bounded kernel memory windows), ADR 0386 (16 KiB tier), ADRs 0389-0400 (opt-in intrinsic blocks).

## Context

Twelve AIUEOS kernel objects still build only with kotoba-compiler/1, because the native object route refuses two
families of forms with `E2101 unknown or unsupported form`:

- the 4 KiB window tier, `kernel-<load|store>-<u8|u16|u32|u64>-4k`: ecdsa-p256, ecdsa-p256-sign, rsa2048, x25519,
  aes128-gcm, aes128-gcm-selftest, tls13-record, hkdf-sha256 (and device-worker-canonical);
- the fences, `kernel-fence-store` / `kernel-fence-load`: rtl8125-program, -ring-build, -rx-poll, -tx-submit.

The reference is kotoba-native `src/kotoba/native/machine_ir.cljk` (local checkout at 3919095):

- `kir-kernel-memory-ops` maps every `kernel-<op>-<w>-4k` to `[:gmir/kernel-<op>-<w> 4096]`. Width and tier are independent
  axes there, so the 4 KiB tier has all four widths.
- `x86-kernel-bounds-check` emits the guard. Every check is unsigned, except the tail check's `jl`, and every one reaches a
  single `ud2` before memory is touched:
  1. `cmp length,maximum; ja`;
  2. `test base,base; jz`;
  3. `cmp index,length; jae`;
  4. for width > 1, `length - index < width; jl`;
  5. for width > 1, the alignment check, last.
- `unaligned-accesses` exempts only `[kernel-load-u32 512]` and `[kernel-store-u32 512]` from alignment. The 4 KiB u32
  forms are therefore aligned.
- `x86-store-answer`: a store answers its operand, untruncated.
- `:fence-load` / `:fence-store` / `:fence-full` encode `0f ae e8` (lfence), `0f ae f8` (sfence) and `0f ae f0` (mfence).
  Each answers 0.

The committed kotoba-compiler/1 objects confirm what was actually emitted (`objdump -d` of
`lib/kotoba.aiueos/os/aiueos/kotoba/*.o` at kotoba 455b84fb):

- **u8 4 KiB loads** (x25519.o, ecdsa-p256.o): `cmp r,0x1000; ja T; test base; je T; cmp index,length; jae T; movzbl;
  jmp; T: ud2`.
- **The u32 4 KiB store** (rtl8125-program.o 0x4f2): the same, then `length - index`, `cmp 4; jl T`, `and index,3; test;
  ja T`, then `movl`.
- **sfence** (rtl8125-program.o 0x4da) and **lfence** (rtl8125-rx-poll.o 0x300): each is followed by `mov r10d,0`, the
  zero answer.
- **4 KiB windows** appear in 13 of the 161 committed objects.

## Decision

Two new blocks follow the port-input block. Each is appended, with every earlier block so the ids stay positional, only
to a source that names one of its stubs.

- **ids 35..42:** `kernel-load-u8-4k`, `kernel-store-u8-4k`, `kernel-load-u16-4k`, `kernel-store-u16-4k`,
  `kernel-load-u32-4k`, `kernel-store-u32-4k`, `kernel-load-u64-4k`, `kernel-store-u64-4k`.
  - **Code:** the memwidth window of the 16 KiB block, with `cmp rcx,4096`. The checks run in the reference's order, and
    every branch is a rel32 to the one `ud2`. All four widths, including u32, check alignment above one byte. A store
    leaves its value in rax.
  - **The window rules are those of every window access:**
    - the base is a rooted region, and the length is that region's own: the owner's length parameter, or the literal
      extent of an array or subregion (E7106);
    - a literal length above 4096 is refused at compile time (E7108, which now names the tier maximum per raw tier:
      512 / 4096 / 16384);
    - a run-time length above 4096 reaches `ud2`, as in the reference.
- **ids 43..45:** `kernel-fence-load`, `kernel-fence-store`, `kernel-fence-full`. These are `lfence`, `sfence` and
  `mfence`, each followed by `xor eax,eax`. They take no operand, so no window rule applies. A call with an argument is
  E2103, like any wrong-arity call of the stubs.

Objects that name neither block keep their bytes. The gates pin these object digests to main's root output:
- the 512-byte width object (`a8ac4f07`);
- the 16 KiB width object (`63c0486c`);
- the out-port object, which carries ids 0..34 (`6377fce8`).

## Gates

`check-aiueos-object-windows4k.py` (Mac fixed point) checks:
- **eight-4k:** the eight accesses decode in order with bound 4096. Every branch lands on the ud2, and no 512-byte or
  16 KiB window is present. The digest is pinned.
- **mixed:** 512-byte, 4 KiB and 16 KiB u8 loads in one object each keep their own bound.
- **opt-in:** the three objects above are byte-identical.
- **tier maximum:** over the object's own `.bss` / `.high_bss` array, length 4096 compiles, and 8192 is refused with E7108
  naming the intrinsic and the maximum 4096. This holds for all eight forms.
- **refused, nothing written:**
  - an unrooted base, a computed length (`(+ n 4)`, `(quot n 2)`), a free literal length and a base read from memory
    (E7106);
  - each form with one argument too few and one too many (E2103).

`check-aiueos-object-fence.py` checks:
- `fl` / `fs` / `ff` carry lfence, sfence and mfence (each with `xor eax,eax`), once each and in that order.
- **A driver shape:** store, sfence, doorbell store; load, lfence, load. Each fence lies between its two 4 KiB accesses.
- **opt-in:** the 4 KiB object and the three objects above carry no `0f ae` and keep their digests.
- Each fence called with an argument is refused (E2103).

Negative controls:
- Both gates are red on main's root (`E2101 unknown or unsupported form 'kernel-load-u8-4k'` / `'kernel-fence-load'`).
- Three mutant compilers built from this source are each caught:
  - bound 8192: the 4k gate finds no 4096 window;
  - the u32 forms without tail and alignment checks: caught by both decoders;
  - lfence and sfence swapped: caught by the fence order check and the driver check.

`docs/evidence/windows4k-fence-20261031/` ran the objects under QEMU by hand, against a C model of the reference guard.

## Not decided here

- **The 64 KiB tier** (`kernel-<op>-<w>-64k`, `[... 65536]` in the reference). sha256 needs it (`kernel-load-u8-64k`). It
  is also blocked separately by a ten-parameter helper. The block would be this one with `cmp rcx,65536` and raw tier 3.
  It is not added until an object can use it.
- **The 16 KiB u32 store**, which ADR 0386 left out. It is still absent; the 4 KiB tier has both u32 forms.
- No change to the locked-project route. seed/86 already supplies all 32 width/tier stubs there.
