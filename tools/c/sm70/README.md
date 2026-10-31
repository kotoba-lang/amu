# tools/c/sm70 -- the SM 7.0 / 7.2 instruction encoder (route C, JUN-713)

Route C (ADR 0375, JUN-701) runs kernels that Amu compiles to the GPU's own ISA, with no vendor user-space code.
Xavier's iGPU (gv11b) is Volta, SM 7.2. This directory holds the first stage: a Kotoba encoder that produces the
128-bit SM70 instruction words, control/scheduling bits included, for a starter set. Nothing here runs on a GPU;
launching these words on Xavier is JUN-714 (C4). The lowering of a KIR v2 kernel and the scheduler that chooses the control bits (JUN-723) are described below.

| File | What it holds |
|---|---|
| `sm70_encode.kotoba` | the encoder: a program vector, the guard predicate, the control bits, and emitters for NOP, EXIT, BRA, MOV (register, immediate, constant bank), S2R, IADD3, IMAD, IMAD.WIDE (immediate), ISETP (registers), FADD, FMUL, FFMA (register and immediate forms), LDG and STG (global, `.E`), each refusing out-of-range operands by code |
| `sm70_encode_test.kotoba` | the cases: one line per encoded word or refusal, and a 12-instruction kernel-shaped sequence |
| `sm70_sched.kotoba` | a machine IR in program order and the scheduler that fills in each instruction's stall, yield, write/read barrier and wait mask, then encodes the IR (JUN-723) |
| `sm70_lower.kotoba` | the lowering of a KIR v2 kernel's SPIR-V words to that IR (JUN-723) |
| `sm70_lower_modules.kotoba`, `sm70_lower_test.kotoba` | the two units of the lowering check: the KIR v2 modules, then their lowered words and a scheduler-only WAR case |

Layout: an instruction is two i64 halves, `lo` = bits 0..63 and `hi` = bits 64..127; the encoder writes fields by
their 128-bit bit numbers, as the reference does. The control word occupies bits 105..125: stall 105..108, yield
109, write barrier 110..112, read barrier 113..115 (7 = none), wait mask 116..121, reuse 122..125. Registers are
R0..R254 and RZ = 255; predicates P0..P6 and PT = 7. Not covered yet: source modifiers (neg/abs), constant-bank
operands other than MOV's, uniform operands, IADD3.X, FSETP and the other SETP forms, shared/local memory, barriers and
convergence (BSSY/BSYNC). The encoder's callers pass the control bits; `sm70_sched.kotoba` chooses them for the lowering.

## The lowering and the scheduler (JUN-723)

The kernel lowered is `kir2-ewise` from `tools/gpu_kernels_v2.kotoba` (z[i] = x[i] op y[i] for i < n, ADR 0372),
the simplest KIR v2 kernel: add and mul at LocalSize 256 and 64. `kir2-dot-rows` is not in the subset yet (a
function-local variable, a loop, shared memory and barriers); it and ewise sub (no FADD negate modifier yet) are
refused by code. The pass reads the module's SPIR-V words, not the KIR builder's calls, so it lowers what the
Vulkan route would load.

ewise add, LocalSize 256, is 22 instructions:

```
S2R R0, SR_CTAID.X          S2R R1, SR_TID.X           IMAD R2, R0, 256, R1        (i)
MOV R4, c[0][0x178]         MOV R5, c[0][0x17c]        LDG.E R6, [R4]              (n)
ISETP.LT.U32 P0, R2, R6
@P0 MOV R8/R9 c[0][0x160..] @P0 IMAD.WIDE.U32 R8, R2, 4, R8   @P0 LDG.E R10, [R8]   (x[i])
@P0 ... R12/R13, R14 the same for y; @P0 FADD R15, R10, R14
@P0 MOV R16/R17 c[0][0x170..] @P0 IMAD.WIDE.U32 R16, R2, 4, R16  @P0 STG.E [R16], R15
EXIT                         BRA self
```

The launch interface is the lowering's assumption, for the launcher (JUN-714) to confirm or change: binding b's
64-bit device address is at `c[0][0x160 + 8 b]`, where CUDA puts kernel parameters on Volta, and the grid's x
dimension is ceil(n / LocalSize.x). Registers are not reused.

The scheduler keeps the order and follows NAK's Volta latency model (`sm70.rs`): a GPR result is readable 6 cycles
after issue and a predicate 13 cycles after; S2R, LDG and STG take one of the six scoreboards for their result,
and a read scoreboard when a later instruction overwrites one of their sources; the consumer's wait mask names
the scoreboards it needs. NAK says these Volta numbers are guesses. Yield is set on EXIT only, as in the published
EXIT word; it is a hint, not a hazard.

`python3 scripts/seed/check-sm70-lower.py [--receipt FILE]` (Mac arm64, through `bin/amu`; no GPU, about 40 s):

* two runs of the lowering give the same bytes; every word decodes into the supported subset and equals
  `check-sm70-encode.py`'s NAK encoding of its decoding;
* a host interpreter runs ewise add (both sizes) and mul over n = 1000, 256 and 1, one thread at a time, and every
  output equals the f64 reference rounded to f32. Inputs are 24-bit values, so add and mul are exact. The words
  past n stay untouched, no access leaves its buffer, and x and z cross a 4 GiB line. The interpreter also times
  issue by the control bits, with variable latencies spread pseudo-randomly. Any read before its write is ready,
  any write that lands under an earlier variable-latency read, and any out-of-order write fails the run;
* the scheduler's WAR case gets exactly the expected control bits;
* negative controls: three corrupted control fields and one operand bit in the emitted words, seven built mutants
  of the lowering (compare, binding and element strides, the guard, the operator, the global id, the member offset)
  and five of the scheduler (no wait mask, no write barrier, no read barrier, a 5-cycle GPR latency, a 6-cycle
  predicate latency) are each detected. The no-read-barrier mutant only shows in the WAR case: ewise never
  overwrites a source of a load.

The interpreter times issue by the same model the scheduler uses. So the check shows that the control bits keep
that model; it does not show that the model is Volta's. Execution on Xavier (JUN-714) is the independent test.

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
