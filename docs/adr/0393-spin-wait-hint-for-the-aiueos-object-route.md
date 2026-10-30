# ADR-0393 -- the aiueos object route's spin-wait hint (JUN-633 slice 5)

- Status: **implemented** (seed/74, `scripts/seed/check-aiueos-object-pause.py`).
- Date: 2026-10-31
- Tracking: JUN-633 (slice 5).
- Follows: ADR 0392.

## Context

AIUEOS's virtio block driver polls its used ring. With MSI-X active it halts between two reads, and kotoba-lang/kotoba
#1073 does that through ADR 0392's `kernel-wait-interrupt`. Without MSI-X it spins, running `pause` between two reads.
A Kotoba object for that wait can only drop the hint, which changes the loop's behaviour on the CPU, unless the route
can emit it.

## Decision

Id 29 is `kernel-pause []`. It emits `pause; xor eax,eax` and returns 0. `pause` changes no architectural state. It
takes no argument, and with one the call is refused (E2103).

It is a block of its own, appended after the halt block, so the ids stay positional, and only to a source that names
it. An object that names only `kernel-wait-interrupt` keeps the bytes it had under ADR 0392.

## Evidence

- `scripts/seed/check-aiueos-object-pause.py`:
  - finds `pause; xor eax,eax` exactly once in a one-pause object;
  - checks that the halt gate's wait object carries no pause and keeps its slice-4 SHA-256 (83d8375a...);
  - checks that the width object is unchanged and refuses an argument (E2103);
  - is wired into mac-selfhost-aiueos.yml.
- `docs/evidence/pause-intrinsic-20261031/`: 100000 calls under QEMU, each returning 0 with IF unchanged.
- The halt, xstate, f32 and cpu gates pass on this root, and kotoba's virtq-wait object recompiles byte-identical.
