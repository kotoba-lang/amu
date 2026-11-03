# ADR-0385 -- the aiueos object route can hand out the address of a fixed-size .bss / .high_bss array (JUN-556 C)

- Status: **implemented** (seed/74, `scripts/seed/check-aiueos-object-arrays.py`).
- Date: 2026-10-30
- Tracking: JUN-556.
- Follows: ADR 0382 (cell addresses), ADR 0383 (extern calls with up to eight arguments), ADR 0384 (exports with up to eight parameters).

## Context

`kernel/tls_aes_gcm.c` is the next C file to move onto the object route. It needs two buffers that are too large
for cells, so ADR 0382 cannot provide them:

* a 1280-byte context in `.bss`, assembled with `memcpy` / `memset` and passed to `kotoba_aiueos_aes128_gcm`;
* a 1536-byte self-test scratch in `.high_bss`.

A cell region is limited to 64 cells (512 bytes), and it lives in `.data`. A 1.5 KiB zero buffer does not belong in the
file, and `.high_bss` is a separate placement in the kernel's `linker.ld`.

## Decision

A private function `bss-addr-<k>-<N> []` or `highbss-addr-<k>-<N> []` returns the **address of array k**: a zero-initialised
LOCAL buffer of N bytes in `.bss` or `.high_bss`.

* k is a single digit, 0..7.
* N is a canonical decimal and a multiple of 8, in 8..65536.
* The body is the placeholder 0.
* Every stub that names one (section, k) must name the same N; two sizes are refused (E7102).

The code is `lea rax,[rip+disp32]` with an `R_X86_64_PC32` relocation against the section's `STT_SECTION` symbol, addend
`offset - 4`. Arrays of one section lie in k order, each at a 16-byte aligned offset.

An object that names a stub gets, after the seven usual sections:

* `.bss` (index 7) and `.high_bss` (index 8): `SHT_NOBITS`, `SHF_WRITE|SHF_ALLOC`, align 16;
* two LOCAL section symbols right after the context symbol. `sh_info` and every global symbol index move up by two.

An object that names no stub is byte-identical to before.

The address is an ordinary value, as for ADR 0382:

* it is not a rooted base, so window and record accesses refuse it (E7106);
* it can only be passed on to an extern, whose real extent is the callee's contract and is not verified;
* the image route refuses the stubs (E7102).

## Gate

`check-aiueos-object-arrays.py` (Mac fixed point) checks:

* the positive object's section headers, section symbols, `sh_info` and global order;
* the three lea relocations (-4, 1276, -4) and the three PLT32 relocations to `memset`;
* that the one-export object stays byte-identical;
* nine malformed or inconsistent declarations (E7102), the address used as a window base or record base (E7106), and the image route (E7102).

It fails on the previous compiler, which emits no `.bss`.

A hand QEMU run linked the positive object with a C-convention harness: `bss-addr-1-24` = `.bss` + 0x500,
`.high_bss` separate, and a memset-then-sum over the arrays returned 0xc28ccc398 = 115608 + 52224 * 10^6.
The record is in `docs/evidence/bss-arrays-20261030/README.md`.

## Consumer

`kernel/tls_aes_gcm.c` as a Kotoba object. It assembles the context through externs `memcpy` / `memset` and calls
`kotoba_aiueos_aes128_gcm` and `kotoba_aiueos_aes128_gcm_selftest`. The verifier in the kotoba repository must accept the
`.bss` / `.high_bss` sections and their PC32 relocations; that change lands with the consumer.

## Non-goals

* No loads or stores into an array from Kotoba code, and no address arithmetic.
* No more than 8 arrays per section, no initialised arrays, and no alignment above 16.
