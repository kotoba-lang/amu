# ADR-0382 -- the aiueos object route can hand out the address of a data cell (JUN-556 D6)

- Status: **implemented** (seed/74, `scripts/seed/check-aiueos-object-celladdr.py`).
- Date: 2026-10-29
- Tracking: JUN-556, JUN-551.
- Follows: ADR 0380 (D1 externs, D3 cells), ADR 0381 (D5 records).

## Context

Two of the small C files that remain in `build-uefi.sh` cannot be written on the object route because they give an
extern function somewhere to write:

* `kernel/device_worker_protocol.c` keeps a `uint8_t out[32]` on the stack, passes it to
  `kotoba_aiueos_device_worker_poll_response(http, length, out)` and unpacks the 32-byte record into the caller's struct;
* `kernel/model_handoff.c` does the same with a 32-byte buffer for `kotoba_aiueos_model_mapping_plan`.

The object route has no stack arrays and no address-of. A D3 cell is eight named bytes in `.data` that Kotoba code can
load and store, but its address cannot be taken, so it cannot be passed to an extern (JUN-556, 2026-10-29).

## Decision

A private function `cell-addr-<k> []` (k canonical decimal below 64, body the placeholder 0) returns the **address of
cell k**: `lea rax,[rip+disp32]` with an `R_X86_64_PC32` relocation against the context symbol, addend `80 + 8k - 4`. That is
the relocation a cell access already has; only the instruction (`48 8d 05`) differs. The stub exists only in sources that
declare it, so other objects are byte-identical.

A scratch buffer is therefore `cell-addr-k` plus loads of the cells the callee writes: cells k, k+1, ... are contiguous in
`.data`, and `.data` holds exactly the cells some stub names. The author must load every cell the callee may write; the
extern's real write extent is the callee's contract and is not verified (as for every D1 extern).

The address is an ordinary value. It is not a rooted base, so a window access and a record access both refuse it (E7106);
the only thing it can do is be passed on, to an extern.

## Gate

`check-aiueos-object-celladdr.py` (Mac fixed point): the positive object has exactly one `lea rax,[rip+0]` whose
relocation is PC32 against the context with addend 84 for cell 1, and the two cell accesses keep 84 and 92; refused:
`k = 64`, a leading zero, a non-number, a parameter, a non-zero body (E7102), the address as a window base or as a record
base (E7106), the image route (E7102). It fails on the previous compiler.

## Consumer

`kernel/device_worker_protocol.c` as a Kotoba export `(http, length, poll)`: the 32-byte record is cells k..k+3
filled by the existing parse object through a D1 extern, and `poll` (40 bytes) is filled with D5 record stores. The verifier
in the kotoba repository must accept `lea rax,[rip+disp]` at cell relocation sites; that change lands with the consumer.

## Non-goals

No address arithmetic, no address of a record or of a window, no heap. A scratch region larger than 64 cells is not
possible; neither is a region that is not a whole number of cells.
