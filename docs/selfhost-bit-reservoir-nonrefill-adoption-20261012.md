# Native selfhost: historical nonrefill bit-reservoir pickup

Parent: `d3dc0ffb7efb079380c4859ba6c8734834304ddf`.

Recovered a bit-reservoir optimization that previously showed a 3.71% local
PicoJPEG improvement but was not adopted. The historical version cached payload
and descriptor information across publication. This version retains the original
read order and rechecks the descriptor and rereads bits after publication; no
observer-exclusion premise is needed. Historical timing is not reused.

The rule matches an exact typed68-row one-vector-to-vector owner with three
separate constant fields. For nonrefill counts1..8, it emits a guarded native
prefix. Each writer retains its private2+2+1 fuel cuts, partial-store behavior,
zero-fuel publication and trap, and successful store/publication ordering.
Context fuel is reloaded after publication. Full unsigned address/span guards
run before additional effects. Refill, unsupported shapes and invalid spans
retain the original cold body. Matching does not use workload or function names.

## One-point local comparison

Original PicoJPEG workload, n=32 and64 calls; one C/OFF/ON trio.
BATCH_ABI_RESET_VALIDATION_V1 includes reset and validation.

| Arm | Microseconds per original body |
| --- | ---: |
| C reference | 21.18 |
| Current parent | 125.93 |
| Candidate | 120.39 |

Observed time reduction:4.4001%; candidate/C:5.6832. This is an unconfirmed
exploratory point, not an official Embench score or a repeatable speedup claim.
No precision repeats. C-or-better remains unmet.

## Qualification

- Parsed controls include103 refusals and268 traces: full64-bit payloads,
  fuel0..6 and high unsigned fuel, ordered partial stores, observer mutations,
  invalid descriptors and wrapping addresses. Existing helper bodies remain exact.
- Whole-machine validation maps the actual133-word prefix, all retained control
  targets, literal pool and export offsets. Code grows532 bytes plus4 alignment
  bytes; PicoJPEG native52484 to53020 bytes. The original cold body is retained.
- Whole G2/G3/G4 native and KSEED containers are byte-identical.
- Original19 compile/extract38 completed. Only PicoJPEG changed; the other18
  source/native/container/all-export sets remain exact.
- Five fresh PicoJPEG profiles0/1/2/17/32 match result, fuel and all17 arena
  counters. Ninety previous profiles are reused through whole-image identity
  and raw-receipt replay. Selected95 is qualified; all95 were not rerun.
- Independent SOURCE, whole-machine, fixed-point, original19 and final95 reviews
  passed. Bootstrap boundary and binaries remain exact; normal Git hooks used.
  No network operations or additional timing.
- A previous V2 attempt attached the vector emitter in the boolean FV matcher
  and failed native compilation with E2104. Its stopped failure is preserved.
  The corrected source wraps the complete vector-returning gn-ins-quiet OP-FUEL
  arm and leaves the FV matcher unchanged. Unexecuted SOURCE drafts are retained.
- The short7 capsule's registered SOURCE/GO/runtime status strings retain a V1
  suffix; exact matching labels and actual source ancestry were checked. Its V3
  namespace and proofs identify the executed candidate. FP6/original38 use V4.

Evidence root: `/Users/junkawasaki/github/workspaces/codex/current-bit-reservoir-nonrefill-adoption-root-v3-20261012`.
Selected95 SHA256: `61519a2e9ee91ba4f4193e8a98ee30f7c66267266668800e8a6096388f3ecb55`.
Compiler native SHA256: `6e8370533f36711844810d5f53a3c2a70c782cb35469292320d756896e5f2990`.
Final independent review SHA256: `4db3bea3da26d81ebc0cc157263a3a8585add3643c8494f8dd7fdf33472918ad`.
Compiler container SHA256: `761558ef0896deabbdb4a5d6df5671bd4d2ca53d52bfd36268398b1a7d54c392`.

ADR0357 exception: this novel semantic lowering has no applicable AST refactor
rule. It is not mechanical refactoring; parsed controls and native translation
validation qualify the handedit. Only source41 and this document change.
