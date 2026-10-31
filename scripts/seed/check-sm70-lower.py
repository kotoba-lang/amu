#!/usr/bin/env python3
"""KIR v2 lowered to SM 7.0 / 7.2 (Xavier's gv11b) with scheduled control bits, checked on the host (JUN-723, JUN-725).

No GPU and no GPU driver: nothing here opens a device or submits work.

Two units run through bin/amu (the Amu-built native Mac arm64 CLI):
* the modules unit (tools/c/sm70/sm70_lower_modules.kotoba after
  tools/spirv_encode.kotoba, spirv_check, gpu_kernel_kir2 and gpu_kernels_v2)
  prints the SPIR-V words of the KIR v2 kernels, built once;
* the lowering unit (tools/c/sm70/sm70_lower_test.kotoba after
  spirv_encode.kotoba, sm70_encode.kotoba, sm70_sched.kotoba and
  sm70_lower.kotoba) takes those words as arguments, lowers, schedules and
  encodes each module, and prints the instruction words.

This script is the oracle; the words come from the Kotoba program. Checked:
* determinism: two runs of the lowering unit print the same bytes;
* every word decodes into the supported subset (DECODE below, read from Mesa
  NAK's sm70_encode.rs like scripts/seed/check-sm70-encode.py) and equals
  that script's NAK encoding of the decoded instruction, bit for bit;
* the expected refusal: ewise sub (OpFSub, 131);
* the scheduler's hand-written WAR cases get exactly the control bits of
  WAR_CTL and LOOPWAR_CTL;
* the interpreter (run_kernel) runs ewise add (LocalSize 256 and 64) and mul
  on sample data, one thread at a time, and every output word equals the
  f64 reference rounded to f32 (exact for add and mul of these inputs), the
  words past n are untouched and no access leaves its buffer. It also
  models the issue timing the control bits promise: a register or
  predicate read before its write is ready (RAW), a write that lands before
  an earlier variable-latency read of the same register (WAR) or before an
  earlier write (WAW) is a hazard and fails the run;
* the interpreter runs dot_rows (DOT_CASES) a workgroup at a time, the
  threads interleaved at each BAR, against an f64 reference (relative to
  sum |w x|, DOT_TOL), with a shared-memory race check between barriers and
  the BSSY/BSYNC pairing; check_control holds the static rules (BSSY targets,
  BAR's stall, yield and NOP);
* negative controls: control bits corrupted in the emitted words (a wait
  mask, a stall, a write barrier), one operand bit, and in dot_rows a barrier
  replaced by a NOP, a branch condition and a BSSY target are detected;
  built mutants of the lowering and of the scheduler (LOWER_MUTANTS,
  SCHED_MUTANTS) compile, run and are detected.

The timing model is NAK's Volta model (GPR 6 cycles, predicate 13, S2R and
memory on scoreboards), the same model the scheduler uses: it shows that the
scheduler keeps its own rules, not that the rules are Volta's. The launch
interface (binding b's address at c[0][0x160 + 8 b]) is the lowering's
assumption. Execution on Xavier (JUN-714) is the independent test.

Usage: python3 scripts/seed/check-sm70-lower.py [--amu bin/amu] [--receipt FILE]
"""

import argparse
import hashlib
import math
import importlib.util
import json
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SM70 = ROOT / "tools/c/sm70"
MODULES_UNIT = (SM70 / "sm70_lower_modules.kotoba",
                ["tools/spirv_encode.kotoba", "tools/spirv_check.kotoba", "tools/gpu_kernel_kir2.kotoba",
                 "tools/gpu_kernels_v2.kotoba"])
LOWER_UNIT = (SM70 / "sm70_lower_test.kotoba",
              ["tools/spirv_encode.kotoba", "tools/c/sm70/sm70_encode.kotoba", "tools/c/sm70/sm70_sched.kotoba",
               "tools/c/sm70/sm70_regalloc.kotoba", "tools/c/sm70/sm70_lower.kotoba"])

spec = importlib.util.spec_from_file_location("sm70_oracle", ROOT / "scripts/seed/check-sm70-encode.py")
NAK = importlib.util.module_from_spec(spec)
spec.loader.exec_module(NAK)

CB_BASE = 0x160
LAT_GPR, LAT_PRED = 6, 13       # NAK ShaderModel70 (sm < 80)
VAR_READ = 8                     # a variable-latency op reads its sources up to this many cycles after issue
EXPECT_REFUSED = {}   # name -> (error, SPIR-V opcode): every module of this check now lowers
# the WAR case: (stall, yield, write barrier, read barrier, wait mask) per instruction
WAR_CTL = [(1, 0, 0, 1, 0), (1, 0, 7, 7, 2), (6, 0, 7, 7, 1), (6, 0, 7, 7, 0), (1, 0, 7, 7, 0), (0, 1, 7, 7, 0)]
# the loop WAR case: the STS's source is rewritten after the back edge, so
# the STS takes a read barrier and the branch waits on it
LOOPWAR_CTL = [(6, 0, 7, 7, 0), (1, 0, 7, 0, 0), (1, 0, 7, 7, 1), (0, 1, 7, 7, 0)]
KERNELS = {"ewise-add-wg256": ("add", 256), "ewise-add-wg64": ("add", 64), "ewise-mul-wg256": ("mul", 256),
           "ewise-sub-wg256": ("sub", 256)}
SIZES = [1000, 256, 1]
# dot_rows: (rows, cols, signed inputs). 700 = 2 * 256 + 188: threads leave
# the strided loop after 3 or 2 iterations; 100: threads 100.. never enter it
DOT_CASES = [(3, 700, False), (2, 256, True), (1, 100, False), (2, 1, True), (1, 1300, True)]
DOT_TOL = 1e-3   # |o - f64 reference| / sum |w x|

# ---------------------------------------------------------------------------
# Units


def strip_ns(text):
    assert text.startswith("(ns ")
    depth = 0
    for k, ch in enumerate(text):
        depth += ch == "("
        depth -= ch == ")"
        if depth == 0:
            return text[k + 1:]
    raise SystemExit("unbalanced ns form")


def unit_text(test, mods, replace=None):
    first, rest = test.read_text().split("\n", 1)
    assert first.startswith("(ns ") and first.count("(") == first.count(")"), first
    parts = []
    for m in mods:
        t = (ROOT / m).read_text()
        if replace and replace[0] == m:
            assert t.count(replace[1]) == 1, f"mutant anchor in {m}: {t.count(replace[1])}"
            t = t.replace(replace[1], replace[2])
        parts.append(strip_ns(t))
    return first + "\n" + "".join(parts) + "\n" + rest


def run_unit(amu, text, work, tag, args=()):
    d = Path(work) / tag
    d.mkdir()
    (d / "unit.kotoba").write_text(text)
    p = subprocess.run([str(amu), "run", "unit.kotoba", "--", *args], cwd=d, capture_output=True, text=True,
                       timeout=600)
    if p.returncode != 0:
        raise RuntimeError(f"{tag}: bin/amu exit {p.returncode}: {p.stderr.strip()[:400]}")
    return p.stdout, hashlib.sha256(text.encode()).hexdigest()


def module_args(modules):
    args = [str(len(modules))]
    for name, words in modules.items():
        args += [name, ",".join(str(w) for w in words)]
    return args


def parse_programs(out):
    lines = out.rstrip("\n").split("\n")
    result = int(lines[-1])
    if result != len(lines) - 1:
        raise RuntimeError(f"lowering unit answered {result} for {len(lines) - 1} lines")
    progs, cur = {}, None
    for line in lines[:-1]:
        f = line.split()
        if f[0] == "K":
            cur = f[1]
            progs[cur] = {"count": int(f[2]), "error": int(f[3]), "op": int(f[4]), "words": []}
        elif f[0] == "I" and f[1] == f"{cur}.{len(progs[cur]['words'])}":
            progs[cur]["words"].append((int(f[2], 16), int(f[3], 16)))
        else:
            raise RuntimeError(f"unexpected line {line!r}")
    for name, p in progs.items():
        if p["count"] != len(p["words"]):
            raise RuntimeError(f"{name}: {p['count']} words announced, {len(p['words'])} printed")
    return progs


# ---------------------------------------------------------------------------
# Decoding (fields as in NAK sm70_encode.rs; check-sm70-encode.py has the encoder)


class Unsupported(Exception):
    pass


def sx(v, n):
    return v - (1 << n) if v >> (n - 1) else v


def decode(lo, hi):
    b = lo | hi << 64

    def f(a, z):
        return (b >> a) & ((1 << (z - a)) - 1)

    i = {"guard": (f(12, 15), f(15, 16)),
         "ctl": (f(105, 109), f(109, 110), f(110, 113), f(113, 116), f(116, 122), f(122, 126))}
    op12, op9, form = f(0, 12), f(0, 9), f(9, 12)
    if op12 == 0x919:
        i.update(op="s2r", d=f(16, 24), sr=f(72, 80))
    elif op12 == 0x94D:
        i.update(op="exit")
    elif op12 == 0x947:
        i.update(op="bra", rel=sx(f(34, 82), 48) // 4, cond=(f(87, 90), f(90, 91)))
    elif op12 == 0x918:
        i.update(op="nop")
    elif op12 == 0xB1D:
        i.update(op="bar")
    elif op12 == 0x945:
        i.update(op="bssy", bar=f(16, 20), rel=sx(f(34, 64), 30) // 4)
    elif op12 == 0x941:
        i.update(op="bsync", bar=f(16, 20))
    elif op12 == 0x984:
        if f(73, 76) != 4 or f(78, 80):
            raise Unsupported("LDS not .32 / X1")
        i.update(op="lds", d=f(16, 24), a=f(24, 32), off=sx(f(40, 64), 24))
    elif op12 == 0x388:
        if f(73, 76) != 4 or f(78, 80):
            raise Unsupported("STS not .32 / X1")
        i.update(op="sts", a=f(24, 32), v=f(32, 40), off=sx(f(40, 64), 24))
    elif op9 == 0x019 and form == 4 and f(24, 32) == 255 and f(73, 75) == 3 and f(76, 77) and f(80, 81):
        i.update(op="shr", d=f(16, 24), a=f(64, 72), imm=f(32, 64))
    elif op9 == 0x019 and form in (1, 4):
        i.update(op="shf", d=f(16, 24), lo=f(24, 32), s=(f(32, 40) if form == 1 else f(32, 64)), imm=form == 4,
                 hi=f(64, 72), ty=f(73, 75), wrap=f(75, 76), right=f(76, 77), high=f(80, 81))
    elif op9 == 0x002 and form == 1:
        i.update(op="mov", d=f(16, 24), a=f(32, 40))
    elif op12 == 0x381:
        if f(73, 76) != 4 or f(72, 73) != 1:
            raise Unsupported("LDG not .E.32")
        i.update(op="ldg", d=f(16, 24), a=f(24, 32), off=sx(f(40, 64), 24), order=(f(77, 79), f(79, 81)))
    elif op12 == 0x386:
        if f(73, 76) != 4 or f(72, 73) != 1:
            raise Unsupported("STG not .E.32")
        i.update(op="stg", a=f(24, 32), v=f(32, 40), off=sx(f(40, 64), 24), order=(f(77, 79), f(79, 81)))
    elif op9 == 0x002 and form == 5:
        i.update(op="mov.cb", d=f(16, 24), bank=f(54, 59), off=f(38, 54))
    elif op9 == 0x002 and form == 4:
        i.update(op="mov.imm", d=f(16, 24), imm=f(32, 64))
    elif op9 == 0x024 and form == 4:
        i.update(op="imad.imm", d=f(16, 24), a=f(24, 32), imm=f(32, 64), c=f(64, 72), signed=f(73, 74))
    elif op9 == 0x024 and form == 1:
        i.update(op="imad", d=f(16, 24), a=f(24, 32), b=f(32, 40), c=f(64, 72), signed=f(73, 74))
    elif op9 == 0x025 and form == 4:
        i.update(op="imad.wide.imm", d=f(16, 24), a=f(24, 32), imm=f(32, 64), c=f(64, 72), signed=f(73, 74))
    elif op9 == 0x010 and form == 1:
        i.update(op="iadd3", d=f(16, 24), a=f(24, 32), b=f(32, 40), c=f(64, 72), neg=(f(72, 73), f(63, 64), f(75, 76)))
    elif op9 == 0x00C and form == 1:
        if f(72, 73) or f(74, 76):
            raise Unsupported("ISETP .EX or not AND")
        i.update(op="isetp", pd=f(81, 84), a=f(24, 32), b=f(32, 40), cmp=f(76, 79), signed=f(73, 74),
                 accum=(f(87, 90), f(90, 91)))
    elif op9 in (0x021, 0x020) and form == 1:
        if f(77, 81):
            raise Unsupported("FADD/FMUL rounding, ftz or sat")
        i.update(op="fadd" if op9 == 0x021 else "fmul", d=f(16, 24), a=f(24, 32), b=f(32, 40),
                 neg=(f(72, 73), f(63, 64)) if op9 == 0x021 else (0, 0))
    elif op9 == 0x020 and form == 4:
        if f(77, 81):
            raise Unsupported("FMUL rounding, ftz or sat")
        i.update(op="fmul.imm", d=f(16, 24), a=f(24, 32), imm=f(32, 64))
    elif op9 == 0x00B and form in (1, 4):
        if f(74, 76) or f(80, 81):
            raise Unsupported("FSETP not AND or ftz")
        i.update(op="fsetp", pd=f(81, 84), a=f(24, 32), b=f(32, 40) if form == 1 else None,
                 imm=f(32, 64) if form == 4 else None, cmp=f(76, 80))
    elif op9 in (0x009, 0x017) and form == 1:
        i.update(op="fmnmx" if op9 == 0x009 else "imnmx", d=f(16, 24), a=f(24, 32), b=f(32, 40),
                 min=(f(87, 90), f(90, 91)), signed=f(73, 74), ftz=f(80, 81))
    elif op9 == 0x007 and form in (1, 4):
        i.update(op="sel", d=f(16, 24), a=f(24, 32), b=f(32, 40) if form == 1 else None,
                 imm=f(32, 64) if form == 4 else None, cond=(f(87, 90), f(90, 91)))
    elif op9 == 0x108 and form == 1:
        i.update(op="mufu", d=f(16, 24), a=f(32, 40), fn=f(74, 80))
    elif op9 == 0x106 and form == 1:
        i.update(op="i2f", d=f(16, 24), a=f(32, 40), signed=f(74, 75), rnd=f(78, 80))
    elif op9 == 0x105 and form == 1:
        i.update(op="f2i", d=f(16, 24), a=f(32, 40), signed=f(72, 73), rnd=f(78, 80), ftz=f(80, 81))
    elif op9 == 0x012 and form in (1, 4):
        i.update(op="lop3", d=f(16, 24), a=f(24, 32), b=f(32, 40) if form == 1 else None,
                 imm=f(32, 64) if form == 4 else None, c=f(64, 72), lut=f(72, 80))
    elif op9 == 0x025 and form == 1:
        i.update(op="imad.wide", d=f(16, 24), a=f(24, 32), b=f(32, 40), c=f(64, 72), signed=f(73, 74))
    elif op9 == 0x01A and form == 4:
        i.update(op="sgxt", d=f(16, 24), a=f(24, 32), bits=f(32, 64), signed=f(73, 74))
    else:
        raise Unsupported(f"opcode {op12:#x} form {form}")
    return i


CMP = {v: k for k, v in NAK.INT_CMP.items()}
FCMP = {v: k for k, v in NAK.FLOAT_CMP.items()}
MUFU_NAME = {v: k for k, v in NAK.MUFU.items()}
SHF_TYPE = {v: k for k, v in NAK.SHF_TYPE.items()}


def reencode(i):
    """the NAK encoding (check-sm70-encode.py) of a decoded instruction"""
    g = (i["guard"][0], bool(i["guard"][1]))
    c = i["ctl"]
    r, imm = NAK.r, NAK.i
    o = i["op"]
    if o == "s2r":
        return NAK.op_s2r(g, c, i["d"], i["sr"])
    if o == "exit":
        return NAK.op_exit(g, c)
    if o == "nop":
        return NAK.op_nop(g, c)
    if o == "bar":
        return NAK.op_bar(g, c)
    if o == "bssy":
        return NAK.op_bssy(g, c, i["bar"], i["rel"])
    if o == "bsync":
        return NAK.op_bsync(g, c, i["bar"])
    if o == "lds":
        return NAK.op_lds(g, c, i["d"], i["a"], i["off"], 4)
    if o == "sts":
        return NAK.op_sts(g, c, i["a"], i["off"], i["v"], 4)
    if o == "shr":
        return NAK.op_shr(g, c, i["d"], i["a"], i["imm"], False)
    if o == "mov":
        return NAK.op_mov(g, c, i["d"], r(i["a"]))
    if o == "bra":
        return NAK.op_bra(g, c, i["cond"][0], bool(i["cond"][1]), i["rel"])
    if o == "ldg":
        return NAK.op_ldg(g, c, i["d"], i["a"], i["off"], 4, 3, 1, True)
    if o == "stg":
        return NAK.op_stg(g, c, i["a"], i["off"], i["v"], 4, 3, 1, True)
    if o == "mov.cb":
        return NAK.op_mov_cb(g, c, i["d"], i["bank"], i["off"])
    if o == "mov.imm":
        return NAK.op_mov(g, c, i["d"], imm(i["imm"]))
    if o == "imad.imm":
        return NAK.op_imad(g, c, i["d"], r(i["a"]), imm(i["imm"]), r(i["c"]), bool(i["signed"]))
    if o == "imad":
        return NAK.op_imad(g, c, i["d"], r(i["a"]), r(i["b"]), r(i["c"]), bool(i["signed"]))
    if o == "imad.wide.imm":
        return NAK.op_imad_wide(g, c, i["d"], r(i["a"]), imm(i["imm"]), r(i["c"]), bool(i["signed"]))
    if o == "iadd3" and any(i["neg"]):
        return NAK.op_iadd3_neg(g, c, i["d"], i["a"], i["b"], i["c"], *map(bool, i["neg"]))
    if o == "iadd3":
        return NAK.op_iadd3(g, c, i["d"], r(i["a"]), r(i["b"]), r(i["c"]))
    if o == "isetp":
        return NAK.op_isetp(g, c, i["pd"], r(i["a"]), r(i["b"]), CMP[i["cmp"]], bool(i["signed"]))
    if o == "fadd" and any(i["neg"]):
        return NAK.op_fadd_neg(g, c, i["d"], i["a"], i["b"], *map(bool, i["neg"]))
    if o == "fadd":
        return NAK.op_fadd(g, c, i["d"], r(i["a"]), r(i["b"]), 0, False, False)
    if o == "fmul.imm":
        return NAK.op_fmul(g, c, i["d"], r(i["a"]), imm(i["imm"]), 0, False, False)
    if o == "fsetp":
        b = r(i["b"]) if i["b"] is not None else imm(i["imm"])
        return NAK.op_fsetp(g, c, i["pd"], i["a"], b, FCMP[i["cmp"]], False)
    if o == "fmnmx":
        return NAK.op_fmnmx(g, c, i["d"], i["a"], i["b"], not i["min"][1], bool(i["ftz"]))
    if o == "imnmx":
        return NAK.op_imnmx(g, c, i["d"], i["a"], i["b"], not i["min"][1], bool(i["signed"]))
    if o == "sel":
        b = r(i["b"]) if i["b"] is not None else imm(i["imm"])
        return NAK.op_sel(g, c, i["d"], i["a"], b, i["cond"][0], bool(i["cond"][1]))
    if o == "mufu":
        return NAK.op_mufu(g, c, i["d"], i["a"], MUFU_NAME[i["fn"]])
    if o == "i2f":
        return NAK.op_i2f(g, c, i["d"], i["a"], bool(i["signed"]), i["rnd"])
    if o == "f2i":
        return NAK.op_f2i(g, c, i["d"], i["a"], bool(i["signed"]), i["rnd"], bool(i["ftz"]))
    if o == "lop3":
        b = r(i["b"]) if i["b"] is not None else imm(i["imm"])
        return NAK.op_lop3(g, c, i["d"], i["a"], b, i["c"], i["lut"])
    if o == "shf":
        return NAK.op_shf(g, c, i["d"], i["lo"], imm(i["s"]) if i["imm"] else r(i["s"]), i["hi"],
                          SHF_TYPE[i["ty"]], bool(i["wrap"]), bool(i["right"]), bool(i["high"]))
    if o == "imad.wide":
        return NAK.op_imad_wide(g, c, i["d"], r(i["a"]), r(i["b"]), r(i["c"]), bool(i["signed"]))
    if o == "sgxt":
        return NAK.op_sgxt(g, c, i["d"], i["a"], i["bits"], bool(i["signed"]))
    if o == "fmul":
        return NAK.op_fmul(g, c, i["d"], r(i["a"]), r(i["b"]), 0, False, False)
    raise Unsupported(o)


# ---------------------------------------------------------------------------
# The interpreter: one thread at a time, in program order, with issue times.


class Hazard(Exception):
    pass


def f32(x):
    return struct.unpack("<f", struct.pack("<f", x))[0]


def bits_f(u):
    return struct.unpack("<f", struct.pack("<I", u & 0xFFFFFFFF))[0]


def f_bits(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


class Memory:
    def __init__(self):
        self.bufs = []  # (base, bytearray)

    def add(self, base, data):
        assert all(base + len(data) <= b or b + len(d) <= base for b, d in self.bufs), "buffers overlap"
        self.bufs.append((base, data))

    def find(self, addr):
        if addr % 4:
            raise Hazard(f"unaligned access {addr:#x}")
        for base, data in self.bufs:
            if base <= addr and addr + 4 <= base + len(data):
                return data, addr - base
        raise Hazard(f"access outside every buffer at {addr:#x}")

    def load(self, addr):
        data, o = self.find(addr)
        return struct.unpack_from("<I", data, o)[0]

    def store(self, addr, v):
        data, o = self.find(addr)
        struct.pack_into("<I", data, o, v & 0xFFFFFFFF)


VAR_OPS = ("s2r", "ldg", "stg", "lds", "sts", "mufu", "i2f", "f2i")


def latency(kind, seed):
    # variable latencies: fixed pseudo-random spreads, so a missing wait shows
    seed = (seed * 6364136223846793005 + 1442695040888963407) % 2**64
    return ({"s2r": 20, "ldg": 200, "lds": 24, "mufu": 14, "cvt": 10}[kind]
            + (seed >> 33) % {"s2r": 400, "ldg": 400, "lds": 60, "mufu": 40, "cvt": 30}[kind])


def fcmp(cmp, a, b):
    """NAK set_float_cmp_op codes: 1..6 ordered (false on NaN), 9..14 unordered (true on NaN)"""
    if cmp == 7:
        return a == a and b == b
    if cmp == 8:
        return a != a or b != b
    nan = a != a or b != b
    rel = {1: a < b, 2: a == b, 3: a <= b, 4: a > b, 5: a != b, 6: a >= b}[cmp & 7]
    return (not nan and rel) if cmp < 8 else (nan or rel)


# MUFU is an approximation; the interpreter answers the f64 function rounded
# to f32 and moved by a pseudo-random 0..MUFU_ULP units in the last place, so
# a gate that passes does not depend on correct rounding
MUFU_ULP = 2


def mufu(fn, x, seed):
    try:
        v = {0: lambda: math.cos(2 * math.pi * x), 1: lambda: math.sin(2 * math.pi * x),
             2: lambda: 2.0 ** x, 3: lambda: math.log2(x) if x > 0 else (-math.inf if x == 0 else math.nan),
             4: lambda: 1.0 / x if x else math.copysign(math.inf, x),
             5: lambda: 1.0 / math.sqrt(x) if x > 0 else (math.inf if x == 0 else math.nan),
             8: lambda: math.sqrt(x) if x >= 0 else math.nan}[fn]()
    except OverflowError:
        v = math.inf
    try:
        v = f32(v)
    except OverflowError:
        v = math.copysign(math.inf, v)
    if v != v or v in (math.inf, -math.inf) or v == 0:
        return v
    seed = (seed * 2862933555777941757 + 3037000493) % 2**64
    k = (seed >> 40) % (2 * MUFU_ULP + 1) - MUFU_ULP
    return bits_f(f_bits(v) + k)


def f2i(x, signed):
    lo, hi = (-2**31, 2**31 - 1) if signed else (0, 2**32 - 1)
    if x != x:
        return 0
    v = max(lo, min(hi, math.trunc(x))) if abs(x) != math.inf else (hi if x > 0 else lo)
    return v % 2**32


def lop3(lut, a, b, c):
    v = 0
    for k in range(8):
        if lut >> k & 1:
            v |= (a if k & 4 else ~a) & (b if k & 2 else ~b) & (c if k & 1 else ~c)
    return v % 2**32


def shf(lo, s, hi, i):
    """NAK's OpShf fold for sm >= 70"""
    bits = 64 if i["ty"] < 2 else 32
    s = s & (bits - 1) if i["wrap"] else min(s, bits)
    x = lo | hi << 32
    if i["ty"] in (0, 2):
        x = sx(x, 64)
    v = (x >> s if i["right"] else x << s) % 2**64
    return v >> 32 if i["high"] else v % 2**32


SHARED_BYTES = 1024          # dot_rows' Workgroup array (the lowering lays it out from byte 0)
SHARED_FILL = 0x7FC00BAD     # a NaN: a shared word read before any write shows in the output
MAX_STEPS = 200000


class Shared:
    """the workgroup's shared memory, with a race check: between two barriers
    (one phase) a word written by one thread is not read or written by
    another, and a word read by one thread is not written by another"""

    def __init__(self, nbytes):
        self.words = [SHARED_FILL] * (nbytes // 4)
        self.w, self.r = {}, {}  # word -> (phase, tid); word -> (phase, set of tids)

    def index(self, addr):
        if addr % 4 or not 0 <= addr < 4 * len(self.words):
            raise Hazard(f"shared access at {addr:#x} outside the {4 * len(self.words)}-byte window")
        return addr // 4

    def load(self, addr, phase, tid):
        k = self.index(addr)
        wp = self.w.get(k)
        if wp and wp[0] == phase and wp[1] != tid:
            raise Hazard(f"shared word {k}: thread {tid} reads what thread {wp[1]} wrote in the same phase")
        rp = self.r.get(k)
        if rp and rp[0] == phase:
            rp[1].add(tid)
        else:
            self.r[k] = (phase, {tid})
        return self.words[k]

    def store(self, addr, v, phase, tid):
        k = self.index(addr)
        wp = self.w.get(k)
        if wp and wp[0] == phase and wp[1] != tid:
            raise Hazard(f"shared word {k}: threads {wp[1]} and {tid} write it in the same phase")
        rp = self.r.get(k)
        if rp and rp[0] == phase and rp[1] - {tid}:
            raise Hazard(f"shared word {k}: thread {tid} writes what thread {min(rp[1] - {tid})} read in the same phase")
        self.w[k] = (phase, tid)
        self.words[k] = v & 0xFFFFFFFF


def run_thread(prog, cbank, mem, shared, ctaid, tid):
    """one thread, a generator: it yields (pc, cycle) at each BAR and is sent
    back the cycle at which the workgroup leaves the barrier; it returns at
    EXIT. Hazards and malformed control flow raise."""
    regs, preds = {}, {}  # reg -> (seq, ready, value)
    pending_reads = {}    # reg -> [(seq, read until)] of variable-latency reads
    sb_done = [0] * 6
    bssy = {}
    t, pc, steps, phase = 0, 0, 0, 0

    def read(r, at, seq):
        if r == 255:
            return 0
        w = regs.get(r)
        if w is None:
            raise Hazard(f"R{r} read before any write (instr {seq})")
        w_seq, ready, v = w
        if ready > at:
            raise Hazard(f"instr {seq} reads R{r} at {at}, written by instr {w_seq} ready at {ready}")
        return v

    def rpred(p, at, seq):
        if p == 7:
            return True
        w = preds.get(p)
        if w is None:
            raise Hazard(f"P{p} read before any write (instr {seq})")
        w_seq, ready, v = w
        if ready > at:
            raise Hazard(f"instr {seq} reads P{p} at {at}, written by instr {w_seq} ready at {ready}")
        return v

    def write(r, ready, v, seq, issue):
        if r == 255:
            return
        w = regs.get(r)
        if w and w[1] > ready:
            raise Hazard(f"instr {seq} writes R{r} ready {ready} before instr {w[0]}'s write at {w[1]}")
        for rs, rt in pending_reads.get(r, []):
            if issue + 1 <= rt:
                raise Hazard(f"instr {seq} writes R{r} at {issue + 1} while instr {rs} reads it until {rt}")
        regs[r] = (seq, ready, v & 0xFFFFFFFF)

    def var_read(regs_read, seq, rt, issue):
        for r in regs_read:
            lst = [e for e in pending_reads.get(r, []) if e[1] >= issue]
            lst.append((seq, rt))
            pending_reads[r] = lst

    while True:
        if not 0 <= pc < len(prog):
            raise Hazard(f"control left the program at {pc}")
        steps += 1
        if steps > MAX_STEPS:
            raise Hazard("the thread does not finish")
        i = prog[pc]
        stall, _yld, wr, rd, wait, _reuse = i["ctl"]
        issue = max([t] + [sb_done[s] for s in range(6) if wait >> s & 1])
        p, inv = i["guard"]
        on = rpred(p, issue, pc) != bool(inv)
        o = i["op"]
        var = o in VAR_OPS
        rt = issue + VAR_READ if var else issue
        seed = ((ctaid * 4096 + tid) * 4096 + pc) * 1000003 + steps
        nxt = pc + 1
        if on:
            if o == "exit":
                return
            if o == "bra":
                if i["rel"] == -1:
                    raise Hazard("reached the trailing branch")
                nxt = pc + 1 + i["rel"]
            elif o == "bssy":
                if i["bar"] in bssy:
                    raise Hazard(f"BSSY B{i['bar']} at {pc} re-armed before its BSYNC")
                bssy[i["bar"]] = pc + 1 + i["rel"]
            elif o == "bsync":
                if bssy.pop(i["bar"], None) != pc:
                    raise Hazard(f"BSYNC B{i['bar']} at {pc} without a BSSY to it")
            elif o == "bar":
                issue = max(issue, (yield pc, issue))
                phase += 1
            elif o == "nop":
                pass
            elif o == "s2r":
                v = {0x21: tid, 0x25: ctaid}[i["sr"]]
                write(i["d"], issue + latency("s2r", seed), v, pc, issue)
            elif o == "mov.cb":
                write(i["d"], issue + LAT_GPR, cbank[(i["bank"], i["off"])], pc, issue)
            elif o == "mov.imm":
                write(i["d"], issue + LAT_GPR, i["imm"], pc, issue)
            elif o == "mov":
                write(i["d"], issue + LAT_GPR, read(i["a"], rt, pc), pc, issue)
            elif o == "shr":
                write(i["d"], issue + LAT_GPR, read(i["a"], rt, pc) >> (i["imm"] & 31), pc, issue)
            elif o in ("imad.imm", "imad"):
                b = i["imm"] if o == "imad.imm" else read(i["b"], rt, pc)
                v = read(i["a"], rt, pc) * b + read(i["c"], rt, pc)
                write(i["d"], issue + LAT_GPR, v, pc, issue)
            elif o == "imad.wide.imm":
                if i["signed"]:
                    raise Unsupported("IMAD.WIDE.S32")
                c = read(i["c"], rt, pc) | read(i["c"] + 1, rt, pc) << 32
                v = (read(i["a"], rt, pc) * i["imm"] + c) % 2**64
                write(i["d"], issue + LAT_GPR, v, pc, issue)
                write(i["d"] + 1, issue + LAT_GPR, v >> 32, pc, issue)
            elif o == "iadd3":
                v = sum(-x if n else x for x, n in zip((read(i["a"], rt, pc), read(i["b"], rt, pc),
                                                         read(i["c"], rt, pc)), i["neg"]))
                write(i["d"], issue + LAT_GPR, v, pc, issue)
            elif o == "isetp":
                a, b = read(i["a"], rt, pc), read(i["b"], rt, pc)
                if i["signed"]:
                    a, b = sx(a, 32), sx(b, 32)
                c = {1: a < b, 2: a == b, 3: a <= b, 4: a > b, 5: a != b, 6: a >= b}[i["cmp"]]
                acc = rpred(i["accum"][0], rt, pc) != bool(i["accum"][1])
                if i["pd"] != 7:
                    preds[i["pd"]] = (pc, issue + LAT_PRED, c and acc)
            elif o in ("fadd", "fmul"):
                a, b = bits_f(read(i["a"], rt, pc)), bits_f(read(i["b"], rt, pc))
                a, b = (-a if i["neg"][0] else a), (-b if i["neg"][1] else b)
                write(i["d"], issue + LAT_GPR, f_bits(f32(a + b if o == "fadd" else a * b)), pc, issue)
            elif o == "fmul.imm":
                write(i["d"], issue + LAT_GPR, f_bits(f32(bits_f(read(i["a"], rt, pc)) * bits_f(i["imm"]))), pc, issue)
            elif o == "fsetp":
                a = bits_f(read(i["a"], rt, pc))
                b = bits_f(read(i["b"], rt, pc) if i["b"] is not None else i["imm"])
                if i["pd"] != 7:
                    preds[i["pd"]] = (pc, issue + LAT_PRED, fcmp(i["cmp"], a, b))
            elif o == "fmnmx":
                a, b = bits_f(read(i["a"], rt, pc)), bits_f(read(i["b"], rt, pc))
                is_min = rpred(i["min"][0], rt, pc) != bool(i["min"][1])
                v = b if a != a else a if b != b else (min(a, b) if is_min else max(a, b))
                write(i["d"], issue + LAT_GPR, f_bits(v), pc, issue)
            elif o == "imnmx":
                a, b = read(i["a"], rt, pc), read(i["b"], rt, pc)
                if i["signed"]:
                    a, b = sx(a, 32), sx(b, 32)
                is_min = rpred(i["min"][0], rt, pc) != bool(i["min"][1])
                write(i["d"], issue + LAT_GPR, min(a, b) if is_min else max(a, b), pc, issue)
            elif o == "sel":
                c = rpred(i["cond"][0], rt, pc) != bool(i["cond"][1])
                b = read(i["b"], rt, pc) if i["b"] is not None else i["imm"]
                write(i["d"], issue + LAT_GPR, read(i["a"], rt, pc) if c else b, pc, issue)
            elif o == "mufu":
                var_read((i["a"],), pc, rt, issue)
                v = mufu(i["fn"], bits_f(read(i["a"], rt, pc)), seed)
                write(i["d"], issue + latency("mufu", seed), f_bits(v), pc, issue)
            elif o == "i2f":
                var_read((i["a"],), pc, rt, issue)
                a = read(i["a"], rt, pc)
                if i["rnd"]:
                    raise Unsupported("I2F rounding other than RN")
                write(i["d"], issue + latency("cvt", seed), f_bits(f32(float(sx(a, 32) if i["signed"] else a))), pc, issue)
            elif o == "f2i":
                var_read((i["a"],), pc, rt, issue)
                if i["rnd"] != 3 or i["ftz"]:
                    raise Unsupported("F2I other than toward zero")
                write(i["d"], issue + latency("cvt", seed), f2i(bits_f(read(i["a"], rt, pc)), i["signed"]), pc, issue)
            elif o == "lop3":
                a, c = read(i["a"], rt, pc), read(i["c"], rt, pc)
                b = read(i["b"], rt, pc) if i["b"] is not None else i["imm"]
                write(i["d"], issue + LAT_GPR, lop3(i["lut"], a, b, c), pc, issue)
            elif o == "shf":
                s = i["s"] if i["imm"] else read(i["s"], rt, pc)
                write(i["d"], issue + LAT_GPR, shf(read(i["lo"], rt, pc), s, read(i["hi"], rt, pc), i), pc, issue)
            elif o == "imad.wide":
                if i["signed"]:
                    raise Unsupported("IMAD.WIDE.S32")
                c = 0 if i["c"] == 255 else read(i["c"], rt, pc) | read(i["c"] + 1, rt, pc) << 32
                v = (read(i["a"], rt, pc) * read(i["b"], rt, pc) + c) % 2**64
                write(i["d"], issue + LAT_GPR, v, pc, issue)
                write(i["d"] + 1, issue + LAT_GPR, v >> 32, pc, issue)
            elif o == "sgxt":
                a, bits = read(i["a"], rt, pc), i["bits"]
                v = a if bits >= 32 else 0 if bits == 0 else (sx(a % 2**bits, bits) if i["signed"] else a % 2**bits)
                write(i["d"], issue + LAT_GPR, v, pc, issue)
            elif o in ("ldg", "stg"):
                addr = (read(i["a"], rt, pc) | read(i["a"] + 1, rt, pc) << 32) + i["off"]
                var_read((i["a"], i["a"] + 1) + ((i["v"],) if o == "stg" else ()), pc, rt, issue)
                if o == "ldg":
                    write(i["d"], issue + latency("ldg", seed), mem.load(addr), pc, issue)
                else:
                    mem.store(addr, read(i["v"], rt, pc))
            elif o in ("lds", "sts"):
                addr = (read(i["a"], rt, pc) + i["off"]) % 2**32
                var_read((i["a"],) + ((i["v"],) if o == "sts" else ()), pc, rt, issue)
                if o == "lds":
                    write(i["d"], issue + latency("lds", seed), shared.load(addr, phase, tid), pc, issue)
                else:
                    shared.store(addr, read(i["v"], rt, pc), phase, tid)
            else:
                raise Unsupported(o)
            if var and wr != 7:
                w = regs.get(i.get("d", 255))
                sb_done[wr] = max(sb_done[wr], w[1] if (o not in ("stg", "sts") and w) else issue + 1)
        elif var and wr != 7:
            sb_done[wr] = max(sb_done[wr], issue + 1)
        if var and rd != 7:
            sb_done[rd] = max(sb_done[rd], rt)
        t = issue + stall
        pc = nxt


def run_cta(prog, cbank, mem, ctaid, wg):
    """the threads of one workgroup, each until it reaches BAR or EXIT; a
    barrier releases when every thread that has not exited waits at the
    same one, at the latest arrival"""
    shared = Shared(SHARED_BYTES)
    live = {tid: run_thread(prog, cbank, mem, shared, ctaid, tid) for tid in range(wg)}
    send = {tid: None for tid in live}
    while live:
        at = {}
        for tid in list(live):
            try:
                at[tid] = live[tid].send(send[tid])
            except StopIteration:
                del live[tid]
        if not live:
            return
        if len({pc for pc, _ in at.values()}) != 1:
            raise Hazard(f"workgroup {ctaid}: threads wait at different barriers {sorted({pc for pc, _ in at.values()})}")
        leave = max(c for _, c in at.values())
        send = {tid: leave for tid in live}


def lcg_values(n, seed):
    out = []
    for _ in range(n):
        seed = (seed * 1103515245 + 12345) % 2**31
        out.append(((seed >> 7) % 2**24 - 2**23) / 1024.0)  # 24-bit values, exact in f32
    return out


def run_kernel(prog, op, wg, n):
    """run the program over ceil(n / wg) workgroups; answers None or the first failure"""
    x, y = lcg_values(n, 7 + n), lcg_values(n, 99 + n)
    bases = [0x1_FFFF_F800, 0x2_8000_0000, 0x3_FFFF_FF00, 0x5_0000_0100]  # x and z cross a 4 GiB line
    canary = 16
    data = [bytearray(struct.pack(f"<{n}f", *x)), bytearray(struct.pack(f"<{n}f", *y)),
            bytearray(struct.pack("<I", 0xDEADBEEF) * (n + canary)), bytearray(struct.pack("<I", n))]
    mem = Memory()
    cbank = {}
    for b, (base, d) in enumerate(zip(bases, data)):
        mem.add(base, d)
        cbank[(0, CB_BASE + 8 * b)] = base & 0xFFFFFFFF
        cbank[(0, CB_BASE + 8 * b + 4)] = base >> 32
    try:
        for ctaid in range((n + wg - 1) // wg):
            run_cta(prog, cbank, mem, ctaid, wg)
    except (Hazard, Unsupported, KeyError) as e:
        return f"{type(e).__name__}: {e}"
    z = struct.unpack(f"<{n + canary}I", data[2])
    for k in range(n):
        want = f_bits(f32({"add": x[k] + y[k], "sub": x[k] - y[k], "mul": x[k] * y[k]}[op]))
        if z[k] != want:
            return f"z[{k}] = {z[k]:#010x}, f64 reference {want:#010x}"
    if any(v != 0xDEADBEEF for v in z[n:]):
        return "a word past n was written"
    if bytes(data[0]) != struct.pack(f"<{n}f", *x) or bytes(data[1]) != struct.pack(f"<{n}f", *y):
        return "an input buffer was written"
    return None


def unit_values(n, seed, signed):
    out = []
    for _ in range(n):
        seed = (seed * 1103515245 + 12345) % 2**31
        u = (seed >> 7) / 2**24  # [0, 1)
        out.append(f32(2 * u - 1 if signed else 0.25 + u))
    return out


def run_dot(prog, rows, cols, signed):
    """dot_rows over rows + 1 workgroups (the last one is past the rows and
    must leave at once); answers (None or the first failure, the largest
    relative error)"""
    w = unit_values(rows * cols, 11 + rows * 7919 + cols, signed)
    x = unit_values(cols, 23 + cols, signed)
    canary = 8
    bases = [0x0_7FFF_FFF8, 0x1_FFFF_FF00, 0x2_FFFF_FFC0, 0x4_0000_0040]  # Meta and X cross a 4 GiB line
    data = [bytearray(struct.pack("<2I", rows, cols)), bytearray(struct.pack(f"<{rows * cols}f", *w)),
            bytearray(struct.pack(f"<{cols}f", *x)), bytearray(struct.pack("<I", 0xDEADBEEF) * (rows + canary))]
    keep = [bytes(d) for d in data[:3]]
    mem = Memory()
    cbank = {}
    for b, (base, d) in enumerate(zip(bases, data)):
        mem.add(base, d)
        cbank[(0, CB_BASE + 8 * b)] = base & 0xFFFFFFFF
        cbank[(0, CB_BASE + 8 * b + 4)] = base >> 32
    try:
        for ctaid in range(rows + 1):
            run_cta(prog, cbank, mem, ctaid, 256)
    except (Hazard, Unsupported, KeyError) as e:
        return f"{type(e).__name__}: {e}", None
    o = struct.unpack(f"<{rows + canary}I", data[3])
    worst = 0.0
    for r in range(rows):
        ref = sum(float(w[r * cols + k]) * float(x[k]) for k in range(cols))   # f64
        scale = sum(abs(float(w[r * cols + k]) * float(x[k])) for k in range(cols))
        got = bits_f(o[r])
        err = abs(got - ref) / scale if scale else abs(got - ref)
        worst = max(worst, err)
        if not err <= DOT_TOL:
            return f"o[{r}] = {got!r}, f64 reference {ref!r} (relative error {err:.3g})", worst
    if any(v != 0xDEADBEEF for v in o[rows:]):
        return "a word past the rows was written", worst
    if [bytes(d) for d in data[:3]] != keep:
        return "an input buffer was written", worst
    return None, worst


# ---------------------------------------------------------------------------
# The decode kernels (JUN-739): nex_ops.comp's ops as KIR v2 lowers them
# (kir2-nex-op). Bindings: 0 Meta {n rows aux aux2 : u32, eps scale p0 p1 :
# f32}, 1 a, 2 b, 3 c, 4 o, 5 s (f32), 6 ids (u32); LocalSize 256. Each case
# runs the program over its grid and compares every word it may write with
# the f64 reference (rounded to f32 where the op is exact), and every other
# word of every buffer with what it held before.

NEX_TOL = 1e-3   # |got - f64 reference| / |reference|, the gate of JUN-739
NEX_CANARY = 8
NEX_BASES = [0x0_7FFF_FFF0, 0x1_FFFF_FF00, 0x2_FFFF_FFC0, 0x3_FFFF_F000, 0x4_FFFF_FE00, 0x5_FFFF_FFF8, 0x6_FFFF_FFF0]


def nex_vals(n, seed, lo, hi):
    out = []
    for _ in range(n):
        seed = (seed * 1103515245 + 12345) % 2**31
        out.append(f32(lo + (hi - lo) * ((seed >> 7) / 2**24)))
    return out


def silu(x):
    return x / (1.0 + math.exp(-x))


def run_nex_case(prog, gate, case):
    """answers (None or the first failure, the largest relative error)"""
    meta = case["meta"]
    bufs = {b: list(v) for b, v in case["bufs"].items()}
    sizes = {b: len(bufs.get(b, [])) for b in range(1, 7)}
    data = [bytearray(struct.pack("<4I4f", *meta[:4], *meta[4:]))]
    for b in range(1, 7):
        v = bufs.get(b, [])
        fmt = "I" if b == 6 else "f"
        data.append(bytearray(struct.pack(f"<{len(v)}{fmt}", *v) + struct.pack("<I", 0xDEADBEEF) * NEX_CANARY))
    before = [bytes(d) for d in data]
    mem = Memory()
    cbank = {}
    for b, (base, d) in enumerate(zip(NEX_BASES, data)):
        mem.add(base, d)
        cbank[(0, CB_BASE + 8 * b)] = base & 0xFFFFFFFF
        cbank[(0, CB_BASE + 8 * b + 4)] = base >> 32
    try:
        for ctaid in range(case["grid"]):
            run_cta(prog, cbank, mem, ctaid, 256)
    except (Hazard, Unsupported, KeyError) as e:
        return f"{type(e).__name__}: {e}", None
    want = case["want"]   # binding -> {index: (value, exact)}
    worst = 0.0
    for b in range(7):
        n = sizes.get(b, 0)
        words = struct.unpack(f"<{len(data[b]) // 4}I", data[b])
        old = struct.unpack(f"<{len(before[b]) // 4}I", before[b])
        for k in range(len(words)):
            w = want.get(b, {}).get(k)
            if w is None:
                if words[k] != old[k]:
                    return f"binding {b} word {k} written ({old[k]:#x} -> {words[k]:#x})", worst
                continue
            ref, exact = w
            if b == 6:
                if words[k] != ref % 2**32:
                    return f"ids[{k}] = {words[k]}, reference {ref}", worst
                continue
            got = bits_f(words[k])
            if exact:
                if words[k] != f_bits(f32(ref)):
                    return f"binding {b}[{k}] = {got!r}, reference {f32(ref)!r} (exact)", worst
                continue
            err = abs(got - ref) / abs(ref) if ref else abs(got)
            worst = max(worst, err)
            if not err <= NEX_TOL:
                return f"binding {b}[{k}] = {got!r}, f64 reference {ref!r} (relative error {err:.3g})", worst
    return None, worst


def nex_meta(n=0, rows=0, aux=0, aux2=0, eps=0.0, scale=0.0, p0=0.0, p1=0.0):
    return [n, rows, aux, aux2, eps, scale, p0, p1]


def case_add(n):
    a, b = nex_vals(n, 3 + n, -4, 4), nex_vals(n, 5 + n, -4, 4)
    return {"label": f"n={n}", "meta": nex_meta(n), "grid": (n + 255) // 256, "bufs": {1: a, 2: b, 4: [0.0] * n},
            "want": {4: {i: (a[i] + b[i], True) for i in range(n)}}}


def case_add_bias(n, aux):
    a, b = nex_vals(n, 7 + n, -4, 4), nex_vals(aux, 9 + aux, -1, 1)
    return {"label": f"n={n} aux={aux}", "meta": nex_meta(n, 0, aux), "grid": (n + 255) // 256,
            "bufs": {1: a, 2: b, 4: [0.0] * n}, "want": {4: {i: (a[i] + b[i % aux], True) for i in range(n)}}}


def case_silu_mul(n):
    a, b = nex_vals(n, 11 + n, -12, 12), nex_vals(n, 13 + n, -3, 3)
    return {"label": f"n={n}", "meta": nex_meta(n), "grid": (n + 255) // 256, "bufs": {1: a, 2: b, 4: [0.0] * n},
            "want": {4: {i: (silu(a[i]) * b[i], False) for i in range(n)}}}


def case_copy_at(n, aux2, dyn, pos):
    a = nex_vals(n, 17 + n, -2, 2)
    rows = 4 * aux2 // max(n, 1) + 2
    size = (pos + 2) * aux2 + n
    off = pos * aux2 if dyn else aux2
    return {"label": f"n={n} aux2={aux2} {'dyn pos ' + str(pos) if dyn else 'static'}",
            "meta": nex_meta(n, rows, 0, aux2, 0.0, 0.0, 0.0, 1.0 if dyn else 0.0), "grid": (n + 255) // 256,
            "bufs": {1: a, 4: [0.0] * size, 6: [pos, 77]}, "want": {4: {off + i: (a[i], True) for i in range(n)}}}


def case_pos_incr(pos):
    return {"label": f"pos={pos}", "meta": nex_meta(1), "grid": 2, "bufs": {6: [pos, 5]}, "want": {6: {0: (pos + 1, True)}}}


def case_rmsnorm(n, rows, aux, eps):
    stride = aux or n
    a = nex_vals(rows * stride, 19 + n + rows, -3, 3)
    b = nex_vals(n, 23 + n, 0.5, 1.5)
    want = {}
    for r in range(rows):
        ss = sum(float(a[r * stride + i]) ** 2 for i in range(n))
        inv = 1.0 / math.sqrt(ss / n + eps)
        for i in range(n):
            want[r * n + i] = (a[r * stride + i] * inv * b[i], False)
    return {"label": f"n={n} rows={rows} aux={aux}", "meta": nex_meta(n, 0, aux, 0, eps), "grid": rows,
            "bufs": {1: a, 2: b, 4: [0.0] * (rows * n)}, "want": {4: want}}


def case_add_rmsnorm(n, rows, eps):
    a, b = nex_vals(rows * n, 29 + n, -3, 3), nex_vals(rows * n, 31 + n, -1, 1)
    c = nex_vals(n, 37 + n, 0.5, 1.5)
    want_o, want_s = {}, {}
    for r in range(rows):
        v = [f32(a[r * n + i] + b[r * n + i]) for i in range(n)]
        inv = 1.0 / math.sqrt(sum(float(x) ** 2 for x in v) / n + eps)
        for i in range(n):
            want_o[r * n + i] = (v[i], True)
            want_s[r * n + i] = (v[i] * inv * c[i], False)
    return {"label": f"n={n} rows={rows}", "meta": nex_meta(n, 0, 0, 0, eps), "grid": rows,
            "bufs": {1: a, 2: b, 3: c, 4: [0.0] * (rows * n), 5: [0.0] * (rows * n)}, "want": {4: want_o, 5: want_s}}


# Qwen2.5-0.5B's widths: hidden 896, KV row 128 (2 heads of 64), FFN 4864
NEX_GATES = {
    "nex-add": {"cases": [case_add(896), case_add(256), case_add(1)]},
    "nex-add-bias": {"cases": [case_add_bias(896, 896), case_add_bias(1000, 7), case_add_bias(300, 1),
                               case_add_bias(1100, 128)]},
    "nex-silu-mul": {"cases": [case_silu_mul(1100), case_silu_mul(1)]},
    "nex-copy-at": {"cases": [case_copy_at(128, 128, True, 0), case_copy_at(128, 128, True, 5),
                              case_copy_at(300, 320, False, 3)]},
    "nex-pos-incr": {"cases": [case_pos_incr(0), case_pos_incr(41)]},
    "nex-rmsnorm": {"cases": [case_rmsnorm(896, 2, 0, 1e-6), case_rmsnorm(64, 3, 128, 1e-6), case_rmsnorm(300, 1, 0, 1e-5)]},
    "nex-add-rmsnorm": {"cases": [case_add_rmsnorm(896, 1, 1e-6), case_add_rmsnorm(200, 2, 1e-6)]},
}


def check_rapred(prog):
    """the allocator's hand-written case (sm70_lower_test.kotoba rapred): two
    predicates live at once get two registers, each SEL reads its own, and
    the two compared values two GPRs"""
    ops = [i["op"] for i in prog]
    if ops[:7] != ["mov.imm", "mov.imm", "isetp", "isetp", "sel", "sel", "iadd3"]:
        return f"unexpected program {ops}"
    p0, p1 = prog[2]["pd"], prog[3]["pd"]
    if p0 == p1 or prog[4]["cond"] != (p0, 0) or prog[5]["cond"] != (p1, 0):
        return f"predicates {p0}, {p1}; SEL conditions {prog[4]['cond']}, {prog[5]['cond']}"
    if prog[0]["d"] == prog[1]["d"]:
        return f"both values in R{prog[0]['d']}"
    return None


def check_control(prog):
    """the static rules the interpreter does not time: every BSSY reconverges
    at a BSYNC on its barrier; BAR is followed by NOP, BAR stalls 5 cycles
    (NAK exec_latency) and the NOP 2; BAR and BSYNC yield (NAK needs_yield)"""
    for k, i in enumerate(prog):
        o, (stall, yld, *_rest) = i["op"], i["ctl"]
        if o == "bssy":
            t = k + 1 + i["rel"]
            if not (0 <= t < len(prog) and prog[t]["op"] == "bsync" and prog[t]["bar"] == i["bar"]):
                return f"BSSY at {k} reconverges at {t}, not at a BSYNC B{i['bar']}"
        if o == "bar" and (stall < 5 or not yld or k + 1 >= len(prog) or prog[k + 1]["op"] != "nop"
                           or prog[k + 1]["ctl"][0] < 2):
            return f"BAR at {k}: stall {stall}, yield {yld}, not followed by a NOP of 2"
        if o == "bsync" and not yld:
            return f"BSYNC at {k} does not yield"
    return None


# ---------------------------------------------------------------------------


def judge(progs, dot_cases=None):
    """the failures of a lowering run against every expectation"""
    bad = []
    for name, (err, op) in EXPECT_REFUSED.items():
        p = progs.get(name)
        if not p or (p["error"], p["op"], p["count"]) != (err, op, 0):
            bad.append(f"{name}: not refused as {err}/{op}: {p and (p['error'], p['op'], p['count'])}")
    decoded = {}
    for name in list(KERNELS) + ["dot-rows", "war", "loopwar", "rapred"] + list(NEX_GATES):
        p = progs.get(name)
        if not p or p["error"] != 0:
            bad.append(f"{name}: refused {p and p['error']}")
            continue
        try:
            d = [decode(lo, hi) for lo, hi in p["words"]]
            for k, (i, w) in enumerate(zip(d, p["words"])):
                if reencode(i) != w:
                    bad.append(f"{name}.{k}: not the NAK encoding of its decoding")
        except Unsupported as e:
            bad.append(f"{name}: {e}")
            continue
        decoded[name] = d
    for name, want in (("war", WAR_CTL), ("loopwar", LOOPWAR_CTL)):
        if name in decoded:
            got = [i["ctl"][:5] for i in decoded[name]]
            if got != [tuple(c) for c in want]:
                bad.append(f"{name}: control bits {got}")
    if "rapred" in decoded:
        r = check_rapred(decoded["rapred"])
        if r:
            bad.append(f"rapred: {r}")
    for name, (op, wg) in KERNELS.items():
        if name in decoded:
            for n in SIZES:
                r = run_kernel(decoded[name], op, wg, n)
                if r:
                    bad.append(f"{name} n={n}: {r}")
    errors = {}
    if "dot-rows" in decoded:
        c = check_control(decoded["dot-rows"])
        if c:
            bad.append(f"dot-rows: {c}")
        for rows, cols, signed in (DOT_CASES if dot_cases is None else dot_cases):
            r, e = run_dot(decoded["dot-rows"], rows, cols, signed)
            errors[f"{rows}x{cols}{' signed' if signed else ''}"] = e
            if r:
                bad.append(f"dot-rows {rows}x{cols}: {r}")
    nex_errors = {}
    for name, gate in NEX_GATES.items():
        if name in decoded:
            c = check_control(decoded[name])
            if c:
                bad.append(f"{name}: {c}")
            for case in gate["cases"]:
                r, e = run_nex_case(decoded[name], gate, case)
                nex_errors[f"{name} {case['label']}"] = e
                if r:
                    bad.append(f"{name} {case['label']}: {r}")
    judge.errors = errors
    judge.nex_errors = nex_errors
    return bad, decoded


def set_ctl(word, field, value):
    lo, hi = word
    b = lo | hi << 64
    start, width = {"stall": (105, 4), "wr": (110, 3), "wait": (116, 6)}[field]
    b = (b & ~(((1 << width) - 1) << start)) | (value << start)
    return b & (2**64 - 1), b >> 64


LOWER = "tools/c/sm70/sm70_lower.kotoba"
SCHED = "tools/c/sm70/sm70_sched.kotoba"
LOWER_MUTANTS = [
    ("ult-as-ule", LOWER, "176 1 177", "176 3 177"),
    ("binding-stride", LOWER, "(* 8 (dget D n 0 var))", "(* 4 (dget D n 0 var))"),
    ("element-stride", LOWER, "(tset T id 13 base off ix 4)", "(tset T id 13 base off ix 8)"),
    ("unguarded", LOWER, "(mi-add Q op (lg L 2) d a b c x y)", "(mi-add Q op (mi-g 7 0) d a b c x y)"),
    ("fadd-as-fmul", LOWER, "(= op SP-FADD) (binop W T Q L at MI-FADD)", "(= op SP-FADD) (binop W T Q L at MI-FMUL)"),
    ("gid-without-ctaid", LOWER, "(add Q L MI-IMADI r c 0 t (lg L 7) 0)", "(add Q L MI-IMADI r c 0 t 0 0)"),
    ("member-offset", LOWER, "o (ls L 11 (tg T p 2))", "o (ls L 11 (+ 4 (tg T p 2)))"),
    ("loop-exit-not-inverted", LOWER, "(= nl tl) (branch Q (mi-g (tg T c 1) 1) fl)", "(= nl tl) (branch Q (mi-g (tg T c 1) 0) fl)"),
    ("barrier-as-nop", LOWER, "(let [a (add Q L MI-BAR 0 0 0 0 0 0)]", "(let [a (add Q L MI-NOP 0 0 0 0 0 0)]"),
    ("shared-stride", LOWER, "(add Q L MI-IMADI r (vreg T ix) 0 255 4 0)", "(add Q L MI-IMADI r (vreg T ix) 0 255 8 0)"),
    ("shared-const-offset", LOWER, "(tset T id 17 (+ off (* 4 (tg T ix 2))) -1 0 0)", "(tset T id 17 (+ 4 off (* 4 (tg T ix 2))) -1 0 0)"),
    ("header-not-moved", LOWER, "h (tset T hd 14 (mi-count Q) 0 0 0)", "h 0"),
    ("no-bsync", LOWER, "y (if (>= merge-bar 0) (add Q L MI-BSYNC merge-bar 0 0 0 0 0) 0)", "y 0"),
    ("var-store-lost", LOWER, "(cond (>= v 0) (add Q L MI-MOV (tg T p 3) v 0 0 0 0)", "(cond (>= v 0) (add Q L MI-MOV 255 v 0 0 0 0)"),
    ("shift-amount", LOWER, "(add Q L (if right MI-SHR MI-SHLI) r a 0 0 (tg T bid 2) 0)",
     "(add Q L (if right MI-SHR MI-SHLI) r a 0 0 (+ 1 (tg T bid 2)) 0)"),
    # JUN-739: the decode kernels' operations
    ("udiv-nir-margin", LOWER, "(def SL-RCP-SCALE 0x4f7ffff8)", "(def SL-RCP-SCALE 0x4f7ffffe)"),
    ("fdiv-reciprocal-of-numerator", LOWER, "(add Q L MI-MUFU r b 0 0 SL-RCP 0) q (gpr Q L) e (add Q L MI-FMUL q a r 0 0 0)",
     "(add Q L MI-MUFU r a 0 0 SL-RCP 0) q (gpr Q L) e (add Q L MI-FMUL q b r 0 0 0)"),
    ("exp-without-log2e", LOWER, "(mufu1 Q L SL-EX2 (fmuli Q L a SL-LOG2E))", "(mufu1 Q L SL-EX2 a)"),
    ("inversesqrt-as-rcp", LOWER, "(= func 32) (mufu1 Q L SL-RSQ a)", "(= func 32) (mufu1 Q L SL-RCP a)"),
    ("fneg-keeps-sign", LOWER, "(add Q L MI-FADDN r 255 a 0 0 3)", "(add Q L MI-FADDN r 255 a 0 0 1)"),
    ("isub-as-iadd", LOWER, "(= mop SP-ISUB) (add Q L MI-IADD3 r a b 255 0 2)", "(= mop SP-ISUB) (add Q L MI-IADD3 r a b 255 0 0)"),
    ("funord-ne-as-eq", LOWER, "182 5 183 13", "182 5 183 2"),
    ("u2f-as-f2u", LOWER, "(cond (= op SP-UTOF) (add Q L MI-I2F r a 0 0 0 0)", "(cond (= op SP-UTOF) (add Q L MI-F2I r a 0 0 0 0)"),
    ("select-arms-swapped", LOWER, "(add Q L MI-SEL r a b 0 (tg T c 1) 0)", "(add Q L MI-SEL r b a 0 (tg T c 1) 0)"),
]
REGALLOC = "tools/c/sm70/sm70_regalloc.kotoba"
REGALLOC_MUTANTS = [
    ("ra-no-interference", REGALLOC,
     "(loop [x 0] (if (>= x nn) 0 (let [y (if (bget O (* k w) x) (interfere I w d x) 0)] (recur (inc x))))))", "0)"),
    ("ra-variable-latency-sources", REGALLOC,
     "(not (or (= op MI-S2R) (= op MI-LDG) (= op MI-LDS) (= op MI-MUFU) (= op MI-I2F) (= op MI-F2I)))", "true"),
    ("ra-guarded-write-kills", REGALLOC, "(if (and unguarded (not= (vector-at N (- v RA-V0)) 3)) (bset K (* k w) nd) 0)",
     "(if (not= (vector-at N (- v RA-V0)) 3) (bset K (* k w) nd) 0)"),
    ("ra-no-back-edge", REGALLOC, "(and (= op MI-BRA) unguarded) tgt", "(and (= op MI-BRA) unguarded) (+ k 1)"),
    ("ra-pred-no-interference", REGALLOC,
     "(loop [x 0] (if (>= x np) 0 (let [y (if (bget O (* k pw) x) (interfere I pw d x) 0)] (recur (inc x))))))", "0)"),
]
SCHED_MUTANTS = [
    ("no-wait-mask", SCHED, "(mi-set Q k 8 (bit-or (i64-shift-left m 16)", "(mi-set Q k 8 (bit-or (i64-shift-left 0 16)"),
    ("no-write-barrier", SCHED, "wr (if (and (mi-var? op) (>= (mi-dst Q k 0) 0)) (take-sb S) 7)", "wr 7"),
    ("no-read-barrier", SCHED, "(and (mi-var? op) (src-rewritten? Q k))", "(and (mi-var? op) false)"),
    ("gpr-latency-5", SCHED, "(def MI-LAT-GPR 6)", "(def MI-LAT-GPR 5)"),
    ("pred-latency-6", SCHED, "(def MI-LAT-PRED 13)", "(def MI-LAT-PRED 6)"),
    ("no-branch-drain", SCHED, "(or (and (= op MI-BRA) (not= (mi-target Q k) k)) (= op MI-EXIT))", "(= op MI-EXIT)"),
    ("no-back-edge-read-barrier", SCHED, "(and (= (mi-op Q j) MI-BRA) (<= (mi-target Q j) k)", "(and false (<= (mi-target Q j) k)"),
    ("bar-exec-latency-1", SCHED, "(cond (= op MI-BAR) 5", "(cond (= op MI-BAR) 1"),
    ("no-bar-yield", SCHED, "(or (= op MI-EXIT) (= op MI-BAR) (= op MI-BSYNC))", "(or (= op MI-EXIT) (= op MI-BSYNC))"),
    # JUN-739
    ("mufu-fixed-latency", SCHED, "(= op MI-STS) (= op MI-MUFU) (= op MI-I2F)", "(= op MI-STS) (= op MI-I2F)"),
    ("sel-predicate-not-waited", SCHED, "ps (mi-psrc Q k) t1", "ps -1 t1"),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--amu", default=str(ROOT / "bin/amu"))
    ap.add_argument("--receipt")
    args = ap.parse_args()
    ok = True
    files = [MODULES_UNIT[0], LOWER_UNIT[0], *[ROOT / m for m in MODULES_UNIT[1] + LOWER_UNIT[1]],
             ROOT / "scripts/seed/check-sm70-encode.py"]
    report: dict[str, object] = {
        "schema": "amu.sm70-lower-check.v1",
        "sources": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in dict.fromkeys(files)},
        "amu": hashlib.sha256(Path(args.amu).resolve().read_bytes()).hexdigest()}

    with tempfile.TemporaryDirectory(prefix="sm70-lower-") as work:
        out, mh = run_unit(args.amu, unit_text(*MODULES_UNIT), work, "modules")
        lines = out.rstrip("\n").split("\n")
        modules = {f[1]: [int(w) for w in f[2:]] for f in (l.split() for l in lines[:-1])}
        assert int(lines[-1]) == len(modules) == 5 + len(NEX_GATES), lines[-1]
        report["modules"] = {k: hashlib.sha256(struct.pack(f"<{len(v)}I", *v)).hexdigest() for k, v in modules.items()}
        print(f"modules: {', '.join(f'{k} ({len(v)} words)' for k, v in modules.items())}")
        margs = module_args(modules)

        text = unit_text(*LOWER_UNIT)
        out1, uh = run_unit(args.amu, text, work, "lower-1", margs)
        out2, _ = run_unit(args.amu, text, work, "lower-2", margs)
        same = out1 == out2
        print(f"determinism: two runs {'identical' if same else 'DIFFER'} ({hashlib.sha256(out1.encode()).hexdigest()[:16]})")
        ok &= same
        progs = parse_programs(out1)
        bad, decoded = judge(progs)
        print(f"lowering: {', '.join(f'{k} {len(p['words'])} words' if not p['error'] else f'{k} refused {p['error']}/{p['op']}' for k, p in progs.items())}")
        print(f"interpreter: {len(KERNELS)} kernels x sizes {SIZES}; failures {bad or 'none'}")
        ok &= not bad
        report.update(unit=uh, output=hashlib.sha256(out1.encode()).hexdigest(), failures=bad,
                      programs={k: [f"{lo:016x}{hi:016x}" for lo, hi in p["words"]] for k, p in progs.items()})
        for k, d in decoded.items():
            if k not in ("war", "loopwar"):
                print(f"  {k}: " + " ".join(i["op"] for i in d))
        errs = getattr(judge, "errors", {})
        print(f"dot-rows: largest relative error per case (tolerance {DOT_TOL}): "
              + ", ".join(f"{k} {v:.2e}" if v is not None else f"{k} none" for k, v in errs.items()))
        report["dot_rows_errors"] = errs
        report["dot_cases"] = DOT_CASES
        nerrs = getattr(judge, "nex_errors", {})
        print(f"decode kernels: largest relative error per case (tolerance {NEX_TOL}, exact cases 0): "
              + ", ".join(f"{k} {v:.2e}" if v is not None else f"{k} none" for k, v in nerrs.items()))
        report["decode_errors"] = nerrs

        # control: corrupted control bits and one operand bit in the emitted words
        base = progs["ewise-add-wg256"]["words"]
        ops = [i["op"] for i in decoded["ewise-add-wg256"]]
        isetp, ldg_x = ops.index("isetp"), ops.index("ldg", ops.index("isetp"))
        controls = [
            ("isetp-no-wait", isetp, lambda w: set_ctl(w, "wait", 0)),
            ("isetp-stall-6", isetp, lambda w: set_ctl(w, "stall", 6)),
            ("ldg-no-write-barrier", ldg_x, lambda w: set_ctl(w, "wr", 7)),
            ("mov-cb-offset-bit", ops.index("mov.cb", isetp), lambda w: (w[0] ^ (1 << 41), w[1])),
        ]
        dbase = progs["dot-rows"]["words"]
        dops = [i["op"] for i in decoded["dot-rows"]]
        bars = [k for k, o in enumerate(dops) if o == "bar"]
        bras = [k for k, o in enumerate(dops) if o == "bra"]
        ldss = [k for k, o in enumerate(dops) if o == "lds"]
        nop_word = NAK.op_nop((7, False), (0, 0, 7, 7, 0, 0))
        dcontrols = [
            ("dot-first-bar-as-nop", bars[0], lambda w: nop_word),
            ("dot-tree-bar-as-nop", bars[1], lambda w: nop_word),
            ("dot-loop-exit-not-inverted", bras[0], lambda w: (w[0] ^ (1 << 15), w[1])),
            # the loop variable's MOV before the back edge: R0 is read again at the header
            ("dot-back-edge-stall-1", bras[1] - 1, lambda w: set_ctl(w, "stall", 1)),
            ("dot-lds-no-write-barrier", ldss[0], lambda w: set_ctl(w, "wr", 7)),
            ("dot-bssy-target", dops.index("bssy"), lambda w: (w[0] ^ (1 << 36), w[1])),
        ]
        nops = {n: [i["op"] for i in decoded[n]] for n in ("nex-rmsnorm", "nex-add-bias", "nex-silu-mul")}
        ncontrols = [
            # MUFU.RSQ -> MUFU.RCP (function field 74..79: 5 -> 4)
            ("nex-rmsnorm:rsq-as-rcp", nops["nex-rmsnorm"].index("mufu"), lambda w: (w[0], w[1] ^ (1 << (74 - 64)))),
            # the division's first quotient fix-up compares nothing: ISETP.GE -> ISETP.LT
            ("nex-add-bias:udiv-fixup-cmp", nops["nex-add-bias"].index("isetp", 8), lambda w: (w[0], w[1] ^ (7 << (76 - 64)))),
            # the MUFU.EX2 result read without waiting for its scoreboard
            ("nex-silu-mul:ex2-no-wait", nops["nex-silu-mul"].index("mufu") + 1, lambda w: set_ctl(w, "wait", 0)),
        ]
        ctl_report = []
        for cname, k, fn in ncontrols:
            name = cname.split(":")[0]
            words = list(progs[name]["words"])
            words[k] = fn(words[k])
            try:
                prog = [decode(lo, hi) for lo, hi in words]
                r = None
                for case in NEX_GATES[name]["cases"]:
                    r = r or run_nex_case(prog, NEX_GATES[name], case)[0]
            except Unsupported as e:
                r = f"Unsupported: {e}"
            ctl_report.append({"control": cname, "instr": k, "detected": r})
            print(f"control {cname} (instr {k}): {'detected' if r else 'NOT DETECTED'} ({r})")
            ok &= bool(r)
        for cname, k, fn in controls + dcontrols:
            words = list(dbase if cname.startswith("dot-") else base)
            words[k] = fn(words[k])
            try:
                prog = [decode(lo, hi) for lo, hi in words]
                if cname.startswith("dot-"):
                    r = check_control(prog)
                    for rows, cols, signed in DOT_CASES[:2]:
                        r = r or run_dot(prog, rows, cols, signed)[0]
                else:
                    r = run_kernel(prog, "add", 256, 1000)
            except Unsupported as e:
                r = f"Unsupported: {e}"
            ctl_report.append({"control": cname, "instr": k, "detected": r})
            print(f"control {cname} (instr {k}): {'detected' if r else 'NOT DETECTED'} ({r})")
            ok &= bool(r)

        muts = []
        for mname, path, old, new in LOWER_MUTANTS + SCHED_MUTANTS + REGALLOC_MUTANTS:
            try:
                mo, mhash = run_unit(args.amu, unit_text(*LOWER_UNIT, replace=(path, old, new)), work, f"mutant-{mname}", margs)
                mb, _ = judge(parse_programs(mo))
            except (RuntimeError, AssertionError) as e:
                mb, mhash = [f"build/run: {e}"], None
            muts.append({"mutant": mname, "file": path, "unit": mhash, "detected": mb})
            print(f"mutant {mname}: {'detected' if mb else 'NOT DETECTED'} ({len(mb)}: {'; '.join(mb[:2])[:160]})")
            ok &= bool(mb) and mhash is not None
        report.update(controls=ctl_report, mutants=muts)

    report["ok"] = bool(ok)
    if args.receipt:
        Path(args.receipt).write_text(json.dumps(report, indent=1) + "\n")
    print("sm70-lower: PASS" if ok else "sm70-lower: FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
