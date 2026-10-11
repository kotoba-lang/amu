# Native selfhost: charged short-circuit affine reader

Parent: `f4d892da4795ccfc9917de6394c2926608478144`.

Remove helper call/frame traffic for an exact closed typed vector+i64-to-boolean
predicate. Match current IR and constants, with no workload or function-name
special case. Reuse the pure affine-index certificate; keep shared entry fuel
publication before the zero-ID branch and all memory reads. Zero ID returns false
without vector checks. Other IDs retain full64 wrapping arithmetic and the
original checked read and trap behavior. Ordinary caller preparation, result
handling, frames and fallback remain exact.

## One-point local comparison

Original SGlib combined workload, n=32 and64 calls; one C/OFF/ON trio.
BATCH_ABI_RESET_VALIDATION_V1 includes reset and validation.

| Arm | Microseconds per original body |
| --- | ---: |
| C reference | 8.61279 |
| Current parent | 45.83984 |
| Candidate | 45.43164 |

Observed time reduction:0.89050%; candidate/C:5.27490. This is an unconfirmed
exploratory point, not an official Embench score or a repeatable speedup claim.
Small positive points are retained; no precision repeats. C-or-better remains unmet.

## Qualification

- Parsed controls:96 refusal cases and832 full64/fuel/handle/payload cases,
  including zero-ID no-read and post-publication descriptor mutation.
- Whole-machine audit:seven exact30-word replacements, all retained code/control
  targets, original helper frame/fuel, literal pool and every export. Code grows
  812 bytes and drops4 old alignment bytes; native25964 to26772 bytes.
- Whole G2/G3/G4 native images and containers are byte-identical.
- Original19 compile/extract38 completed. Only SGlib changed; the other18
  source/native/container/all-export sets remain exact.
- Five fresh SGlib profiles0/1/2/17/32 match result, fuel and all17 arena
  counters. Ninety previous profiles are reused through whole-image identity
  and raw-receipt replay. Explicit selected95 is qualified; all95 were not rerun.
- Independent SOURCE, whole-machine, fixed-point, original19 and final95 reviews
  passed. Bootstrap boundary and binaries remain exact; normal Git hooks used.
  No network operations or additional timing.

Evidence root: `/Users/junkawasaki/github/workspaces/codex/current-charged-shortcircuit-affine-reader-adoption-root-v1-20261012`.

ADR0357 exception: this novel semantic lowering has no applicable AST refactor
rule. Parsed controls and native translation validation qualify the handedit.
Only source41 and this document change.
