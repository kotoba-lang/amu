# x86-64 field descriptions — neutral extraction (re-disasm M4, KOT-45)

Status: PHASE 1 ONLY. This document is the neutral field-description table
extracted from the Intel 64 and IA-32 Architectures Software Developer's
Manual Volume 2 (instruction set reference) and Volume 1 chapter 2 (instruc-
tion format). Per KOT-45's two-person discipline, the decoder implementation
reads **this document only** — the SDM is not consulted again during
implementation, and no other disassembler's output, table or test vector is
used at any point (cleanroom rules, see re_disasm/README.md).

Test expectations must be hand-computed from the encodings described here.

## 1. Instruction byte sequence (64-bit mode)

    [legacy prefixes*] [REX] opcode(1-3B) [ModRM] [SIB] [disp] [imm]

- Prefix order is free except REX must be last (immediately before opcode).
- Not every instruction has ModRM/disp/imm; per-opcode rows below say which
  operands exist.

## 2. Legacy prefixes

    0xF0        LOCK (group 1)
    0xF2/0xF3   REPNE/REP (group 1)
    0x2E 0x36 0x3E 0x26 0x64 0x65   segment overrides (group 2)
    0x66        operand-size override (group 3)
    0x67        address-size override (group 4)

Decoder behaviour: consume greedily in a loop; count group-3 (0x66) since it
flips the default operand size 64 -> 16; group-4 flips address size.

## 3. REX prefix (0x40-0x4F), one byte, last before opcode

    bit 7-4 = 0100
    bit 3 W : 1 = 64-bit operand size
    bit 2 R : extends ModRM.reg to 4 bits
    bit 1 X : extends SIB.index to 4 bits
    bit 0 B : extends ModRM.rm / SIB.base / opcode-reg to 4 bits

W=0 with 0x66 -> 16-bit; W=0 without -> 32-bit. A bare 0x40-0x4F with no
other effect is still a REX (it silences the old INC/DEC one-byte opcodes).

## 4. ModRM (one byte)

    bits 7-6 mod : addressing mode / displacement size
    bits 5-3 reg : register operand or opcode extension
    bits 2-0 rm  : register or memory operand

64-bit mod/rm (rm combined with REX.B into r8..r15):

    mod=00 rm=000..100,110..111 : [r64]           (rm=101 = RIP+disp32, see 6)
    mod=00 rm=101               : RIP+disp32
    mod=01 rm=any               : [r64 + disp8]
    mod=10 rm=any               : [r64 + disp32]
    mod=11 rm=any               : register operand

rm=100 (with any mod except 11) means SIB follows.

## 5. SIB (one byte, follows ModRM when rm=100)

    bits 7-6 scale : 1/2/4/8
    bits 5-3 index : index register (REX.X extends; index=100 + REX.X=0 = no
                     index)
    bits 2-0 base  : base register (REX.B extends; base=101 with mod=00 =
                     no base, disp32 follows)

Effective address = [base] + [index]*scale + disp, each part optional per
above. mod=01/10 with base=101 means rbp/r13 base + the disp.

## 6. Displacement and immediate

    disp8  : sign-extended to 64
    disp32 : sign-extended to 64
    imm8   : sign-extended when the operand form says so (e.g. ALU group 0x83)
    imm16  : only under 0x66
    imm32  : sign-extended to 64 when moved into a 64-bit register
    imm64  : MOV r64, imm64 (opcode B8+r with REX.W)

RIP-relative (mod=00 rm=101): address = end-of-instruction + signext(disp32).
That is why the decoder must know the full instruction length.

## 7. Opcode map subset (the M4 core)

ALU block — opcodes 0x00 + op*8 + form, op = 0..7 selects the operation:

    op  0 ADD   1 OR    2 ADC   3 SBB   4 AND   5 SUB   6 XOR   7 CMP

    base+0 : op r/m8, r8          (ModRM)
    base+1 : op r/m, r            (ModRM; operand size 16/32/64)
    base+2 : op r8, r/m8          (ModRM)
    base+3 : op r, r/m            (ModRM)
    base+4 : op AL, imm8
    base+5 : op eAX, imm16/32

    (base 0x00, 0x08, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38)

Registers, 4-bit (REX extends 3-bit fields):

    0 AX/CX/DX/BX/SP/BP/SI/DI  8 R8..R15     (8-bit 0..3 = AL/CL/DL/BL,
                                               4..7 = SPL/BPL/SIL/DIL,
                                               REX.W -> 32-bit zero-extends
                                               to 64; no REX.W -> 32-bit)

Group 1 — immediate to r/m:

    0x80 : op r/m8, imm8      (ModRM.reg selects op 0..7 as above)
    0x81 : op r/m, imm16/32   (imm32 sign-extends in 64-bit)
    0x83 : op r/m, imm8       (imm8 sign-extended)

MOV family:

    0x88 : mov r/m8, r8       (ModRM)
    0x89 : mov r/m, r         (ModRM)
    0x8A : mov r8, r/m8       (ModRM)
    0x8B : mov r, r/m         (ModRM)
    0x8D : lea r, m           (ModRM; ModRM.reg is the destination)
    0xB8+r : mov r64, imm     (r = low 3 bits + REX.B; REX.W -> imm64,
                               otherwise imm32; 0x66 -> imm16)
    0xC6 /0 : mov r/m8, imm8   (ModRM.reg must be 0)
    0xC7 /0 : mov r/m, imm16/32 (ModRM.reg must be 0; imm32 sign-extends
                                 in 64-bit)

PUSH / POP (64-bit default operand size, no ModRM):

    0x50+r : push r64         (r + REX.B)
    0x58+r : pop r64          (r + REX.B)

Stack ops (no ModRM): 0x68 push imm32, 0x6A push imm8.

Unary group 3 (ModRM.reg selects): 0xF6/0xF7 — /2 not, /3 neg, /4 mul,
/5 imul, /6 div, /7 idiv; /0 /1 test with immediate.

TEST: 0x84 test r/m8, r8; 0x85 test r/m, r.

XCHG: 0x86/0x87 xchg r/m, r. 0x90+r xchg eAX, r (0x90 alone = NOP).

INC/DEC group 5 (ModRM.reg): 0xFE/0xFF — /0 inc, /1 dec; FF /2 call r/m,
/4 jmp r/m, /6 push r/m.

Branches:

    0x70+cc : jcc rel8         (cc = low nibble)
    0x0F 0x80+cc : jcc rel32
    0xE8 : call rel32
    0xE9 : jmp rel32
    0xEB : jmp rel8
    0xC3 : ret
    0xC2 : ret imm16
    0xCB : retf
    0x9A / 0xEA : far call/jmp (legacy; decode as invalid in 64-bit)

NOP forms: 0x90 (xchg eax,eax); 0x0F 0x1F /0 r/m (multi-byte nop).

Condition codes cc (bits 3:0 of jcc opcode):

    0 O   1 NO  2 B   3 AE  4 E   5 NE  6 BE  7 A
    8 S   9 NS  10 P  11 NP 12 L  13 GE 14 LE 15 G

Two-byte escape: 0x0F starts a two-byte opcode; the M4 core uses only
0x80+cc (jcc rel32) and 0x1F (nop). Everything else 0x0F decodes as
:unsupported with its byte length (ModRM-aware) consumed.

## 8. Decoder outputs (mirroring the A64 core)

Classes (names mirror re_disasm/disasm.kotoba):

    class-nop class-ret class-jmp class-jcc class-call
    class-mov class-lea class-alu class-test class-xchg
    class-push class-pop class-incdec class-unary class-unknown

Fields:

    insn-length     total bytes consumed (needed for RIP-relative)
    insn-rd         ModRM.reg register (dest for lea/mov r,rm)
    insn-rm         ModRM.rm register when mod=11, else -1
    insn-base       SIB/base register or ModRM.rm memory base, -1 if none
    insn-index      SIB index register, -1 if none
    insn-scale      SIB scale 1/2/4/8, 0 if none
    insn-disp       sign-extended displacement (0 if none)
    insn-imm        sign-extended immediate (0 if none)
    insn-rel        sign-extended branch displacement (0 if none)
    insn-op         ALU operation 0..7 / cc for jcc / ModRM.reg for group
    insn-rex-w      1 when REX.W set
    insn-cc         condition code for jcc, -1 otherwise

Targets: branch target = end-of-instruction + insn-rel (same shape as the
A64 insn-target). RIP-relative data references use insn-disp with the same
end-of-instruction base.

## 9. Open (not in M4 core)

VEX/EVEX (AVX), x87, legacy prefixes with semantic effect beyond operand
size, 0x0F multi-byte maps beyond 0x1F/0x80+cc, far control transfer,
bound/int/into (invalid in 64-bit), REX-less 8-bit AH/CH/DH/BH vs SPL forms
when a REX is present (a REX prefix forces the SPL/BPL/SIL/DIL naming).
