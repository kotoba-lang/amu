# Selfhost Statemate: complete workload, untimed evidence

The new `bench/embench/batch-ports/statemate.kotoba` preserves the pinned
upstream window-controller workload. It replaces no historical result or
simplified port. C-or-better performance remains unachieved; asher is offline,
and local correctness runs do not qualify as timing measurements.

The profile is Embench commit `09c2ed8c3b7008c95d08b038de4a3f6dc103ed70`,
`src/statemate/libstatemate.c` SHA-256
`389c4bae5caba79a6f9139e02bf5e61c92921a756ec01200d2d2f16dc1c4ccf5`.
The native selfhost-built Amu compiler is
`abcc1318957af7d3a09cfd66c06d17821b5cf47f4c47d02b5620e9e92a24f02e`.
Native `check` accepts the source, and native `compile` produces its AArch64
code. No nbb, Node or JVM is used for checking, compilation or execution.
Python/pycparser 2.23 and Clang preprocessing are bootstrap source-authoring
and C-oracle tools; the 97 PRODUCT inventory entries remain unchanged.

The source generator supports this hash-locked C AST, rejects unsupported
forms, and emits static typed continuation functions. It preserves all seven
controller functions, switch selection and fallthrough, nested early breaks,
conditionals and the stabilization loop. It does not interpret a state table.
Assignments narrow signed char/int values; unsigned long comparisons use
unsigned ordering over 64-bit representations. All 64 Bitlist elements and
105 scalar globals have explicit slots in the 169-element owned vector.
The batch retains state across bodies while clearing Bitlist and invoking
`init`, `interface`, and `FH_DU` in the original order. Its result uses the
original 64-bit-list and 19-scalar verification predicates.

Correctness evidence:

- 2,028 individual state values match C: time profiles 0, 1 and 2, four stages,
  and all 169 state slots. The unchanged C benchmark body also matches the
  staged C oracle for each profile.
- 169 additional state values from the actual Kotoba production body match C.
- 676 repeated-body final values match unchanged C after 1, 2, 17 and 32 bodies.
- Batches 0, 1, 2, 17 and 32 match the original C verifier; fuel 1 traps.
- Vector index 168 succeeds and 169 traps. Guards and arena limits are intact.
- Regeneration is byte-identical. Both generators refuse a changed upstream
  file even with Python assertions disabled.

These bounded profiles establish the recorded state comparisons, not a proof
for every input or arbitrary C program. The signed-width assumptions match
this AArch64 profile; arbitrary signed-overflow behavior is not claimed.
The C adapter includes upstream unchanged and snapshots its globals. The
Python tools are new algorithm authoring outside the product path; existing
AST refactor rules do not cover C-to-Kotoba algorithm generation.

Artifacts and replay are under `docs/evidence/coscientist-statemate-20261004/`.
The research archive contains source, native code, provenance, all state
comparisons, guards, generator receipts and C inputs. The measurement bundle
contains a fresh directory `coscientist-statemate-complete`, without results.
Place it beside the existing pinned `upstream`, `runner`, and `images/r6m`:

```sh
python3 measure-statemate-full.py coscientist-statemate-complete
python3 audit-statemate-repeats.py coscientist-statemate-complete
```

The timing harness refuses existing evidence, requires load <= 4, calibrates
32-body calls, uses one untimed warmup and 30 rotated samples per arm. It reports
C and Kotoba ns/body and their ratio. CPU-idle and formal native perfgate
qualification remain separate requirements; this is not an official Embench
score. No timing, hypothesis ranking or optimization promotion follows from
these correctness-only results.

Five adapted workloads still lack complete alternatives: picojpeg, qrduino,
sglib-combined, slre and wikisort. Next measure this and the already queued
complete workloads on asher, then rank compiler optimization hypotheses by
separated repeated measurements. Full-suite C-or-better remains the goal.
