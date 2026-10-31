# tools/c/sm70 -- the SM 7.0 / 7.2 instruction encoder (route C, JUN-713)

Route C (ADR 0375, JUN-701) runs kernels that Amu compiles to the GPU's own ISA, with no vendor user-space code.
Xavier's iGPU (gv11b) is Volta, SM 7.2. This directory holds the first stage: a Kotoba encoder that produces the
128-bit SM70 instruction words, control/scheduling bits included, for a starter set. Nothing here runs on a GPU;
launching these words on Xavier is JUN-714 (C4). The lowering of a KIR v2 kernel and the scheduler that chooses the control bits (JUN-723) are described below, with the loops, shared memory and barriers that dot_rows needs (JUN-725).

| File | What it holds |
|---|---|
| `sm70_encode.kotoba` | the encoder: a program vector, the guard predicate, the control bits, and emitters for NOP, EXIT, BRA, MOV (register, immediate, constant bank), S2R, IADD3, IMAD, IMAD.WIDE (immediate), ISETP (registers), FADD, FMUL, FFMA (register and immediate forms), LDG and STG (global, `.E`), LDS and STS (shared), BAR.SYNC 0, BSSY and BSYNC (convergence barriers), SHF.R.HI (a 32-bit right shift by an immediate), each refusing out-of-range operands by code |
| `sm70_encode_test.kotoba` | the cases: one line per encoded word or refusal, and a 12-instruction kernel-shaped sequence |
| `sm70_sched.kotoba` | a machine IR in program order and the scheduler that fills in each instruction's stall, yield, write/read barrier and wait mask, then encodes the IR (JUN-723) |
| `sm70_lower.kotoba` | the lowering of a KIR v2 kernel's SPIR-V words to that IR (JUN-723) |
| `sm70_regalloc.kotoba` | the register and predicate allocator that maps the lowering's virtual registers to R0..R254 and P0..P6 (JUN-739) |
| `sm70_lower_modules.kotoba`, `sm70_lower_test.kotoba` | the two units of the lowering check: the KIR v2 modules, then their lowered words and two scheduler-only WAR cases |

Layout: an instruction is two i64 halves, `lo` = bits 0..63 and `hi` = bits 64..127; the encoder writes fields by
their 128-bit bit numbers, as the reference does. The control word occupies bits 105..125: stall 105..108, yield
109, write barrier 110..112, read barrier 113..115 (7 = none), wait mask 116..121, reuse 122..125. Registers are
R0..R254 and RZ = 255; predicates P0..P6 and PT = 7; convergence barriers B0..B15. The decode kernels (JUN-739)
added FADD and IADD3 with negated sources, FSETP (register and immediate), FMNMX, IMNMX, SEL (register and
immediate), MUFU (COS, SIN, EX2, LG2, RCP, RSQ, SQRT), I2F and F2I (32-bit), LOP3 (register and immediate), SHF
(register and immediate shift, every type), IMAD.WIDE with a register multiplier and SGXT. Not covered yet: abs
modifiers, constant-bank operands other than MOV's, uniform operands, IADD3.X, PLOP3 and the other SETP forms,
SHFL, PRMT, local memory, the other BAR forms (ARV, RED, a barrier number other than 0). The encoder's callers pass the control bits;
`sm70_sched.kotoba` chooses them for the lowering.

BAR.SYNC follows NAK, which writes the opcode 0xb1d and nothing else. The recalled CUDA listing word for
`BAR.SYNC 0x0` on sm_70 (`0x0000000000007b1d 0x000fec0000010000`) also has bit 80 set, which nvdisasm prints as
`.DEFER_BLOCKING`; NAK leaves it clear. The lowering runs every barrier in converged code (each loop is wrapped in
BSSY/BSYNC), as NAK does. Whether bit 80 matters on gv11b is for the run on Xavier (JUN-714).

## The lowering and the scheduler (JUN-723)

The kernels lowered are `kir2-ewise` from `tools/gpu_kernels_v2.kotoba` (z[i] = x[i] op y[i] for i < n, ADR 0372):
add and mul at LocalSize 256 and 64; and `kir2-dot-rows` (o[row] = sum over k of w[row cols + k] x[k], one
workgroup of 256 per row: a strided loop over k into a function variable, the partial sums in a shared array, a
tree reduction with barriers, thread 0 stores) (JUN-725). Ewise sub lowers since JUN-739 (FADD with a negated
source). The pass reads the module's SPIR-V words, not the KIR builder's calls, so it lowers what the Vulkan route
would load.

ewise add, LocalSize 256, is 22 instructions (the register numbers below are from before the allocator of JUN-739,
which packs them into R0..R13; `--receipt` has the current words):

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
dimension is ceil(n / LocalSize.x). Registers are allocated by `sm70_regalloc.kotoba` (JUN-739, below).

dot_rows is 72 instructions. Its launch: bindings 0 Meta {rows, cols : u32}, 1 W, 2 X, 3 O (f32); LocalSize 256;
grid.x = rows; 1024 bytes of shared memory (Workgroup arrays are laid out from byte 0 in declaration order). The
control flow:

* Function variables live in one register each; a store is a MOV into it, a load a MOV out of it. A constant
  operand is a MOV immediate where it is used, except 0, which is RZ.
* An if is predicated as for ewise; `if (row >= rows) return;` becomes `@P0 EXIT`. An if may not hold a loop, a
  branch or a barrier.
* A loop is `BSSY Bn, merge` before the header, the condition `@!P BRA merge` (the body falls through), the body,
  the continue block and `BRA header`, which lands after the BSSY; at the merge label `BSYNC Bn`. The threads of a
  warp leave the strided loop after different numbers of iterations (cols = 700: 3 or 2) and reconverge at BSYNC
  before the shared store and the barrier.
* OpControlBarrier (Workgroup execution and memory scope) is `BAR.SYNC 0` and a NOP, as NAK emits it.
* A Workgroup access chain is an IMAD of the index by 4 and LDS/STS with the array's byte offset as the immediate;
  a constant index is RZ plus its offset.

```
S2R R3, CTAID.X     S2R R4, TID.X     MOV R6/R7 c[0][0x160..]  LDG.E R8, [R6]   (rows)
ISETP.GE.U32 P0, R3, R8               @P0 EXIT
... LDG.E R12 (cols)  MOV R2, 0 (acc)  MOV R0, R4 (k)
BSSY B0, L36
L13: MOV R13, R0   ISETP.LT.U32 P1, R13, R12   @!P1 BRA L36
     ... W[row cols + k], X[k]: LDG, LDG; FMUL; FADD into R2; k += 256 (MOV R29, 256; IADD3)   BRA L13
L36: BSYNC B0      STS [R4 * 4], R2      BAR.SYNC 0   NOP
     st = 128      BSSY B1, L63
L44: st > 0 (ISETP.GT.U32 vs RZ)   @!P2 BRA L63
     ISETP.LT.U32 P3, t, st    @P3 LDS, LDS, FADD, STS    BAR.SYNC 0   NOP   SHF.R.U32.HI st >> 1   BRA L44
L63: BSYNC B1      ISETP.EQ.U32 P4, t, RZ   @P4 LDS R44, [RZ]   @P4 ... STG.E [O + row 4], R44   EXIT   BRA self
```

The scheduler keeps the order and follows NAK's Volta latency model (`sm70.rs`): a GPR result is readable 6 cycles
after issue and a predicate 13 cycles after; S2R, LDG, STG, LDS and STS take one of the six scoreboards for their
result, and a read scoreboard when an instruction that may run later overwrites one of their sources (after it in
program order, or before it inside a loop that a backward branch after it repeats); the consumer's wait mask names
the scoreboards it needs. NAK says these Volta numbers are guesses. The control-flow rules (`calc_instr_deps.rs`,
`ir.rs` at the same revision):

* a branch other than the trailing self-loop, and EXIT, waits on every scoreboard in use (NAK `add_barrier` for
  `is_branch`) and, beyond NAK, until every fixed-latency result is ready, so a branch target is entered with
  nothing pending and the straight-line state of the fall-through path is the only one to keep;
* BAR stalls 5 cycles before the next instruction (NAK `exec_latency`), and the NOP after it 2 (NAK inserts it after
  every instruction with an exec latency); BAR does not wait on the scoreboards: as in NAK, the barrier orders
  shared memory itself;
* yield is set on EXIT, as in the published EXIT word, and on BAR and BSYNC (NAK `needs_yield`); it is a hint, not a
  hazard.

A loop's back edge waits for its loads to finish each iteration: correct, not fast. Register reuse and keeping
loads in flight across the back edge are later work.

`python3 scripts/seed/check-sm70-lower.py [--receipt FILE]` (Mac arm64, through `bin/amu`; no GPU, about 60 s):

* two runs of the lowering give the same bytes; every word decodes into the supported subset and equals
  `check-sm70-encode.py`'s NAK encoding of its decoding;
* a host interpreter runs ewise add (both sizes) and mul over n = 1000, 256 and 1, one thread at a time, and every
  output equals the f64 reference rounded to f32. Inputs are 24-bit values, so add and mul are exact. The words
  past n stay untouched, no access leaves its buffer, and x and z cross a 4 GiB line. The interpreter also times
  issue by the control bits, with variable latencies spread pseudo-randomly. Any read before its write is ready,
  any write that lands under an earlier variable-latency read, and any out-of-order write fails the run;
* the interpreter runs dot_rows a workgroup at a time: each thread until BAR or EXIT, the barrier released at the
  latest arrival once every thread that has not exited waits at it. The cases are rows x cols = 3 x 700, 2 x 256,
  1 x 100, 2 x 1 and 1 x 1300, with positive and signed inputs, plus one workgroup past the rows that must exit
  at once. Every o[row] is within 1e-3 of the f64 reference relative to sum |w x| (the largest error is about
  2.5e-8), the words past the rows stay untouched and the inputs unchanged. Shared memory starts as a NaN, and a
  race check fails the run when, between two barriers, a thread reads or writes a word that another thread wrote,
  or writes a word that another read. BSSY must not be re-armed before its BSYNC, BSYNC must match the BSSY that
  armed it, every BSSY reconverges at a BSYNC on its barrier, and each BAR stalls 5, yields and is followed by a
  NOP of 2;
* the scheduler's WAR case and its loop WAR case (an STS source rewritten after the back edge) get exactly the
  expected control bits;
* negative controls: three corrupted control fields and one operand bit in the ewise words; in the dot_rows words,
  either BAR replaced by a NOP, the loop exit's condition not inverted, a 1-cycle stall before the back edge, the
  write barrier of an LDS dropped and a BSSY target bit; sixteen built mutants of the lowering (ewise: compare,
  binding and element strides, the guard, the operator, the global id, the member offset; dot_rows: the loop exit
  condition, the barrier, the shared stride and a constant shared offset, the loop header not moved past BSSY, no
  BSYNC, a lost variable store, the shift amount) and nine of the scheduler (no wait mask, no write barrier, no
  read barrier, a 5-cycle GPR latency, a 6-cycle predicate latency, no drain at branches, no back-edge read
  barrier, a 1-cycle BAR, no yield on BAR) are each detected. The read-barrier mutants only show in the WAR cases:
  neither kernel overwrites a source of a load while it can still be read.

The interpreter times issue by the same model the scheduler uses. So the check shows that the control bits keep
that model; it does not show that the model is Volta's. Execution on Xavier (JUN-714) is the independent test.

## The decode kernels of qwen2.5-0.5b q8_0 (JUN-739)

One decode token of Qwen2.5-0.5B-Instruct q8_0 (24 dense layers, hidden 896, 14 query and 2 KV heads of 64, FFN
4864, vocabulary 151936) runs these kernels, in the unfused f32 form of inference's generator
(`verify/native/gpu/gen_decode_tokens_guest.cljk` at kotoba-lang/inference `3e5da0d`: `emit-dense-layer!`,
`emit-lm-head!` and the token loop; layout table "radv", the f32 kernels that also ran this model on Xavier in its
tick 55). Every kernel is a KIR v2 module of `tools/gpu_kernels_v2.kotoba`:

| step | kernel | KIR v2 module | SPIR-V it needs beyond the earlier subset | here |
|---|---|---|---|---|
| token row | `embed_q8` (embed_iq4xs.comp -DQ8) | `(kir2-embed 8)` | BitFieldSExtract, ConvertSToF, the half scale (UnpackHalf2x16), SGreaterThanEqual | not yet |
| norms | `rmsnorm` | `(kir2-nex-op 1)` | InverseSqrt, FDiv, ConvertUToF, Select | **lowered, gated** |
| q, k, v, o, gate, up, down | `kdot_f32_r8` (wide) and `kdot_f32_r1` (narrow), Q8_0 arm | `(kir2-kdot-f32-r8 8)`, `(kir2-kdot-f32-r1)` | every tensor type's arm: vectors, OpDot, BitFieldSExtract, UnpackHalf2x16, Function arrays | not yet |
| q, k, v bias | `add_bias` | `(kir2-nex-op 11)` | UDiv by a register, ISub | **lowered, gated** |
| rope | `rope_neox` | `(kir2-nex-op 15)` | Pow, Sin, Cos, a select of booleans, a branch inside an if (continue) | not yet |
| KV cache write | `copy_at` | `(kir2-nex-op 8)` | FUnordNotEqual (the dynamic position) | **lowered, gated** |
| attention: score, softmax, weighted sum | `attn_decode` | `(kir2-nex-op 16)` | Exp, FMax, FOrdLessThan, FNegate, seven barriers, five loops | not yet |
| residual and norm | `add_rmsnorm` | `(kir2-nex-op 13)` | as rmsnorm | **lowered, gated** |
| SwiGLU | `silu_mul` | `(kir2-nex-op 4)` | Exp, FNegate, FDiv | **lowered, gated** |
| residual | `add` | `(kir2-nex-op 10)` | none | **lowered, gated** |
| final norm | `rmsnorm` | `(kir2-nex-op 1)` | as above | **lowered, gated** |
| lm head | `kdot_f32_r1` | `(kir2-kdot-f32-r1)` | as the matvecs | not yet |
| argmax | `argmax_partial`, `argmax_final` | `(kir2-nex-op 18)`, `(kir2-nex-op 19)` | LogicalAnd / LogicalOr (PLOP3), Bitcast | not yet |
| position | `pos_incr` | `(kir2-nex-op 14)` | none | **lowered, gated** |

The fused decode forms of the generator (`attn_copy_dense`, the h2 / int8 kdots) are speed variants of the same
arithmetic and are not needed for one token. nex_ops modules share their bindings: 0 Meta {n rows aux aux2 : u32,
eps scale p0 p1 : f32}, 1 a, 2 b, 3 c, 4 o, 5 s (f32), 6 ids (u32); LocalSize 256; grid.x per op as the generator
dispatches it (rows for the norms, ceil(n / 256) for the elementwise ops).

How the new SPIR-V lowers, following NAK (`from_nir.rs`, `builder.rs` at the same revision): exp(x) is MUFU.EX2 of
x log2 e; pow(x, y) is MUFU.EX2(MUFU.LG2(x) y); sin and cos are MUFU.SIN / COS of x / (2 pi); inversesqrt is
MUFU.RSQ; a / b is a times MUFU.RCP(b); FNegate is FADD -RZ, -x and FSub FADD a, -b; ISub is IADD3 a, -b, RZ; float compares
are FSETP (ordered or unordered as SPIR-V says); Select is SEL; FMax / FMin are FMNMX and UMin / UMax / SMin / SMax
IMNMX; shifts are SHF (left: SHF.L.W.S32, right: SHF.R.W.HI.U32); bitwise ops are LOP3; integer-float conversions
are I2F / F2I (toward zero). Unsigned division by a constant power of two is a shift; by a register it is
nir_lower_idiv's sequence (I2F, MUFU.RCP, a scale, F2I, one Newton step with IMAD.WIDE high words, two fix-ups) with
one deliberate change: the reciprocal is scaled by 2^32 - 2048 instead of nir's 2^32 - 512. nir's margin keeps the
quotient exact only while MUFU.RCP overshoots by less than about one unit in the last place; with 2048 it is exact
for a reciprocal up to three units off either way (checked over random and edge numerators and divisors with the
reciprocal moved by -6..+6 units: exact for -6..+3).

NAK counts MUFU, I2F and F2I as variable latency, so the scheduler gives them scoreboards like the loads; a SEL
waits for its predicate as a guard does.

**Register allocation** (`sm70_regalloc.kotoba`). The lowering gives out virtual GPRs from 256 and virtual
predicates from 8; the allocator computes liveness over the IR's control flow (a BRA's target, the fall-through, an
unguarded EXIT ends the thread; a guarded write does not end the old value), records interference where a node is
written while another is live after it (and between a variable-latency instruction's result and its sources, which
it still reads after issue), and colours nodes in order with the lowest free register; a register pair (LDG / STG
address, IMAD.WIDE result and addend) is one node on an even register. ewise now uses R0..R13, dot_rows R0..R19,
add_bias R0..R7 and the norms R0..R16. A module that needs more than R0..R254 or P0..P6 is refused (104). A
hand-written case (`rapred` in `sm70_lower_test.kotoba`) holds two predicates live at once; none of the kernels
lowered so far does.

The check (`check-sm70-lower.py`) runs each decode kernel in the host interpreter, a workgroup at a time, and
compares every word it may write with the f64 reference: exact for add, add_bias, copy_at and pos_incr (and the
residual add_rmsnorm stores); relative error at most 1e-3 for silu_mul, rmsnorm and add_rmsnorm. Every other word
of every buffer must keep its value. The interpreter models MUFU as the f64 function rounded to f32 and moved by a
pseudo-random 0..2 units in the last place, so the gates do not depend on correct rounding, which hardware does
not give. The cases use Qwen's widths (896, 128 the KV row) and odd ones (1, 7, 300, 1000, 1100).

Negative controls added with the decode kernels, each detected: in the emitted words, MUFU.RSQ turned into RCP
(rmsnorm), the division's fix-up compare inverted (add_bias) and the wait on a MUFU source dropped (silu_mul); built
mutants of the lowering (nir's 2^32 - 512 division margin, the reciprocal of the numerator, exp without log2 e,
inversesqrt as RCP, FNegate keeping the sign, ISub as IADD, unordered != as ==, ConvertUToF as F2I, Select's arms
swapped), of the scheduler (MUFU as fixed latency, SEL not waiting for its predicate) and of the allocator (no
interference, none between a variable-latency result and its sources, a guarded write ending a value, no back edge
in liveness, no predicate interference). `check-sm70-encode.py` checks the thirteen new emitters (36 words and 13
refusals) bit for bit against its NAK transcription, with thirteen more built mutants.

## Reference

There is no NVIDIA ISA specification. The layouts are transcribed from Mesa NAK, revision
`fd8ef2befafd01190e33f12dbfd109b924c8ebc3` (main, fetched 2026-10-31):

| File | SHA-256 |
|---|---|
| `src/nouveau/compiler/nak/sm70_encode.rs` | `cd45b5d3690316da9b991a5e5919c68833ab54ea04575c9f14cab41ea6784cd0` |
| `src/nouveau/compiler/nak/sm70.rs` | `49a9ea75eff9ceabf457a45a914769f13229155183bb647507e38c43c4313080` |
| `src/nouveau/compiler/nak_private.h` (special-register numbers) | `6a4654372c24e0ca2a103b429c11babedef6ce21cc75731339a28e61ce83736a` |
| `src/nouveau/compiler/nak/ir.rs` (latency classes, `is_branch`, `needs_yield`) | `396820e02a2920fa1389e4f1ddf79cfcdbfaa35f4209fc8afda02c17f938e53f` |
| `src/nouveau/compiler/nak/calc_instr_deps.rs` (branch waits, the NOP after BAR) | `d4dbdbf8e4d6837559ff46454af3f7c2cc22461489c8d0270dad99b18fbc2e22` |
| `src/nouveau/compiler/nak/builder.rs` (`shr` as SHF on sm >= 70) | `4e7376bfbafad5d70ba82f1d57faf4e9a48425f6a2516f03dd222c5e6d8c43e5` |

SM 7.2 is below NAK's `has_ugpr` (`sm >= 73`): LDG/STG use opcodes 0x381/0x386 with the `.E` bit at 72 and no
uniform register, and NAK writes no predicate source for LDG there; STS uses 0x388 (LDS is 0x984 on every SM). NAK's own tests (`hw_tests.rs` on hardware,
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
  sixteen built mutants of the encoder (opcodes of IADD3, IMAD.WIDE and LDS, the branch split, the LDG offset
  field, a control-bit shift, the memory scope, an offset bound, the guard field, the constant-bank offset, the
  ISETP compare, the STS data field, the BSSY target, the BSYNC barrier, the SHF type and .HI bit) each compile,
  run and are detected.

The Python oracle and the Kotoba encoder are two readings of the same source by the same author; a shared
misreading would pass. Execution on Xavier (JUN-714) is the independent test.
