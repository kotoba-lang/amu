# ADR 0326: advance kotoba-native past the reentry parameter home

Status: accepted. Date: 2026-09-03.

## Context

Every Amu revision from `0df9d992` onward miscompiles
`os/aiueos/kotoba/aiueos/sha256.kotoba` for `x86_64-aiueos-kernel-v1`. The
object links, passes `verify-kotoba-kernel-object.py`, and traps with `#UD` the
first time the kernel calls it. aiueos ADR-0150 measured the symptom and bounded
the window to `9cf3a0ac..7e8f06d7` without naming a commit.

The bisect names it. `0df9d992` changes exactly one line — the kotoba-native pin
`3dab370e` -> `3162d868` — and the bad commit inside that range is kotoba-native
`da3b56b`, "Optimize x86 direct self reentry". The defect is not there either:
`da3b56b` also pinned kotoba-mir `3aea0acc`, which turns the direct-reentry
allocator path on for x86-64, and in that path a parameter's spill store was
spliced at the entry plan — before the `:mir/reentry` marker the recur edge jumps
back to. The store ran once; the body's reloads ran every iteration.

kotoba-mir ADR 0038 fixes it; kotoba-native ADR 0076 pins the fix.

## Decision

Advance `io.github.kotoba-lang/kotoba-native` from `24f43e21` to `d7105581`.

This is not a narrow pin move. `24f43e21` is the DEVICE-CLIENT pin from
2026-09-02, and `d7105581` is 8 streams later — it carries the RTL8125 driver
symbols, CR4/XSETBV, the store-result register fix, the 32/64-bit memory width
family, the boot literal pool, the writable scratch region, the slice-carrier
lowering, and the Q8_0/Q4_K/Q6_K dequant work. Every one of those was landed in
kotoba-native and left unpinned here.

It is taken as one advance rather than split because the alternative is a pin
that stays on a revision **known to produce an object that does not boot**, and
because the intermediate revisions were never measured against this repository's
suite either — splitting would produce a sequence of equally unmeasured pins,
not a safer one.

## Consequences

- `sha256.o` at this pin: 9,936 B, `a31e2bd5…`, and the static check for a
  parameter home stored outside its loop reports 0 findings while all 8
  body-label-form back edges are kept.
- Objects emitted by any self-tail function that spills a parameter change
  bytes. Every committed aiueos object was already going to change at any pin
  past `9cf3a0ac`; this makes the ones that change **correct** rather than
  merely different.
- `deps-lock.edn` is regenerated for the new closure.
- **What this does not do**: it does not attest or rebuild any aiueos object.
  That belongs to the aiueos attestation stream, whose blocker this removes.
