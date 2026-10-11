# Native selfhost: immutable variable-step scan with physical home binding

Parent: `e2f2ed9c927bce7b4d30840462611c7b27a90d63`.

The earlier exact typed scan prototype did not activate because its saved
register guard expected19/20/21/22, while the actual logical homes were
20/21/22/19. Bind handle/base/length/current-index roles to four distinct saved
registers19..28, excluding scratch/context/fuel registers. Keep the exact typed
root49, classifier28 and endzero-reader17 closure and immutable extent guards.

After the original entry debit, a guarded ASCII loop reads code-backed string
bytes directly. Every original fuel debit, trap and publication remains; UTF8,
low fuel, invalid extent or unsupported inputs enter the original paid body
with the current index. The original frame, allocation and epilogue remain.

## Current one-point local comparison

Original SLRE workload, n=32 and64 calls; one C/OFF/ON trio.
BATCH_ABI_RESET_VALIDATION_V1 includes reset and verification.

| Arm | ns per original body |
| --- | ---: |
| C reference | 1713.8671875 |
| Adopted parent | 9284.66796875 |
| Candidate | 8686.03515625 |

Time reduction:6.447541%; candidate/C:5.068091. This is one unconfirmed
exploratory point, not an official Embench score. No timing repeats.
The C-or-better goal remains unmet.

## Qualification

- Parsed392 refusals and24,816 result/fuel/publication trace cases passed.
- Exact117-word native prefix468 bytes; whole image grows464 bytes after
  removing4 old zero-alignment bytes. Original paid prologue/body/frame/cold
  inputs preserved; all943 retained control targets and8 source-bound literal
  references mapped. All87 literal-pool bytes and all exports are preserved.
- Whole G2/G3/G4 native and KSEED containers are byte-identical.
- All original19 targets compiled/extracted in38 closed calls. Only SLRE
  changed; other18 source/native/container/all-export/profile sets are exact.
- Five fresh original profiles (0,1,2,17,32) match result/fuel/17 arena counters.
- Ninety previous profiles are reused through exact whole-image identity;
  selected95 is qualified, but all95 were not rerun.
- Independent source/machine/raw/final95 reviews passed. Bootstrap boundary
  and binaries remain unchanged. Normal Git hooks; no network operations.

Evidence root: `/Users/junkawasaki/github/workspaces/codex/current-immutable-variable-step-scan-physical-homes-adoption-root-v7-20261012`.
Selected95 SHA256: `66be48a1287000fcc0196f12685a519eb41b9709955650a21e2c3f072b8c952d`.
Compiler native SHA256: `4afc77275ae8bcefe2f0f1e9e4a5626886b4517d0f960e8fde79e94cb764fcc1`.
Final independent review SHA256: `e8d1e35d07ece4beba2b62763d939f7cc5695daf177152a414e5d782bffe3051`.

ADR0357 exception: this one-off semantic scan lowering has no applicable AST
refactor rule and is not mechanical refactoring. Other15 compiler modules remain exact. Previously adopted FV/PF and
long-address changes are retained.
