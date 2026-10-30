# ADR-0392 -- the aiueos object route waits for an interrupt (JUN-633 slice 4)

- Status: **implemented** (seed/74, `scripts/seed/check-aiueos-object-halt.py`).
- Date: 2026-10-31
- Tracking: JUN-633 (slice 4).
- Follows: ADR 0389, 0390, 0391.

## Context

Every virtio driver in AIUEOS's `kernel/pci.c` waits for its device the same way. It loops a bounded number of times,
checks a used ring or an interrupt counter, and otherwise runs `sti; hlt; cli`. The JUN-598 work has moved the ring
operations into Kotoba objects (kotoba-lang/kotoba #1072), but the wait itself can't follow: the object route has no
instruction that halts.

## Decision

Id 28 follows the extended-state block: `kernel-wait-interrupt []`. It emits `sti; hlt; cli; xor eax,eax`:
- It waits, with interrupts enabled for exactly the halt, until the next interrupt has been taken.
- It returns 0 with interrupts disabled again.
- The `sti` interrupt shadow makes the `hlt` the first instruction an interrupt can land on, so an interrupt that was
  already pending before the wait is taken at the halt and not lost.

What the object can and cannot do:
- It takes no argument, and with an argument the call is refused (E2103).
- The interrupt handlers are the kernel's own; the object only waits.
- It can't change which interrupts are enabled, and it never leaves interrupts enabled on return.

**Opt-in block:** it is appended (after the earlier blocks, so the ids stay positional) only to a source that names
the stub. Objects that don't name it are byte-identical.

## Not in this slice

Using the wait in the drivers' wait loops is kotoba-lang/kotoba JUN-598 work.

## Evidence

- `scripts/seed/check-aiueos-object-halt.py`:
  - finds `sti; hlt; cli; xor eax,eax` exactly once in an object exporting one wait;
  - finds no `sti` / `hlt` / `cli` in an object that does not name the stub;
  - checks that the width object is unchanged and refuses an argument (E2103);
  - is wired into mac-selfhost-aiueos.yml.
- `docs/evidence/halt-intrinsic-20261031/` runs the wait under QEMU with the PIC remapped and a 100 Hz PIT. 20 of 20
  waits returned after exactly one tick, with RFLAGS.IF clear. An object that returns without waiting gets 0 of 20.
- The xstate, cpu, f32 and tier-maximum gates pass on this root.
- Six committed kotoba-lang/kotoba aiueos objects recompile byte-identical: virtq-ring, xstate-setup, cpu-reads,
  qwen35-select, virtio-caps, dns-answer.
