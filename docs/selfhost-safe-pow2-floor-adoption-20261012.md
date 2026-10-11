# Native selfhost: historical safe power-of-two floor pickup

Parent: `757347dd05ca58e651fa1f01f38740b1cca70e73`.

Recovered a pure signed floor helper previously left out after an exploratory
3.0705% PicoJPEG improvement. The new implementation matches the exact typed
25-row helper and a literal positive power of two (shifts 1..62). It captures
that constant before ordinary call preparation, uses arithmetic shift only
for `x >= MIN + 2^shift`, and keeps the complete original helper call for the
overflow-sensitive interval. Call preparation, postlude, tail calls, fuel,
frame, context, arena and traps are preserved.

The explicit prerequisite changes local function-address lowering to a checked
PC-relative four-word sequence and validates its fixups in layout. This avoids
the old short ADR range wall during compiler growth. It is included in the
qualified source; the PicoJPEG subject has no such address expansions, so its
performance change is attributed to the two floor transfers, not that prerequisite.

## Current one-point local comparison

Metric: BATCH_ABI_RESET_VALIDATION_V1, reset and verification included.
Original workload, n=32 and 64 calls; one C/OFF/ON trio, no precision repeats.

| Arm | ns per original body |
| --- | ---: |
| C reference | 19265.13671875 |
| Adopted parent | 129504.39453125 |
| Candidate | 127248.046875 |

Candidate time reduction: 1.7422942784%; candidate/C: 6.6050944114.
This is one unconfirmed exploratory point, not an official Embench score.
The C-or-better goal remains unmet.

## Qualification

- Whole G2/G3/G4 native and KSEED containers are byte-identical.
- All original19 targets compiled/extracted in 38 closed calls.
- Only PicoJPEG changed (+48 bytes, two activated floor transfers). Other18
  whole native/container/source/export sets are identical to the parent.
- Five fresh Pico profiles (0,1,2,17,32) match original result/fuel/17 arena
  counters. Ninety prior profiles are reused only through whole-image identity;
  selected95 is qualified, but not all95 were rerun.
- Independent source, machine, raw-output and final95 reviews passed.
- Bootstrap boundary/binaries are retained. No network operations or timing repeats.

Evidence root: `/Users/junkawasaki/github/workspaces/codex/current-safe-pow2-floor-adoption-root-v2-20261012`.
Authoritative selected95 SHA256: `d14a54f7df260e12b5e1bd77a7fd0c3dc5aefe3551608077533024978a9421db`.
Compiler native SHA256: `54ab4f031da90bdc6848a97a339d49fd34a046d300dc277482d1534917434e8f`.
Final independent review SHA256: `fbc9b63f3811a0bcab8287846f161828e03fd474c7d6f27316d5e4c3704823bc`.

ADR0357 exception: this one-off semantic lowering/fixup implementation has no
applicable AST refactor rule. Existing call pipeline and other14 compiler
modules remain exact; parsed controls and native translation audits qualify it.
