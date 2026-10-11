# Native selfhost: historical unsigned wide-product pickup

Parent: `d21ffc49f02ac8db59e998794330b7e26f07bd66`.

Recovered the standalone unsigned limb-product rule previously left out after
an exploratory 2.35849% AHA-Mont64 improvement. Its combined funnel-shift trial
regressed; this change qualifies the standalone rule on the current compiler,
without inheriting historical timing.

Match an exact typed73-row two-i64-to-vector limb decomposition. Capture both
inputs, emit wrapping MUL and unsigned UMULH, and write the original low/high
result homes. Replace only66 arithmetic rows; retain the original allocation,
ordered high/low payload stores, fuel, arena, traps, frame and return. No
workload or function-name dispatch. Current saved-home/spill, frame, live-table
and capacity guards retain the ordinary path for unsupported shapes.

## Current one-point local comparison

Original AHA-Mont64 workload, n=32 and64 calls; one C/OFF/ON trio.
BATCH_ABI_RESET_VALIDATION_V1 includes reset and verification.

| Arm | ns per original body |
| --- | ---: |
| C reference | 1080.078125 |
| Adopted parent | 1677.734375 |
| Candidate | 1676.7578125 |

Observed time reduction:0.058207%; candidate/C:1.552441. This tiny difference
is an unconfirmed exploratory point, not an official Embench score or a
statistically established speedup. No precision repeats. The small-gain
accumulation policy allows qualified local adoption; C-or-better remains unmet.

## Qualification

- Parsed324 refusals and4196 full64 cases check the actual limb SIR arithmetic
  and captured-input/output overlap. The algebra also bounds intermediate limb
  sums below2^64; source wrapping semantics preserve the full product halves.
- Actual arithmetic29 to6 instructions, −92 bytes;4 alignment bytes yield
  whole native3552 to3464. Original frame240/save10 and100-byte allocation/
  ordered-store/return suffix remain exact. All retained control targets,
  literal references, pool payload and exports map to the new image.
- Whole G2/G3/G4 native and KSEED containers are byte-identical.
- All original19 targets compiled/extracted in38 closed calls. Only AHA changed;
  other18 source/native/container/all-export sets remain exact. IVS/FV/PF and
  long-address lowering are retained; layout42 is unchanged.
- Five fresh original AHA profiles0/1/2/17/32 match result/fuel/all17 arena
  counters. Ninety previous profiles are reused only through whole-image
  identity and raw-receipt replay. Selected95 is qualified; all95 were not rerun.
- Independent source, whole-machine, raw-output, fixed-point and final95 peers
  passed. Bootstrap boundary and binaries remain exact; normal Git hooks,
  no network operations, no additional timing.
- FP6 preregistration retains unused donor ancestry metadata. Active guards
  bind the current parent and reviewed source; the independent receipt records
  this limitation. Fresh original38 metadata explicitly binds the current parent.

Evidence root: `/Users/junkawasaki/github/workspaces/codex/current-unsigned-wide-product-adoption-root-v3-20261012`.
Selected95 SHA256: `5bcf601b89a1d7c433612b9dd8341586a611eef057681e7f836985ebdff394b9`.
Compiler native SHA256: `8af63c85abc0f70172f3bb45f60d8b6f50cc3eb91fc626e659b1710be0f65b64`.
Final independent review SHA256: `c14b217de8f401391c5543af6c98891fb8081e83a2c2c8fd32c79a8036a5a126`.

ADR0357 exception: this one-off semantic arithmetic lowering has no applicable
AST refactor rule and is not mechanical refactoring. Only source41 and this
document change; parsed controls and native translation validation qualify it.
