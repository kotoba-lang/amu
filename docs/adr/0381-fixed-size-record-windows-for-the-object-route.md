# ADR-0381 -- the aiueos object route gains fixed-size record windows (JUN-556 D5)

- Status: **proposed**. Nothing here changes a seed, an artifact or a pin.
- Date: 2026-10-29
- Tracking: JUN-556, JUN-551.
- Follows: ADR 0373 (bounded kernel memory windows), ADR 0380 (D1-D4, implemented in amu#1662/#1680).

## Context

The object route's memory windows (ADR 0373) take a *rooted base* (a pointer parameter that
is never reassigned) plus a *paired length*, and bound every access by that length at run
time (E7106 refuses anything else). That fits `(buffer, length)` arguments. It cannot express
the other common C shape: an **output record** passed as a bare pointer whose size is a
property of the type, not of a second argument.

The smallest example is `kernel/device_worker_protocol.c` (40 lines):

    int aiueos_device_worker_poll_response(const uint8_t *http, uint32_t length,
                                           struct aiueos_device_worker_poll *poll);

`http`/`length` is a window pair. `poll` is a 40-byte struct (`u64 job_id; u64 control_id;
u32 bos_token; int ready, has_job, reboot_pxe, restart_runtime;`), written at constant offsets.
There is no length to pair it with, so today the function cannot be written on this route,
and the same holds for every file whose public functions fill a caller-owned struct.

After amu#1680 (D3/D3b/D4) and the Kotoba apic object (kotoba#1003) this is the first thing
that stops the next-smallest C files (JUN-556 comment of 2026-10-29).

## Decision (proposed)

### D5 -- a parameter declared as a record of N bytes

A parameter whose name ends in `-rec<N>` (decimal, 8 <= N <= 256, a multiple of 4) is a
**record pointer**: the caller promises it points at N writable bytes. Inside the function:

* it is rooted exactly like a window base (never reassigned, never the result of arithmetic);
* it may be used only by the record accessors `record-load-<w>` / `record-store-<w>`
  (`w` in `u8 u16 u32 u64`) with an index that is a **literal** constant `off` such that
  `off + width <= N` and `off` is a multiple of `width` -- checked at compile time, so no run-time
  bound and no extra instruction beyond `mov [base+off], value`;
* it may be compared with `0` (the C files test `!poll`), and may not be passed on, stored,
  or used in any other expression (E7106);
* a non-literal index, an out-of-range or misaligned offset, a second record accessor family
  on a window base (or the reverse), and any use of the name outside the accessors are refused
  with E7106 and nothing is written.

The object contains no new relocation, symbol or data: only the stores/loads in `.text`.
`verify-kotoba-kernel-object.py` needs no change (it does not inspect instruction bodies for
windows today; the gate decodes them, as `check-aiueos-object-windows.py` does).

### What this does and does not guarantee

It guarantees that the Kotoba code never touches a byte outside `[ptr, ptr+N)`. It does **not**
guarantee that the caller's pointer really has N bytes: that remains the C caller's contract,
exactly as `length` is trusted in the window case. The declaration `-rec40` makes the contract
explicit in the symbol's source and lets a reviewer compare it with the C struct size.

### Gate (must exist before the seed change merges)

`scripts/seed/check-aiueos-object-records.py`, run on the Mac fixed point like the exports/windows/
externs/cells/mmio/globals gates:

* positive: a function filling a 40-byte record at the offsets of `struct aiueos_device_worker_poll`;
  the `.text` bytes are decoded independently and every store is at `[reg+off]` with
  `off+width <= 40`;
* refused (E7106, no output): non-literal index; `off + width > N`; misaligned `off`; `N` not a
  multiple of 4 or outside 8..256; record base reassigned; record base used in arithmetic or
  passed to a call; record accessor on a window base; window accessor on a record base; the image route;
* the existing gates' digests (one export, two exports, windows, externs, cells, globals, mmio)
  are unchanged, because the family is added only when the source uses it
  (`xk-uses-records?`, the same rule `xk-uses-widths?` established in B).

### Pin impact

A change to `seed/74` re-derives the Mac root, the Linux roots, the CLI image and the
`native-product.json` source revision, as amu#1680 did. It lands as one PR with the two-phase
adoption, and a follow-up sourceRevision PR after the squash.

### Consumer

Once D5 exists, `device_worker_protocol.c` can be written as a Kotoba export taking
`(http, length, poll-rec40)` and calling the existing parse object through a D1 extern; the
differential check is the QEMU harness pattern of `scripts/apic-x86-smoke` (C and Kotoba objects
run on the same input, outputs diffed, with a negative control), plus `smoke-qemu-uefi.sh`.

## Non-goals

* No pointers into records, no records inside records, no variable offsets (a later ADR if a
  consumer needs them).
* No change to the 5-argument limit (JUN-556 E), port I/O, run-time-base MMIO, or `.S` files.
* No claim about how many C files D5 unblocks: the regex pass of ADR 0380 cannot tell a struct
  output from a buffer. The count comes from reading each candidate, starting with
  `device_worker_protocol.c`.

## Open questions for the owner

1. Is a parameter-name suffix (`-rec<N>`) acceptable, given that windows already use suffix names?
2. Should `N` be capped at 256, or follow the 512-byte frame of the window route?
3. D5 before E (7+ arguments)? This ADR assumes yes, because the small C files stop at D5 first.
