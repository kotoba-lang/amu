#!/usr/bin/env python3
"""The SM 7.0 / 7.2 (Volta, Xavier's gv11b) instruction encoder in Kotoba, checked on the host (JUN-713).

No GPU. The unit is the ns line of tools/c/sm70/sm70_encode_test.kotoba, then
tools/c/sm70/sm70_encode.kotoba without its ns form, then the rest of the
test. bin/amu (the Amu-built native Mac arm64 CLI) runs it; the program prints
one line per case (see the test's header) and answers the number of lines.

The oracle is this script's own encoding of every case, transcribed
separately from Mesa NAK's SM70 encoder (src/nouveau/compiler/nak/
sm70_encode.rs at MESA_REV below; the file digests are in
tools/c/sm70/README.md). Checked:
* every I line equals the oracle's 128-bit word bit for bit, every R line
  names the oracle's refusal code, there is no X line, and the set of case
  names equals the oracle's;
* the words of LISTING (NOP, EXIT, the self-branch, S2R TID.X) also equal
  the words of recalled published cuobjdump listings (see LISTING);
* negative controls: one bit flipped in one expected word is reported for
  exactly that case, and every built mutant of the encoder (MUTANTS: one
  field or one bound changed in the Kotoba source) compiles, runs, and is
  detected.

Python only stages the unit, launches bin/amu and compares text; the words
come from the Kotoba program. Usage:
  python3 scripts/seed/check-sm70-encode.py [--amu bin/amu] [--receipt FILE]
"""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENCODER = ROOT / "tools/c/sm70/sm70_encode.kotoba"
TEST = ROOT / "tools/c/sm70/sm70_encode_test.kotoba"
MESA_REV = "fd8ef2befafd01190e33f12dbfd109b924c8ebc3"

# ---------------------------------------------------------------------------
# The oracle: NAK's SM70Encoder, on a Python int of 128 bits.


class Instr:
    def __init__(self):
        self.bits = 0

    def set_field(self, start, end, val):
        n = end - start
        mask = (1 << n) - 1
        self.bits = (self.bits & ~(mask << start)) | ((val & mask) << start)

    def set_bit(self, bit, val):
        self.set_field(bit, bit + 1, 1 if val else 0)

    def words(self):
        return self.bits & (2**64 - 1), self.bits >> 64


RZ, PT = 255, 7


def ctl(delay, yld, wr, rd, wait, reuse):
    return (delay, yld, wr, rd, wait, reuse)


C0 = ctl(0, 0, 7, 7, 0, 0)
C1 = ctl(5, 1, 0, 7, 0, 0)
C2 = ctl(15, 0, 7, 3, 33, 9)
G = (7, False)


def finish(e, guard, deps):
    # encode_sm70_shader: op.encode, then set_pred, then set_instr_deps
    p, inv = guard
    e.set_field(12, 15, p)
    e.set_bit(15, inv)
    delay, yld, wr, rd, wait, reuse = deps
    e.set_field(105, 109, delay)
    e.set_field(110, 113, wr)
    e.set_field(113, 116, rd)
    e.set_field(116, 122, wait)
    e.set_bit(109, yld)
    e.set_field(122, 126, reuse)
    return e.words()


def alu(e, opcode, dst, src0, src1, src2):
    """encode_alu_base for GPR/immediate sources, no modifiers. A source is
    ("r", n), ("i", value) or None."""
    if dst is not None:
        e.set_field(16, 24, dst)
    if src0 is not None:
        e.set_field(24, 32, src0[1])
        e.set_bit(73, False)
        e.set_bit(72, False)

    def src2_reg(s):
        if s is not None:
            e.set_field(64, 72, s[1])
            e.set_bit(74, False)
            e.set_bit(75, False)

    if src2 is None or src2[0] == "r":
        src2_reg(src2)
        if src1 is None:
            form = 1
        elif src1[0] == "r":
            e.set_field(32, 40, src1[1])
            e.set_bit(62, False)
            e.set_bit(63, False)
            form = 1
        else:
            e.set_field(32, 64, src1[1])
            form = 4
    else:
        e.set_field(32, 64, src2[1])
        src2_reg(src1)
        form = 2
    e.set_field(0, 9, opcode)
    e.set_field(9, 12, form)


def r(n):
    return ("r", n)


def i(v):
    return ("i", v)


def op_nop(guard, deps):
    e = Instr()
    e.set_field(0, 12, 0x918)
    return finish(e, guard, deps)


def op_exit(guard, deps):
    e = Instr()
    e.set_field(0, 12, 0x94D)
    e.set_field(84, 85, 0)
    e.set_field(85, 86, 0)
    e.set_field(87, 90, 7)
    e.set_field(90, 91, 0)
    return finish(e, guard, deps)


def op_bra(guard, deps, cond, cond_not, rel):
    # rel in instructions from the next one; NAK: target_ip - ip - 4 in u32 words
    e = Instr()
    e.set_field(0, 12, 0x947)
    e.set_bit(32, False)
    e.set_field(87, 90, cond)
    e.set_bit(90, cond_not)
    ip = 1000 * 4
    target = ip + 4 + 4 * rel
    e.set_field(34, 82, target - ip - 4)
    return finish(e, guard, deps)


def op_mov(guard, deps, d, src):
    e = Instr()
    alu(e, 0x002, d, None, src, None)
    e.set_field(72, 76, 0xF)
    return finish(e, guard, deps)


def op_s2r(guard, deps, d, idx):
    e = Instr()
    e.set_field(0, 12, 0x919)
    e.set_field(16, 24, d)
    e.set_field(72, 80, idx)
    return finish(e, guard, deps)


def op_iadd3(guard, deps, d, a, b, c):
    e = Instr()
    alu(e, 0x010, d, a, b, c)
    e.set_field(87, 90, 7)  # set_pred_src(87..90, 90, false): PT, not
    e.set_bit(90, True)
    e.set_field(77, 80, 7)
    e.set_bit(80, True)
    e.set_field(81, 84, 7)  # overflow dsts None: PT
    e.set_field(84, 87, 7)
    return finish(e, guard, deps)


def op_imad(guard, deps, d, a, b, c, signed):
    e = Instr()
    alu(e, 0x024, d, a, b, c)
    e.set_field(81, 84, 7)
    e.set_bit(73, signed)
    return finish(e, guard, deps)


def cb(e, bank, off):
    # encode_alu_cb: set_src_cb(32..59, 91, cb), abs 62, neg 63
    e.set_field(32 + 6, 32 + 22, off)
    e.set_field(32 + 22, 32 + 27, bank)
    e.set_bit(91, False)
    e.set_bit(62, False)
    e.set_bit(63, False)


def op_mov_cb(guard, deps, d, bank, off):
    e = Instr()
    e.set_field(16, 24, d)
    cb(e, bank, off)
    e.set_field(0, 9, 0x002)
    e.set_field(9, 12, 5)
    e.set_field(72, 76, 0xF)
    return finish(e, guard, deps)


def op_imad_wide(guard, deps, d, a, b, c, signed):
    e = Instr()
    alu(e, 0x025, d, a, b, c)
    e.set_field(81, 84, 7)
    e.set_bit(73, signed)
    return finish(e, guard, deps)


INT_CMP = {"lt": 1, "eq": 2, "le": 3, "gt": 4, "ne": 5, "ge": 6}


def op_isetp(guard, deps, pd, a, b, cmp, signed):
    e = Instr()
    alu(e, 0x00C, None, a, b, None)
    e.set_field(68, 71, 7)  # low_cmp: PT
    e.set_bit(71, False)
    e.set_field(87, 90, 7)  # accum: PT
    e.set_bit(90, False)
    e.set_bit(72, False)
    e.set_field(73, 74, 1 if signed else 0)
    e.set_field(74, 76, 0)  # AND
    e.set_field(76, 79, INT_CMP[cmp])
    e.set_field(81, 84, pd)
    e.set_field(84, 87, 7)
    return finish(e, guard, deps)


def fmods(e, rnd, ftz, sat):
    e.set_bit(77, sat)
    e.set_field(78, 80, rnd)
    e.set_bit(80, ftz)


def op_fadd(guard, deps, d, a, b, rnd, ftz, sat):
    e = Instr()
    if b[0] == "r":
        alu(e, 0x021, d, a, b, None)
    else:
        alu(e, 0x021, d, a, r(RZ), b)
    fmods(e, rnd, ftz, sat)
    return finish(e, guard, deps)


def op_fmul(guard, deps, d, a, b, rnd, ftz, sat):
    e = Instr()
    alu(e, 0x020, d, a, b, r(RZ))
    e.set_bit(76, False)
    fmods(e, rnd, ftz, sat)
    e.set_field(84, 87, 4)
    return finish(e, guard, deps)


def op_ffma(guard, deps, d, a, b, c, rnd, ftz, sat):
    e = Instr()
    alu(e, 0x023, d, a, b, c)
    e.set_bit(76, False)
    fmods(e, rnd, ftz, sat)
    return finish(e, guard, deps)


# OpLd / OpSt, MemSpace::Global, sm < 73 (no UGPR); set_mem_access for sm < 80
ORDER = {0: (3, 0), 1: (0, 1), 2: (0, 2), 3: (2, 2), 4: (3, 2)}  # code -> (scope, order)


def mem_access(e, mtype, order, evict):
    e.set_field(73, 76, mtype)
    scope, o = ORDER[order]
    e.set_field(77, 79, scope)
    e.set_field(79, 81, o)
    e.set_field(84, 87, evict)


def op_ldg(guard, deps, d, a, off, mtype, order, evict, a64):
    e = Instr()
    e.set_field(0, 12, 0x381)
    e.set_field(24, 32, a)
    e.set_bit(72, a64)
    e.set_field(81, 84, 7)
    mem_access(e, mtype, order, evict)
    e.set_field(16, 24, d)
    e.set_field(40, 64, off)
    e.set_bit(91, False)
    return finish(e, guard, deps)


def op_stg(guard, deps, a, off, data, mtype, order, evict, a64):
    e = Instr()
    e.set_field(0, 12, 0x386)
    e.set_field(24, 32, a)
    e.set_bit(72, a64)
    mem_access(e, mtype, order, evict)
    e.set_field(32, 40, data)
    e.set_field(40, 64, off)
    e.set_bit(91, False)
    return finish(e, guard, deps)


# OpLd / OpSt, MemSpace::Shared, sm < 73 (JUN-725): stride X1 (78..80 = 0);
# NAK asserts strong.CTA / normal eviction and writes no order or eviction
def op_lds(guard, deps, d, a, off, mtype):
    e = Instr()
    e.set_field(0, 12, 0x984)
    e.set_field(24, 32, a)
    e.set_field(73, 76, mtype)
    e.set_field(78, 80, 0)
    e.set_bit(87, False)
    e.set_field(16, 24, d)
    e.set_field(40, 64, off)
    e.set_bit(91, False)
    return finish(e, guard, deps)


def op_sts(guard, deps, a, off, data, mtype):
    e = Instr()
    e.set_field(0, 12, 0x388)
    e.set_field(24, 32, a)
    e.set_field(73, 76, mtype)
    e.set_field(78, 80, 0)
    e.set_field(32, 40, data)
    e.set_field(40, 64, off)
    e.set_bit(91, False)
    return finish(e, guard, deps)


def op_bar(guard, deps):
    e = Instr()
    e.set_field(0, 12, 0xB1D)
    return finish(e, guard, deps)


def op_bssy(guard, deps, bar, rel):
    e = Instr()
    e.set_field(0, 12, 0x945)
    e.set_field(16, 20, bar)
    ip = 1000 * 4
    e.set_field(34, 64, ip + 4 + 4 * rel - ip - 4)
    e.set_field(87, 90, 7)
    e.set_bit(90, False)
    return finish(e, guard, deps)


def op_bsync(guard, deps, bar):
    e = Instr()
    e.set_field(0, 12, 0x941)
    e.set_field(16, 20, bar)
    e.set_field(87, 90, 7)
    e.set_bit(90, False)
    return finish(e, guard, deps)


def op_shr(guard, deps, d, a, shift, signed):
    # builder shr (sm >= 70): OpShf {low 0, high a, shift, right, wrap, dst_high}
    e = Instr()
    alu(e, 0x019, d, r(RZ), i(shift & 31), r(a))
    e.set_field(73, 75, 2 if signed else 3)
    e.set_bit(75, True)
    e.set_bit(76, True)
    e.set_bit(80, True)
    return finish(e, guard, deps)


# ---------------------------------------------------------------------------
# The cases: the same names and operands as the Kotoba test.

E_REG, E_PRED, E_CTL, E_IMM, E_OFF, E_BRA, E_ENUM, E_CAP, E_CB, E_BAR = range(1, 11)
SR_LANEID, SR_TID_X, SR_CTAID_X, SR_CTAID_Y = 0x00, 0x21, 0x25, 0x26


def cases():
    c = {}
    c["nop"] = op_nop(G, C0)
    c["exit"] = op_exit(G, ctl(5, 1, 7, 7, 0, 0))
    c["exit.np0"] = op_exit((0, True), C0)
    c["bra.self"] = op_bra(G, C0, 7, False, -1)
    c["bra.next"] = op_bra(G, C0, 7, False, 0)
    c["bra.np2.fwd"] = op_bra(G, C0, 2, True, 37)
    c["bra.gp3.back"] = op_bra((3, False), C0, 7, False, -1000000)
    c["bra.far.fwd"] = op_bra(G, C0, 7, False, 300000000)
    c["bra.max"] = op_bra(G, C0, 7, False, 35184372088831)
    c["bra.min"] = op_bra(G, C0, 7, False, -35184372088832)
    c["mov.r"] = op_mov(G, C0, 4, r(9))
    c["mov.imm"] = op_mov(G, C0, 1, i(0x3F800000))
    c["mov.imm.neg"] = op_mov(G, C0, 254, i(-1))
    c["s2r.tid.x"] = op_s2r(G, C1, 0, SR_TID_X)
    c["s2r.ctaid.y"] = op_s2r(G, C1, 3, SR_CTAID_Y)
    c["s2r.laneid"] = op_s2r(G, C0, 200, SR_LANEID)
    c["s2r.tid.x.listing"] = op_s2r(G, ctl(1, 1, 0, 7, 0, 0), 0, SR_TID_X)
    c["iadd3"] = op_iadd3(G, C0, 1, r(2), r(3), r(4))
    c["iadd3.rz"] = op_iadd3(G, C2, 1, r(2), r(RZ), r(RZ))
    c["iadd3.imm"] = op_iadd3(G, C0, 5, r(6), i(0x400), r(RZ))
    c["iadd3.imm.neg"] = op_iadd3(G, C0, 5, r(6), i(-16), r(7))
    c["imad.s32"] = op_imad(G, C0, 8, r(9), r(10), r(11), True)
    c["imad.u32"] = op_imad(G, C0, 8, r(9), r(10), r(11), False)
    c["imad.imm.u32"] = op_imad(G, C0, 2, r(0), i(4), r(RZ), False)
    c["imad.imm.s32.p1"] = op_imad((1, False), C0, 2, r(0), i(-4), r(3), True)
    c["fadd"] = op_fadd(G, C0, 4, r(5), r(6), 0, False, False)
    c["fadd.rz.ftz.sat"] = op_fadd(G, C0, 4, r(5), r(6), 3, True, True)
    c["fadd.imm"] = op_fadd(G, C0, 4, r(5), i(0x3F800000), 0, False, False)
    c["fmul"] = op_fmul(G, C0, 7, r(8), r(9), 0, False, False)
    c["fmul.rp.sat"] = op_fmul(G, C0, 7, r(8), r(9), 2, False, True)
    c["fmul.imm.rm.ftz"] = op_fmul(G, C0, 7, r(8), i(0x40000000), 1, True, False)
    c["ffma"] = op_ffma(G, C0, 12, r(13), r(14), r(15), 0, False, False)
    c["ffma.rm.ctl"] = op_ffma(G, C2, 12, r(13), r(14), r(15), 1, False, False)
    c["ffma.imm.ftz"] = op_ffma(G, C0, 12, r(13), i(0xBF000000), r(15), 0, True, False)
    c["mov.cb"] = op_mov_cb(G, C0, 6, 0, 0x160)
    c["mov.cb.listing"] = op_mov_cb(G, ctl(5, 0, 7, 7, 0, 0), 1, 0, 0x28)
    c["mov.cb.bank3.max"] = op_mov_cb((2, True), C0, 7, 3, 0xFFFC)
    c["imad.wide.u32"] = op_imad_wide(G, C0, 6, r(0), i(4), r(6), False)
    c["imad.wide.s32.neg"] = op_imad_wide(G, C2, 2, r(9), i(-8), r(250), True)
    c["isetp.lt.u32"] = op_isetp(G, C0, 0, r(0), r(4), "lt", False)
    c["isetp.ge.s32.p6"] = op_isetp(G, C0, 6, r(9), r(RZ), "ge", True)
    c["isetp.eq.u32.gp1"] = op_isetp((1, False), C2, 3, r(2), r(7), "eq", False)
    c["ldg.e.32.strong.gpu"] = op_ldg(G, C1, 4, 2, 0, 4, 3, 1, True)
    c["ldg.e.64.weak.off"] = op_ldg(G, C1, 4, 2, 16, 5, 1, 1, True)
    c["ldg.e.128.constant.neg"] = op_ldg(G, C1, 8, 2, -4, 6, 0, 4, True)
    c["ldg.rz.32.sys.ef"] = op_ldg(G, C1, 4, 255, 256, 4, 4, 0, False)
    c["ldg.s8.cta.na.max"] = op_ldg(G, C1, 4, 2, 8388607, 1, 2, 5, True)
    c["stg.e.32.strong.gpu"] = op_stg(G, C0, 2, 0, 6, 4, 3, 1, True)
    c["stg.e.64.weak.min"] = op_stg(G, C0, 2, -8388608, 6, 5, 1, 2, True)
    c["stg.s16.sys.np0"] = op_stg((0, True), C0, 10, 12, 6, 3, 4, 3, False)
    c["lds.32"] = op_lds(G, C1, 4, 2, 0, 4)
    c["lds.rz.off.p1"] = op_lds((1, False), C1, 9, RZ, 0x3FC, 4)
    c["lds.64.min"] = op_lds(G, C2, 4, 2, -8388608, 5)
    c["sts.32"] = op_sts(G, C0, 2, 0, 6, 4)
    c["sts.u8.max.np0"] = op_sts((0, True), C2, RZ, 8388607, 6, 0)
    c["bar.sync"] = op_bar(G, ctl(5, 1, 7, 7, 0, 0))
    c["bssy.b0.fwd"] = op_bssy(G, C0, 0, 12)
    c["bssy.b15.back"] = op_bssy(G, C2, 15, -3)
    c["bssy.max"] = op_bssy(G, C0, 1, 134217727)
    c["bsync.b0"] = op_bsync(G, ctl(1, 1, 7, 7, 0, 0), 0)
    c["bsync.b9.p2"] = op_bsync((2, False), C0, 9)
    c["shr.u32.1"] = op_shr(G, C0, 5, 6, 1, False)
    c["shr.s32.31"] = op_shr(G, C2, 5, 6, 31, True)
    c["shr.rz.0.np3"] = op_shr((3, True), C0, 254, RZ, 0, False)
    refusals = {
        "refuse.reg.256": E_REG, "refuse.reg.neg": E_REG, "refuse.pred.8": E_PRED,
        "refuse.pred.not": E_PRED, "refuse.guard": E_PRED, "refuse.ctl.delay": E_CTL,
        "refuse.ctl.wait": E_CTL, "refuse.imm.wide": E_IMM, "refuse.imm.low": E_IMM,
        "refuse.off.high": E_OFF, "refuse.off.low": E_OFF, "refuse.bra.far": E_BRA,
        "refuse.enum.mtype": E_ENUM, "refuse.enum.order": E_ENUM, "refuse.enum.evict": E_ENUM,
        "refuse.enum.rnd": E_ENUM, "refuse.enum.signed": E_ENUM, "refuse.enum.sr": E_ENUM,
        "refuse.cap": E_CAP, "refuse.cb.align": E_CB, "refuse.cb.bank": E_CB, "refuse.cb.off": E_CB,
        "refuse.wide.odd": E_REG, "refuse.wide.rz": E_REG, "refuse.enum.cmp": E_ENUM,
        "refuse.lds.off": E_OFF, "refuse.sts.mtype": E_ENUM, "refuse.bssy.bar": E_BAR,
        "refuse.bssy.far": E_BRA, "refuse.bsync.bar": E_BAR, "refuse.shr.imm": E_IMM, "refuse.shr.signed": E_ENUM,
    }
    c.update({k: ("R", v) for k, v in refusals.items()})
    saxpy = [
        op_s2r(G, C1, 0, SR_TID_X),
        op_s2r(G, ctl(1, 1, 1, 7, 0, 0), 6, SR_CTAID_X),
        op_imad(G, ctl(4, 1, 7, 7, 3, 0), 0, r(6), i(128), r(0), False),
        op_imad(G, C0, 8, r(0), i(4), r(2), False),
        op_imad(G, C0, 10, r(0), i(4), r(4), False),
        op_ldg(G, ctl(1, 1, 2, 7, 0, 0), 12, 8, 0, 4, 3, 1, True),
        op_ldg(G, ctl(1, 1, 3, 7, 0, 0), 13, 10, 0, 4, 3, 1, True),
        op_ffma(G, ctl(4, 1, 7, 7, 12, 0), 13, r(12), r(1), r(13), 0, False, False),
        op_stg(G, ctl(1, 1, 7, 7, 0, 0), 10, 0, 13, 4, 3, 1, True),
        op_exit(G, ctl(5, 1, 7, 7, 0, 0)),
        op_bra(G, C0, 7, False, -1),
        op_nop(G, C0),
    ]
    for k, w in enumerate(saxpy):
        c[f"saxpy.{k}"] = w
    return c


# Instruction words in the form cuobjdump -sass / nvdisasm print them for
# Volta-family code (the "/* 0x... */" pairs; lo first). They are recalled
# from widely published listings, not fetched or produced by NVIDIA tools in
# this check (none run here), so they are a cross-check of the NAK reading
# for these four words, not an authoritative reference.
LISTING = {
    "nop": (0x0000000000007918, 0x000FC00000000000),
    "exit": (0x000000000000794D, 0x000FEA0003800000),
    "bra.self": (0xFFFFFFF000007947, 0x000FC0000383FFFF),
    "s2r.tid.x.listing": (0x0000000000007919, 0x000E220000002100),
    # MOV R1, c[0x0][0x28]: the stack-pointer load at the top of CUDA kernels
    "mov.cb.listing": (0x00000A0000017A02, 0x000FCA0000000F00),
}

# Built mutants: (name, old text, new text, cases that must then differ).
MUTANTS = [
    ("iadd3-opcode", "(alu-lo 0x010 1 d a)", "(alu-lo 0x011 1 d a)", ["iadd3"]),
    ("bra-split", "(hf 64 18 (i64-shift-right w 30))", "(hf 64 18 (i64-shift-right w 31))", ["bra.far.fwd"]),
    ("ldg-offset-field", "(lf 24 8 a) (lf 40 24 off))\n                (mem-hi (hf 0 81 3 7)",
     "(lf 24 8 a) (lf 41 23 off))\n                (mem-hi (hf 0 81 3 7)", ["ldg.e.64.weak.off"]),
    ("ctl-wait-shift", "(i64-shift-left wait 11)", "(i64-shift-left wait 12)", ["ffma.rm.ctl"]),
    ("mem-scope-gpu", "(= order 3) 2", "(= order 3) 1", ["ldg.e.32.strong.gpu"]),
    ("off-bound", "(in? off -8388608 8388607)) (sm-fail M SM70-E-OFF)\n        (not (mem? mtype order evict a64)) (sm-fail M SM70-E-ENUM)\n        :else (sm-emit M g ctl\n                (-> 0 (lf 0 12 0x381)",
     "(in? off -8388608 8388608)) (sm-fail M SM70-E-OFF)\n        (not (mem? mtype order evict a64)) (sm-fail M SM70-E-ENUM)\n        :else (sm-emit M g ctl\n                (-> 0 (lf 0 12 0x381)", ["refuse.off.high"]),
    ("guard-field", "(lf lo 12 4 g)", "(lf lo 12 3 g)", ["exit.np0"]),
    ("cb-offset-field", "(lf 38 16 off)", "(lf 36 16 off)", ["mov.cb"]),
    ("isetp-cmp-field", "(hf 76 3 cmp)", "(hf 75 3 cmp)", ["isetp.lt.u32"]),
    ("wide-opcode", "(alu-lo 0x025 4 d a)", "(alu-lo 0x024 4 d a)", ["imad.wide.u32"]),
    ("lds-opcode", "(lf 0 12 0x984)", "(lf 0 12 0x384)", ["lds.32"]),
    ("sts-data-field", "(lf 0 12 0x388) (lf 24 8 a) (lf 32 8 v)", "(lf 0 12 0x388) (lf 24 8 a) (lf 33 8 v)", ["sts.32"]),
    ("bssy-target-field", "(lf 34 30 w)) (-> 0 (hf 87 3", "(lf 32 30 w)) (-> 0 (hf 87 3", ["bssy.b0.fwd"]),
    ("bsync-bar-field", "(lf 0 12 0x941) (lf 16 4 b)", "(lf 0 12 0x941) (lf 17 4 b)", ["bsync.b9.p2"]),
    ("shr-type", "(hf 73 2 (- 3 sgn))", "(hf 73 2 (- 2 sgn))", ["shr.u32.1"]),
    ("shr-high", "(hf 76 1 1) (hf 80 1 1)", "(hf 76 1 1) (hf 80 1 0)", ["shr.u32.1"]),
]

# ---------------------------------------------------------------------------


def strip_ns(text):
    """text without its leading (ns ...) form (which may span lines)."""
    assert text.startswith("(ns ")
    depth = 0
    for k, ch in enumerate(text):
        depth += ch == "("
        depth -= ch == ")"
        if depth == 0:
            return text[k + 1:]
    raise SystemExit("unbalanced ns form")


def unit(encoder_text):
    first, rest = TEST.read_text().split("\n", 1)
    assert first.startswith("(ns ") and first.count("(") == first.count(")"), first
    return first + "\n" + strip_ns(encoder_text) + "\n" + rest


def run(amu, encoder_text, work, tag):
    d = Path(work) / tag
    d.mkdir()
    src = d / "unit.kotoba"
    src.write_text(unit(encoder_text))
    p = subprocess.run([str(amu), "run", src.name], cwd=d, capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        raise RuntimeError(f"{tag}: bin/amu exit {p.returncode}: {p.stderr.strip()}")
    lines = p.stdout.rstrip("\n").split("\n")
    result = int(lines[-1])
    return lines[:-1], result, hashlib.sha256(src.read_bytes()).hexdigest()


def compare(lines, result, want):
    """the case names that differ from want (plus a structural message)"""
    bad, seen = [], set()
    for line in lines:
        f = line.split()
        name = f[1] if len(f) > 1 else line
        if name in seen:
            bad.append(f"duplicate {name}")
        seen.add(name)
        w = want.get(name)
        if f[0] == "I" and len(f) == 4 and isinstance(w, tuple) and w[0] != "R":
            if (int(f[2], 16), int(f[3], 16)) != w:
                bad.append(name)
        elif f[0] == "R" and len(f) == 3 and isinstance(w, tuple) and w[0] == "R":
            if int(f[2]) != w[1]:
                bad.append(name)
        else:
            bad.append(name)
    bad += [f"missing {k}" for k in want if k not in seen]
    if result != len(lines):
        bad.append(f"result {result} != {len(lines)} lines")
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--amu", default=str(ROOT / "bin/amu"))
    ap.add_argument("--receipt")
    args = ap.parse_args()

    want = cases()
    ok = True
    report: dict[str, object] = {"schema": "amu.sm70-encode-check.v1", "mesa": MESA_REV,
              "encoder": hashlib.sha256(ENCODER.read_bytes()).hexdigest(),
              "test": hashlib.sha256(TEST.read_bytes()).hexdigest(),
              "amu": hashlib.sha256(Path(args.amu).resolve().read_bytes()).hexdigest()}

    # the oracle itself against the listings
    for name, words in LISTING.items():
        if want[name] != words:
            print(f"FAIL oracle {name}: {want[name]} != listing {words}")
            ok = False

    with tempfile.TemporaryDirectory(prefix="sm70-") as work:
        enc = ENCODER.read_text()
        lines, result, h = run(args.amu, enc, work, "unit")
        bad = compare(lines, result, want)
        n_i = sum(1 for l in lines if l.startswith("I "))
        n_r = sum(1 for l in lines if l.startswith("R "))
        print(f"unit: {len(lines)} cases ({n_i} words, {n_r} refusals), mismatches {bad or 'none'}")
        ok &= not bad
        got = {l.split()[1]: l for l in lines}
        for name, (lo, hi) in LISTING.items():
            if got.get(name, "") != f"I {name} {lo:016x} {hi:016x}":
                print(f"FAIL listing {name}: {got.get(name)}")
                ok = False
        print(f"listing: {len(LISTING)} words compared")
        report.update(unit=h, cases=len(lines), words=n_i, refusals=n_r, mismatches=bad)

        # control 1: one flipped bit in one expected word is reported for that case alone
        flips = []
        for name, bit in [("ffma", 3), ("ldg.e.32.strong.gpu", 64 + 22), ("saxpy.7", 127)]:
            w2 = dict(want)
            lo, hi = w2[name]
            v = (lo | hi << 64) ^ (1 << bit)
            w2[name] = (v & (2**64 - 1), v >> 64)
            b = compare(lines, result, w2)
            flips.append({"case": name, "bit": bit, "reported": b})
            if b != [name]:
                print(f"FAIL control flip {name} bit {bit}: {b}")
                ok = False
        print(f"control flips: {len(flips)} detected" if all(f["reported"] == [f["case"]] for f in flips) else "control flips: FAIL")

        # control 2: built mutants of the encoder
        muts = []
        for name, old, new, must in MUTANTS:
            if enc.count(old) != 1:
                print(f"FAIL mutant {name}: anchor found {enc.count(old)} times")
                ok = False
                continue
            ml, mr, mh = run(args.amu, enc.replace(old, new), work, f"mutant-{name}")
            b = compare(ml, mr, want)
            hit = all(m in b for m in must)
            muts.append({"mutant": name, "unit": mh, "detected": b})
            print(f"mutant {name}: {'detected' if hit else 'NOT DETECTED'} ({len(b)} cases differ: {', '.join(b[:6])}{' ...' if len(b) > 6 else ''})")
            ok &= hit
        report.update(flips=flips, mutants=muts)

    report["ok"] = bool(ok)
    if args.receipt:
        Path(args.receipt).write_text(json.dumps(report, indent=1) + "\n")
    print("sm70-encode: PASS" if ok else "sm70-encode: FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
