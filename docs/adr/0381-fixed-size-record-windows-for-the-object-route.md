# ADR-0381 -- the aiueos object route gains fixed-size record windows (JUN-556 D5)

- Status: **implemented** in the PR that revises this text (seed/74, `check-aiueos-object-records.py`). The first version
  proposed a parameter-name suffix; reading seed/74 showed the route carries constants in the NAMES OF STUB FUNCTIONS
  (cell-load-<k>, mmio-load32-<addr>), not in parameter names, so D5 follows that pattern. The revised decision is below.
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

### D5 -- private record-load / record-store stubs that carry the offset and the record size

A private function `record-load-<w>-<off>-<N> [b]` or `record-store-<w>-<off>-<N> [b v]` (body the placeholder 0, as for
`cell-*` and `mmio-*`) is a record access: `w` is `u8 u16 u32 u64`; `off` and `N` are canonical decimals (at most three
digits, no leading zero); `N` is a multiple of 4 in 8..256; `off` is a multiple of the width; `off + width <= N`. Anything
else is refused at admission (E7102). The call site becomes
`mov rdx,[b]; (mov rax,[v];) test rdx,rdx; jz ud2; <access [rdx+off32]>; jmp +2; ud2`: no run-time bound, because `off`
and `N` are literals checked at compile time; a null `b` traps. The object gets no relocation, symbol or data.

Admission (E7106 otherwise), in `xk-check`:

* the base argument is an unassigned parameter of an **exported** function (resolved through `xk-src`, so a let-bound copy
  is fine; a literal, arithmetic, a value read from memory or a private helper's parameter is not);
* every record access to that parameter in the function names the same `N`;
* that parameter is not also the base of a window access in the function.

The stubs exist only in sources that declare them, so objects that do not use records are byte-identical to before (the
exports, windows, externs, cells, mmio and globals gates, and the Kotoba apic object, are unchanged).

### What this does and does not guarantee

It guarantees that the Kotoba code never touches a byte outside `[ptr, ptr+N)`. It does **not**
guarantee that the caller's pointer really has N bytes: that remains the C caller's contract,
exactly as `length` is trusted in the window case. The `-<N>` in every access name makes the contract
explicit in the source and lets a reviewer compare it with the C struct size; the consistency rule keeps one parameter
from being used with two sizes.

### Gate (must exist before the seed change merges)

`scripts/seed/check-aiueos-object-records.py`, run on the Mac fixed point like the exports/windows/
externs/cells/mmio/globals gates:

* positive: a function filling a 40-byte record at the offsets of `struct aiueos_device_worker_poll` and reading it back;
  the `.text` bytes are checked one instruction at a time against the expected encodings;
* refused (E7106, no output): non-literal index; `off + width > N`; misaligned `off`; `N` not a
  multiple of 4 or outside 8..256; record base reassigned; record base used in arithmetic or
  passed to a call; record accessor on a window base; window accessor on a record base; the image route;
* the existing gates' digests (one export, two exports, windows, externs, cells, globals, mmio)
  are unchanged, because the family is added only when the source uses it
  (the stubs are declared by the source, like `cell-*` and `mmio-*`).

### Pin impact

The change to `seed/74` re-derived the Mac root, the Linux roots, the CLI image and the
`native-product.json` source revision, as amu#1680 did. It lands as one PR with the two-phase
adoption, and a follow-up sourceRevision PR after the squash.

### Consumer

Once D5 exists, `device_worker_protocol.c` can be written as a Kotoba export taking
`(http, length, poll)`, with `record-store-*-<off>-40` accesses on `poll`, and calling the existing parse object through a D1 extern; the
differential check is the QEMU harness pattern of `scripts/apic-x86-smoke` (C and Kotoba objects
run on the same input, outputs diffed, with a negative control), plus `smoke-qemu-uefi.sh`.

## Non-goals

* No pointers into records, no records inside records, no variable offsets (a later ADR if a
  consumer needs them).
* No change to the 5-argument limit (JUN-556 E), port I/O, run-time-base MMIO, or `.S` files.
* No claim about how many C files D5 unblocks: the regex pass of ADR 0380 cannot tell a struct
  output from a buffer. The count comes from reading each candidate, starting with
  `device_worker_protocol.c`.

## Open questions for the owner (answered by the implementation, open to change)

1. Is the size carried in the access names (`-<N>`), with a per-parameter consistency check, acceptable? It follows the
   cell/mmio pattern; a parameter-name suffix would need parameter names carried into seed/74.
2. `N` is capped at 256; the window route's 512-byte frame would also fit.
3. D5 landed before E (7+ arguments), because the small C files stop at D5 first.
