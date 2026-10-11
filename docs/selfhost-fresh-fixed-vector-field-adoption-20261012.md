# Native selfhost: historical fresh fixed-vector field pickup

Parent: `3be67455ce2b7db6edc0b5c3c8f4681f3e76d0a6`.

Recovered a fixed-vector field optimization previously left out after an
exploratory 1.3468% AHA-Mont64 improvement. The current implementation proves a
successful closed typed producer returns an allocated fixed vector (1..32
items), finds its nearest unchanged local binding, and proves a constant field
index is in range. It emits a direct field load while preserving the original
allocation, calls, fuel, arena, publication order and ordinary checked fallback.
Calls, writers, unknown operations and control boundaries refuse the shortcut.

## Current one-point local comparison

Original AHA-Mont64 workload, n=32 and 64 calls; one C/OFF/ON trio.
BATCH_ABI_RESET_VALIDATION_V1 includes reset and verification.

| Arm | ns per original body |
| --- | ---: |
| C reference | 1034.1796875 |
| Adopted parent | 1673.33984375 |
| Candidate | 1625.48828125 |

Time reduction: 2.859644%; candidate/C: 1.571766. This is one unconfirmed
exploratory point, not an official Embench score. The identity-weighted estimate
across19 is 0.152585%; the other18 programs were not timed again.
The C-or-better goal remains unmet.

## Qualification

- Whole G2/G3/G4 native and KSEED containers are byte-identical.
- All original19 targets compiled/extracted in38 closed calls.
- Only AHA-Mont64 changed:12 source-certified field loads, native3984 to3552
  bytes. The sole literal-address relocation is source-bound and audited.
- Five fresh profiles (0,1,2,17,32) match original result/fuel/17 arena counters.
- Ninety previous profiles are reused through exact source/native/container/
  all-export/profile identity. Selected95 is qualified; all95 were not rerun.
- Independent source, whole-machine, raw-output and final95 reviews passed.
- Bootstrap boundary/binaries are retained; normal Git hooks, no network,
  no precision repeats. Only source41 and this document are committed.

Evidence root: `/Users/junkawasaki/github/workspaces/codex/current-fresh-fixed-vector-field-adoption-root-v3-20261012`.
Selected95 SHA256: `56a4bea991fee67f094bc9e2bbb416979bf8c6b44acf4ccc034d11b94a8c2fca`.
Compiler native SHA256: `60f67b67756cb847a97ab701bd1b7411efb1124b35dba93502f69b37bf19c3c2`.
Final independent review SHA256: `43531a68cdda8e6a8419bdae22672f2706584094bd3cc36b44b9021d173e2b31`.

ADR0357 exception: this one-off semantic lowering implementation has no
applicable AST refactor rule. It is not a mechanical refactoring. Other15
compiler modules remain exact; parsed refusal controls and native translation
validation qualify the implementation.
