# tools/c/sm70 -- the SM 7.0 / 7.2 instruction encoder (route C, JUN-713)

Route C (ADR 0375, JUN-701) runs kernels that Amu compiles to the GPU's own ISA, with no vendor user-space code.
Xavier's iGPU (gv11b) is Volta, SM 7.2. This directory holds the first stage: a Kotoba encoder that produces the
128-bit SM70 instruction words, control/scheduling bits included, for a starter set. Nothing here runs on a GPU;
launching these words on Xavier is JUN-714 (C4), and lowering KIR v2 to them is a later issue.

| File | What it holds |
|---|---|
| `sm70_encode.kotoba` | the encoder: a program vector, the guard predicate, the control bits, and emitters for NOP, EXIT, BRA, MOV (register, immediate), S2R, IADD3, IMAD, FADD, FMUL, FFMA (register and immediate forms), LDG and STG (global, `.E`), each refusing out-of-range operands by code |
| `sm70_encode_test.kotoba` | the cases: one line per encoded word or refusal, and a 12-instruction kernel-shaped sequence |

Layout: an instruction is two i64 halves, `lo` = bits 0..63 and `hi` = bits 64..127; the encoder writes fields by
their 128-bit bit numbers, as the reference does. The control word occupies bits 105..125: stall 105..108, yield
109, write barrier 110..112, read barrier 113..115 (7 = none), wait mask 116..121, reuse 122..125. Registers are
R0..R254 and RZ = 255; predicates P0..P6 and PT = 7. Not covered yet: source modifiers (neg/abs), constant-bank
and uniform operands, 64-bit IMAD.WIDE / IADD3.X, compares and SETP, shared/local memory, barriers and
convergence (BSSY/BSYNC). A scheduler that chooses the control bits is a later step; callers pass them.

## Reference

There is no NVIDIA ISA specification. The layouts are transcribed from Mesa NAK, revision
`fd8ef2befafd01190e33f12dbfd109b924c8ebc3` (main, fetched 2026-10-31):

| File | SHA-256 |
|---|---|
| `src/nouveau/compiler/nak/sm70_encode.rs` | `cd45b5d3690316da9b991a5e5919c68833ab54ea04575c9f14cab41ea6784cd0` |
| `src/nouveau/compiler/nak/sm70.rs` | `49a9ea75eff9ceabf457a45a914769f13229155183bb647507e38c43c4313080` |
| `src/nouveau/compiler/nak_private.h` (special-register numbers) | `6a4654372c24e0ca2a103b429c11babedef6ce21cc75731339a28e61ce83736a` |

SM 7.2 is below NAK's `has_ugpr` (`sm >= 73`): LDG/STG use opcodes 0x381/0x386 with the `.E` bit at 72 and no
uniform register, and NAK writes no predicate source for LDG there. NAK's own tests (`hw_tests.rs` on hardware,
`nvdisasm_tests.rs` against NVIDIA's disassembler) hold no instruction words, so the expected words are derived
from the encoder source.

## Check

`python3 scripts/seed/check-sm70-encode.py [--receipt FILE]` (Mac arm64, through `bin/amu`; no GPU, about 7 s):

* the unit (the test's ns line, the encoder without its ns form, the rest of the test) runs; every word equals
  the script's own encoding of the same case, transcribed separately from NAK, bit for bit, and every refusal
  names the expected code;
* four words (NOP, EXIT, the self-branch, S2R TID.X) also equal recalled published cuobjdump listings: a
  cross-check of the NAK reading, not an authoritative reference;
* negative controls: one flipped bit in one expected word is reported for that case alone (three cases), and
  seven built mutants of the encoder (an opcode, the branch split, the LDG offset field, a control-bit shift, the
  memory scope, an offset bound, the guard field) each compile, run and are detected.

The Python oracle and the Kotoba encoder are two readings of the same source by the same author; a shared
misreading would pass. Execution on Xavier (JUN-714) is the independent test.
