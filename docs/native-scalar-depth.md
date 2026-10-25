# Native scalar regions for deep EVM frames

AWAI-81's native frame manager exposed the AArch64 runtime's previous
256-level scalar-region bound on official 1,024-deep CALL fixtures. The
AArch64 Linux static/packed candidate now reserves 4,096 marks (256 KiB)
and refuses the next entry with `budget/scope-depth` before changing a mark
or counter. The five saved counters, LIFO validation and scalar-only result
contract are retained. No reference may escape a released region.

[The native receipt](evidence/awai81-scalar-depth-20261025/receipt.json) pins
the exact 31 `seed/FULL-MANIFEST` modules. The preceding admitted candidate
builds a transition compiler, which packages the new runtime. That candidate
then rebuilds itself twice: F1 = F2 = F3, including the native image bytes
(SHA256 `ea15b258f2b2dffd72e7aeaade0410c69c4e5d2be314e30ee7ce375449242642`).
The compiler payloads also agree. This uses the ordinary manifest assembly;
no compiler module is dropped or semantically rewritten.

The canonical `test/native/amu/test/scalar_depth_gate.kotoba` executes depth
257 and 4,096, and checks the named refusal at 4,097, with an 8 MiB native
stack. Kotoba VM independently runs the formerly failing official deep-CALL
case with this runtime. These are correctness and boundary results; they
are not measurements of peak memory, throughput or arbitrary EVM workloads.

The x86 runtime retains its separately bounded 256-level profile. This
AArch64 candidate does not qualify deep EVM execution on x86, change public
release selection, or complete the native CI/controller and whole API gates.
The historical 256/257 receipts in the source-lock documentation remain
historical evidence for their recorded artifacts.

## AWAI-81 AArch64 string-pool follow-on

The bounded Paris full-state candidate needs more cumulative string allocation
than the previous 256 MiB AArch64 static runtime. The AArch64 pool is now
1 GiB; the x86 pool and AArch64 vector-item limit remain unchanged. The
[follow-on receipt](evidence/awai81-aarch64-pool-20261025/receipt.json)
pins all 31 manifest modules and an exact source concatenation. Its selfhost
payloads agree at R1 = R2 = R3, and its packed compiler images agree at
R2 = R3 (SHA-256
`567e56c6400ca9f2f64577c10f18c0bde4f327784a52fbc3490f87537128f7cb`).
R2 packs the Kotoba VM v39 Paris full-state driver byte-for-byte identically
to the exploratory 1 GiB compiler. Selected native VM resource, transaction,
state-root and durable-store results belong to Kotoba VM
[#26](https://github.com/kotoba-lang/kotoba-vm/pull/26).

This is an AArch64 candidate resource bound, not a claim that the full Paris
corpus, all allocation patterns, x86 execution, or public release is qualified.
