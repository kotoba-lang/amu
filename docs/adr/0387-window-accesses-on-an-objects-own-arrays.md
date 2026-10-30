# ADR-0387 -- window accesses on the aiueos object route's own arrays (JUN-553)

- Status: **implemented** (seed/74 `xk-region`, `scripts/seed/check-aiueos-object-array-windows.py`).
- Date: 2026-10-30
- Owner decision: 2026-10-30, "Amu array windows", for porting `kernel/tls13.c`'s handshake.
- Tracking: JUN-553.
- Amends: ADR 0385, whose array address was "not a rooted base".

## Context

`kernel/tls13.c` still has its handshake in C: ClientHello, the HKDF key schedule, the ServerHello and certificate parsers,
and the state machine. It keeps that state in about twenty module-static buffers.

ADR 0385 gave an object its own `.bss` / `.high_bss` arrays, but only their address, for handing to an extern. Kotoba code
could not read or write them, so a stateful module like this could not be written.

## Decision

The result of an array stub `bss-addr-<k>-<N>` / `highbss-addr-<k>-<N>` is a **rooted base whose region is the array itself**,
with region length the literal N. Every existing window access then works on it, with its own unchanged checks: the
512-byte and 16 KiB tiers of u8/u16/u32/u64 loads and stores, and `kernel-subregion`. A window's length operand must be
the region's own length (ADR 0373), so:

- `(kernel-load-u8 (bss-addr-0-64) 64 i)` is admitted;
- `(kernel-load-u8 (bss-addr-0-64) n i)` with a parameter n is still refused (E7106), as ADR 0385's gate expects;
- so is a different literal, arithmetic on the address, and the address as a record base.

The change is in admission only (`xk-region`); code generation is unchanged. Consequences:

- every object that compiled before compiles to the same bytes;
- the runtime checks are the windows' own: an index at or past N traps (ud2) before the access.

## Gate

`check-aiueos-object-array-windows.py` (Mac fixed point):

- **positive:** a 64-byte `.bss` and a 4096-byte `.high_bss` array; 5 windows at the 512 tier and 2 at the 16 KiB tier; 7 array `lea` relocations;
- **refused (E7106):** a parameter length, a wrong literal, a record base, and arithmetic;
- **unchanged:** the pinned one-export object.

It fails on the previous compiler. `check-aiueos-object-arrays.py` still passes. `docs/evidence/array-windows-20261030/` ran the positive object under QEMU: zero-initialised, round-trips at both ends, subregion, 16 KiB tier, and #UD at index N.

## Non-goals

- No record (fixed-offset) access to an array.
- No address arithmetic.
- No array larger than 64 KiB (ADR 0385's bound).
