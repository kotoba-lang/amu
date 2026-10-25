#!/usr/bin/env python3
"""ADR 0372 step 4 and ADR 0371 step 6's acceptance: the KIR v2 kernels on real
tensors, through the product route (a static guest, the static launcher and
the Vulkan provider), against the hand-written kernels and an f64 oracle.

Phases:
  fixtures  on the GPU host: the tensors, cut from the files that hold them,
            and the activation x; their digests and sources (fixtures.json)
  ref       on the developer host: f64 dequant references, stdlib only
            (Python is the test oracle here, never the product route)
  build     on Linux: one static guest per fixture, compiled by the pinned
            root, beside the launcher and provider images and the kernels
  run       on the GPU host: each guest under the launcher; KIR v2 and
            glslang's module on the same tensor, compared byte for byte, timed,
            and checked against the f64 reference; the lm_head's argmax chain
            against the f64 argmax

The fixtures (kotoba-lang/inference verify/native/gpu/kdot_check.py names the
first four by their byte counts):
  attn_qkv       Q5_K   8192 x 2048   /root/kdot/attn_qkv.q5k.bin
  attn_gate      IQ4_XS 4096 x 2048   /root/kdot/attn_gate.iq4xs.bin
  ffn_gate_exp0  IQ4_XS  512 x 2048   expert 0 of /root/kdot/ffn_gate_exps.iq4xs.bin
  output         Q6_K 248320 x 2048   output.weight of Qwen3.6-35B-A3B-Q4_K_M.gguf
  attn_gate_q4k  Q4_K   4096 x 2048   blk.0.attn_gate.weight of the same GGUF
  ffn_gate_inp   F32     256 x 2048   blk.0.ffn_gate_inp.weight (the MoE router), the dot fixture
"""
import argparse
import hashlib
import json
import math
import multiprocessing
import operator
import platform
import re
import shutil
import struct
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COLS = 2048
# name, ggml type, rows, bytes, and the source: (kdot file, offset) or (GGUF tensor)
FIXTURES = [
    dict(name="attn_qkv", tt=13, rows=8192, nbytes=11534336, kdot="attn_qkv.q5k.bin", offset=0),
    dict(name="attn_gate", tt=23, rows=4096, nbytes=4456448, kdot="attn_gate.iq4xs.bin", offset=0),
    dict(name="ffn_gate_exp0", tt=23, rows=512, nbytes=557056, kdot="ffn_gate_exps.iq4xs.bin", offset=0),
    dict(name="output", tt=14, rows=248320, nbytes=417177600, tensor="output.weight"),
    dict(name="attn_gate_q4k", tt=12, rows=4096, nbytes=4718592, tensor="blk.0.attn_gate.weight"),
    dict(name="ffn_gate_inp", tt=0, rows=256, nbytes=2097152, tensor="blk.0.ffn_gate_inp.weight"),
]
# bytes per 256 values (0: F32)
BLOCK = {0: 1024, 12: 144, 13: 176, 14: 210, 23: 136}
# the layouts each fixture runs: name, the KIR v2 module, glslang's module, rows a workgroup
LAYOUTS = {"r1": ("kir2-kdot-f32-r1.spv", "ref-kdot-f32-r1.spv", 1),
           "r8": ("kir2-kdot-f32-r8.spv", "ref-kdot-f32-r8.spv", 8),
           "x8r4": ("kir2-kdot-x8r4.spv", "ref-kdot-x8r8-rows4.spv", 4),
           "h2r1": ("kir2-kdot-h2-r1.spv", "ref-kdot-h2-r1.spv", 1),
           "h2q6r1": ("kir2-kdot-h2-r1-q6half.spv", "ref-kdot-h2-r1-q6half.spv", 1),
           "dot": ("kir2-dot-rows.spv", "ref-dot-rows.spv", 1)}
DEFAULT_LAYOUTS = ["r1", "r8", "x8r4", "h2r1"]
# the guests: name -> (fixture, layouts). The lm_head runs the decode tables' lm kernels (anv x8r4,
# radv r1, nvgpu h2q6r1) and the argmax chain on its first layout's logits. r1 and h2q6r1 take one
# workgroup per row, 248320 of them: past Vulkan's guaranteed maxComputeWorkGroupCount (65535, which
# ANV has), so they are their own guest, run only with --max-workgroups above it
GUESTS = {"attn_qkv": ("attn_qkv", DEFAULT_LAYOUTS), "attn_gate": ("attn_gate", DEFAULT_LAYOUTS),
          "ffn_gate_exp0": ("ffn_gate_exp0", DEFAULT_LAYOUTS), "attn_gate_q4k": ("attn_gate_q4k", DEFAULT_LAYOUTS),
          "output": ("output", ["x8r4", "r8"]), "output_wide": ("output", ["r1", "h2q6r1"]),
          "ffn_gate_inp": ("ffn_gate_inp", ["dot"])}
VULKAN_MIN_WORKGROUPS = 65535


def guest_workgroups(f, layouts):
    """the largest workgroup count of the guest's dispatches"""
    return max(-(-f["rows"] // LAYOUTS[lay][2]) for lay in layouts)
ARGMAX = [("kir2-nex-argmax_partial.spv", "ref-nex-ops-argmax_partial.spv"), ("kir2-nex-argmax_final.spv", "ref-nex-ops-argmax_final.spv")]
# the numeric gates. f32 layouts: kdot_check.py's max |got - ref| / max(|ref|, 1e-2) <= 1e-3. The h2
# layouts compute their products in f16, so that metric (whose 1e-2 floor divides small, cancelling rows
# by little) is not theirs: max |got - ref| / rms(ref) <= 1e-2. Both are recorded for every layout.
REL_MAX = {"r1": 1e-3, "r8": 1e-3, "x8r4": 1e-3, "dot": 1e-3}
RMS_MAX = {"h2r1": 1e-2, "h2q6r1": 1e-2}
# the speed gate: the median of KIR v2's ROUNDS 10-dispatch command buffers (alternating with
# glslang's) within SPEED_MAX of glslang's median, where glslang's median buffer takes SPEED_MIN_NS or
# more; shorter ones are launch-bound, their ratio is noise, and they are recorded without the gate
ROUNDS = 7
SPEED_MAX = 1.25
SPEED_MIN_NS = 500000
WALL = 300


def pin(path):
    h, n = hashlib.sha256(), 0
    with open(path, "rb") as f:
        while True:
            b = f.read(1 << 24)
            if not b:
                break
            h.update(b)
            n += len(b)
    return {"bytes": n, "sha256": h.hexdigest()}


def lcg(n, seed):
    """n values in [-1, 1) with 24 significant bits (exact in f32) from a fixed LCG."""
    out, x = [], seed
    for _ in range(n):
        x = (x * 6364136223846793005 + 1442695040888963407) % (1 << 64)
        out.append((x >> 40) / float(1 << 23) - 1.0)
    return out


def gguf_dir(path):
    """The GGUF's tensor directory: {name: (type, dims, absolute offset)}, and the header's length."""
    with open(path, "rb") as f:
        r = f.read

        def u32():
            return struct.unpack("<I", r(4))[0]

        def u64():
            return struct.unpack("<Q", r(8))[0]

        def s():
            return r(u64()).decode()

        def val(t):
            if t == 8:
                return s()
            if t == 9:
                et, n = u32(), u64()
                return [val(et) for _ in range(n)]
            b = r({0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}[t])
            return int.from_bytes(b, "little") if t in (0, 2, 4, 7, 10) else b
        assert r(4) == b"GGUF"
        u32()
        nt, nkv = u64(), u64()
        kv = {}
        for _ in range(nkv):
            k = s()
            kv[k] = val(u32())
        tensors = {}
        for _ in range(nt):
            name = s()
            dims = [u64() for _ in range(u32())]
            typ, off = u32(), u64()
            tensors[name] = (typ, dims, off)
        align = kv.get("general.alignment", 32)
        start = (f.tell() + align - 1) // align * align
    return {n: (t, d, start + o) for n, (t, d, o) in tensors.items()}, start


def fixtures(output, kdot_dir, gguf):
    out = output / "fixtures"
    out.mkdir(parents=True, exist_ok=False)
    tensors, header = gguf_dir(gguf)
    with open(gguf, "rb") as f:
        head = f.read(header)
    rows = {}
    for fx in FIXTURES:
        if "tensor" in fx:
            typ, dims, off = tensors[fx["tensor"]]
            assert typ == fx["tt"] and dims == [COLS, fx["rows"]], (fx["name"], typ, dims)
            src, source = gguf, dict(gguf=str(gguf), ggufBytes=Path(gguf).stat().st_size, ggufHeaderSHA256=hashlib.sha256(head).hexdigest(),
                                     tensor=fx["tensor"], offset=off)
        else:
            src, off = kdot_dir / fx["kdot"], fx["offset"]
            source = dict(file=str(src), fileBytes=src.stat().st_size, offset=off)
        with open(src, "rb") as f:
            f.seek(off)
            data = f.read(fx["nbytes"])
        assert len(data) == fx["nbytes"] == fx["rows"] * (COLS // 256) * BLOCK[fx["tt"]], fx["name"]
        (out / (fx["name"] + ".bin")).write_bytes(data)
        rows[fx["name"]] = dict(tt=fx["tt"], rows=fx["rows"], cols=COLS, source=source, data=pin(out / (fx["name"] + ".bin")))
    x = struct.pack(f"<{COLS}f", *lcg(COLS, 2026))
    (out / "x.f32").write_bytes(x)
    report = dict(status="FIXTURES", host=[platform.system(), platform.machine(), platform.node()], fixtures=rows, x=pin(out / "x.f32"),
                  note="kotoba-lang/inference kdot_check.py names attn_qkv, attn_gate, ffn_gate_exp0 and output by their byte counts")
    (output / "fixtures.json").write_text(json.dumps(report, indent=2) + "\n")
    print("FIXTURES", len(rows), flush=True)


# ---- the f64 oracle: ggml's dequant (kotoba-lang/inference kdot_ref.py) times x, summed in f64

KV = [-127, -104, -83, -65, -49, -35, -22, -10, 1, 13, 25, 38, 53, 69, 89, 113]
LO = bytes(b & 15 for b in range(256))
HI = bytes(b >> 4 for b in range(256))
BIT = [bytes((b >> k) & 1 for b in range(256)) for k in range(8)]
TWO = [bytes((b >> k) & 3 for b in range(256)) for k in range(0, 8, 2)]
KVLO = [KV[b & 15] for b in range(256)]
KVHI = [KV[b >> 4] for b in range(256)]


def dot(q, x):
    return sum(map(operator.mul, q, x))


def f16(b, o):
    return struct.unpack_from("<e", b, o)[0]


def scales_mins(sc):
    s, m = [0] * 8, [0] * 8
    for j in range(8):
        if j < 4:
            s[j], m[j] = sc[j] & 63, sc[j + 4] & 63
        else:
            s[j], m[j] = (sc[j + 4] & 15) | ((sc[j - 4] >> 6) << 4), (sc[j + 4] >> 4) | ((sc[j] >> 6) << 4)
    return s, m


def block_dot(tt, b, x):
    """sum over the block's 256 values of dequant(value) x[value], in f64"""
    if tt == 0:
        return dot(struct.unpack("<256f", b), x)
    if tt in (12, 13):
        d, dmin = f16(b, 0), f16(b, 2)
        s, m = scales_mins(b[4:16])
        qs = b[16:144] if tt == 12 else b[48:176]
        qh = b[16:48]
        acc = 0.0
        for g in range(4):
            q = qs[32 * g:32 * g + 32]
            xl, xh = x[64 * g:64 * g + 32], x[64 * g + 32:64 * g + 64]
            lo, hi = dot(q.translate(LO), xl), dot(q.translate(HI), xh)
            if tt == 13:
                lo += 16 * dot(qh.translate(BIT[2 * g]), xl)
                hi += 16 * dot(qh.translate(BIT[2 * g + 1]), xh)
            acc += d * s[2 * g] * lo - dmin * m[2 * g] * sum(xl) + d * s[2 * g + 1] * hi - dmin * m[2 * g + 1] * sum(xh)
        return acc
    if tt == 23:
        d, sh, sl, qs = f16(b, 0), struct.unpack_from("<H", b, 2)[0], b[4:8], b[8:136]
        acc = 0.0
        for ib in range(8):
            ls = ((sl[ib // 2] >> (4 * (ib % 2))) & 15) | (((sh >> (2 * ib)) & 3) << 4)
            q = qs[16 * ib:16 * ib + 16]
            acc += d * (ls - 32) * (dot([KVLO[c] for c in q], x[32 * ib:32 * ib + 16]) + dot([KVHI[c] for c in q], x[32 * ib + 16:32 * ib + 32]))
        return acc
    # Q6_K
    ql, qh, d = b[0:128], b[128:192], f16(b, 208)
    sc = struct.unpack_from("<16b", b, 192)
    acc = 0.0
    for g in range(2):
        qlg, qhg = ql[64 * g:64 * g + 64], qh[32 * g:32 * g + 32]
        for part, (nib, src, k) in enumerate(((LO, 0, 0), (LO, 32, 1), (HI, 0, 2), (HI, 32, 3))):
            lows = qlg[src:src + 32].translate(nib)
            highs = qhg.translate(TWO[k])
            for half in range(2):
                xs = x[128 * g + 32 * part + 16 * half:128 * g + 32 * part + 16 * half + 16]
                lo, hi = lows[16 * half:16 * half + 16], highs[16 * half:16 * half + 16]
                acc += d * sc[8 * g + 2 * part + half] * (dot(lo, xs) + 16 * dot(hi, xs) - 32 * sum(xs))
    return acc


def ref_rows(args):
    path, tt, r0, r1, x = args
    bb, per = BLOCK[tt], COLS // 256
    rb = per * bb
    with open(path, "rb") as f:
        f.seek(r0 * rb)
        data = f.read((r1 - r0) * rb)
    return [sum(block_dot(tt, data[r * rb + k * bb:r * rb + (k + 1) * bb], x[256 * k:256 * k + 256]) for k in range(per)) for r in range(r1 - r0)]


def ref(output, jobs):
    fx = json.loads((output / "fixtures.json").read_text())
    assert pin(output / "fixtures" / "x.f32") == fx["x"], "x changed since the fixtures phase"
    x = list(struct.unpack(f"<{COLS}f", (output / "fixtures" / "x.f32").read_bytes()))
    out = output / "ref"
    out.mkdir(exist_ok=False)
    rows = {}
    with multiprocessing.Pool(jobs) as pool:
        for name, f in fx["fixtures"].items():
            path = output / "fixtures" / (name + ".bin")
            assert pin(path) == f["data"], (name, "the fixture changed since the fixtures phase")
            t0 = time.monotonic()
            step = 2048
            vals = [v for part in pool.map(ref_rows, [(str(path), f["tt"], r, min(r + step, f["rows"]), x) for r in range(0, f["rows"], step)]) for v in part]
            (out / (name + ".f64")).write_bytes(struct.pack(f"<{len(vals)}d", *vals))
            row = dict(rows=len(vals), seconds=round(time.monotonic() - t0, 1), fixture=f["data"], ref=pin(out / (name + ".f64")))
            if name == "output":
                order = sorted(range(len(vals)), key=lambda k: -vals[k])[:8]
                row.update(argmax=order[0], top8=[[k, vals[k]] for k in order], gap=vals[order[0]] - vals[order[1]])
            rows[name] = row
            print("REF", name, row["rows"], row["seconds"], "s", flush=True)
    (output / "ref.json").write_text(json.dumps(dict(status="REF", host=[platform.system(), platform.machine()], fixtures=rows, x=fx["x"],
                                                     note="f64 dequant oracle, test-time only"), indent=2) + "\n")


# ---- the guests

def hexu32(*vs):
    return struct.pack(f"<{len(vs)}I", *vs).hex()


def guest_source(name, f, layouts):
    """(name: the fixture's)"""
    """A static guest: maps the fixture and x, runs each layout's KIR v2 and glslang
    module (one dispatch, then three command buffers of 10), and prints a line per
    layout: L <layout> <same 0/1> K <one> <ten> xROUNDS R <one> <ten> xROUNDS <hex of
    KIR v2's outputs> (one dispatch of each to warm up, then ROUNDS rounds of a
    10-dispatch command buffer, KIR v2 then glslang, so neither takes the clock
    ramp alone); for the lm_head also the argmax chains: A <KIR pick>
    <glslang pick> <KIR max> <glslang max>."""
    rows, nb = f["rows"], f["rows"] * 4
    lines = ['(ns g (:export [main]))',
             '(defn- gpu [r :string] :string (typed-cap-call 42 :string :string r))',
             '(defn- say [s :string] :i64 (let [x (typed-cap-call :io/write :string :string s)] 0))',
             '(defn- cat [a :string b :string] :string (string-concat a b))',
             ';; n recorded dispatches; the number whose answer is not "1"',
             '(defn- times [n :i64 req :string bad :i64] :i64',
             '  (if (< n 1) bad (let [a (gpu req)] (times (- n 1) req (if (string=? a "1") bad (+ bad 1))))))',
             ';; n hex digits of ff (NaN as f32), by doubling',
             '(defn- ffs [n :i64 s :string] :string (if (>= (string-length s) n) (string-substring s 0 n) (ffs n (cat s s))))',
             ';; a command buffer of 10 dispatches: its ns, or X when a recorded dispatch was refused',
             '(defn- batch [req :string] :string (let [a (gpu "BEGIN") b (times 10 req 0) t (gpu "SUBMIT")] (if (= b 0) t "X")))',
             ';; n rounds, KIR v2 then glslang in each: " k1 .. kn R <one-r> r1 .. rn"',
             '(defn- rounds [n :i64 rk :string rr :string one-r :string ak :string ar :string] :string',
             '  (if (< n 1) (cat ak (cat " R " (cat one-r ar)))',
             '    (let [k (batch rk) r (batch rr)] (rounds (- n 1) rk rr one-r (cat ak (cat " " k)) (cat ar (cat " " r))))))',
             '(defn- req [p :string wg :string m :string w :string x :string o :string e :string] :string',
             '  (cat "DISPATCH " (cat p (cat " " (cat wg (cat " 1 1 " (cat m (cat " " (cat w (cat " " (cat x (cat " " (cat o (cat " " e))))))))))))))',
             ';; dot_rows: four bindings (Meta, W, X, O)',
             '(defn- req4 [p :string wg :string m :string w :string x :string o :string e :string] :string',
             '  (cat "DISPATCH " (cat p (cat " " (cat wg (cat " 1 1 " (cat m (cat " " (cat w (cat " " (cat x (cat " " o))))))))))))',
             '(defn main [] :i64',
             f'  (let [w (gpu "MAP {name}.bin 0 {f["data"]["bytes"]}") x (gpu "MAP x.f32 0 {COLS * 4}")',
             '        m (gpu "ALLOC 32") e (gpu "ALLOC 16")',
             f'        o1 (gpu "ALLOC {nb}") o2 (gpu "ALLOC {nb}") nan (ffs {2 * nb} "ff")',
             f'        wm (gpu (cat "WRITE " (cat m " 0 {hexu32(rows, COLS) if f["tt"] == 0 else hexu32(rows, COLS, f["tt"], 1, 0, 0, 0, 0)}")))',
             '        we (gpu (cat "WRITE " (cat e " 0 00000000000000000000000000000000")))']
    for k, lay in enumerate(layouts):
        kir, gl, R = LAYOUTS[lay]
        wg = -(-rows // R)
        nbind, rq = (4, "req4") if lay == "dot" else (5, "req")
        lines += [f'        pk{k} (gpu "PIPELINE {kir} {nbind}") pr{k} (gpu "PIPELINE {gl} {nbind}")',
                  f'        qk{k} ({rq} pk{k} "{wg}" m w x o1 e) qr{k} ({rq} pr{k} "{wg}" m w x o2 e)',
                  f'        fk{k} (gpu (cat "WRITE " (cat o1 (cat " 0 " nan)))) fr{k} (gpu (cat "WRITE " (cat o2 (cat " 0 " nan))))',
                  f'        ok{k} (gpu qk{k}) or{k} (gpu qr{k}) tk{k} (rounds {ROUNDS} qk{k} qr{k} or{k} "" "")',
                  f'        hk{k} (gpu (cat "READ " (cat o1 " 0 {nb}"))) hr{k} (gpu (cat "READ " (cat o2 " 0 {nb}")))',
                  f'        s{k} (say (cat "L {lay} " (cat (if (and (string=? fk{k} "1") (and (string=? fr{k} "1") (string=? hk{k} hr{k}))) "1" "0") (cat " K " (cat ok{k} (cat tk{k} (cat " " (cat hk{k} "\\n"))))))))']
    if name == "output":
        # the decode guest's argmax chain over the first layout's logits:
        # argmax_partial (one workgroup per 4096 logits) then argmax_final; nex
        # Meta, bindings 1..6
        parts = -(-rows // 4096)
        kir, gl, R = LAYOUTS[layouts[0]]
        # (the first layout's logits again: the layouts after it wrote o1 and o2)
        lines += [f'        km (gpu "PIPELINE {kir} 5") kr (gpu "PIPELINE {gl} 5")',
                  f'        lk (gpu (req km "{-(-rows // R)}" m w x o1 e)) lr (gpu (req kr "{-(-rows // R)}" m w x o2 e))',
                  '        nm (gpu "ALLOC 32") nb (gpu "ALLOC 64") nc (gpu "ALLOC 16") no (gpu "ALLOC 256") ns (gpu "ALLOC 256") ni (gpu "ALLOC 256")',
                  f'        nw (gpu (cat "WRITE " (cat nm " 0 {hexu32(rows, 0, parts, 0)}{"00" * 16}")))']
        for side, (pp, pf) in (("k", (ARGMAX[0][0], ARGMAX[1][0])), ("r", (ARGMAX[0][1], ARGMAX[1][1]))):
            o = "o1" if side == "k" else "o2"
            lines += [f'        a{side}p (gpu "PIPELINE {pp} 7") a{side}f (gpu "PIPELINE {pf} 7")',
                      f'        a{side}0 (gpu (cat "WRITE " (cat ns (cat " 0 " (ffs 512 "ff"))))) a{side}1 (gpu (cat "WRITE " (cat ni (cat " 0 " (ffs 512 "ff")))))',
                      f'        a{side}2 (gpu (cat "WRITE " (cat no (cat " 0 " (ffs 512 "ff")))))',
                      f'        a{side}3 (gpu (cat "DISPATCH " (cat a{side}p (cat " {parts} 1 1 " (cat nm (cat " " (cat {o} (cat " " (cat nb (cat " " (cat nc (cat " " (cat no (cat " " (cat ns (cat " " ni))))))))))))))))',
                      f'        a{side}4 (gpu (cat "DISPATCH " (cat a{side}f (cat " 1 1 1 " (cat nm (cat " " (cat {o} (cat " " (cat nb (cat " " (cat nc (cat " " (cat no (cat " " (cat ns (cat " " ni))))))))))))))))',
                      f'        a{side}5 (gpu (cat "READ " (cat ni " {4 * parts} 4"))) a{side}6 (gpu (cat "READ " (cat no " 0 4")))',
                      f'        a{side}7 (gpu (cat "READ " (cat ns " 0 {4 * parts}"))) a{side}8 (gpu (cat "READ " (cat ni " 0 {4 * parts}")))']
        # A <r1 KIR> <r1 glslang> <partial, final KIR> <partial, final glslang> <picks> <maxima> <partials KIR> <partials glslang>
        fields = ["lk", "lr", "ak3", "ak4", "ar3", "ar4", "ak5", "ar5", "ak6", "ar6", "ak7", "ak8", "ar7", "ar8"]
        expr = '"\\n"'
        for fld in reversed(fields):
            expr = f'(cat " " (cat {fld} {expr}))'
        lines += [f'        sa (say (cat "A" {expr}))']
    lines += ['        ]', '    0))']
    return "\n".join(lines) + "\n"


def build(compiler, output, kernels, provider):
    assert platform.system() == "Linux", "run the build phase on Linux"
    fx = json.loads((output / "fixtures.json").read_text())
    assert sorted(fx["fixtures"]) == sorted(f["name"] for f in FIXTURES), sorted(fx["fixtures"])
    root = json.loads((ROOT / "seed/bootstrap/aarch64-linux-static-root.json").read_text())["image"]
    assert pin(compiler) == root, ("not the pinned root", pin(compiler), root)
    art = output / "artifacts"
    art.mkdir(exist_ok=False)
    producer = art / "compiler.elf"
    producer.write_bytes(compiler.read_bytes())
    producer.chmod(0o755)
    guests = {}
    for name, (fixture, layouts) in GUESTS.items():
        f = fx["fixtures"][fixture]
        src, elf = art / f"guest-{name}.kotoba", art / f"guest-{name}.elf"
        src.write_text(guest_source(fixture, f, layouts))
        c = subprocess.run([str(producer), "compile", str(src), "--target", "x86_64-linux", "--output", str(elf), "--format", "static"],
                           cwd=art, env={"PATH": "/usr/bin:/bin", "KEXE_CAP_RESOURCES_35": str(art)}, capture_output=True, timeout=600)
        assert c.returncode == 0 and not c.stderr and b":ok true" in c.stdout, (name, c.returncode, c.stderr[-400:], c.stdout[-400:])
        guests[name] = dict(fixture=fixture, layouts=layouts, workgroups=guest_workgroups(f, layouts), source=pin(src), image=pin(elf))
    # the kernels: the kir2 suite's build (its oracle phase passed) and glslang's
    krep = json.loads((kernels / "gpu-kernel-kir2.json").read_text())
    assert krep["status"].startswith("PASS_GPU_KERNEL_SPIRV_BUILD_AND_ORACLE") or krep["status"] == "PASS_GPU_KERNEL_KIR2_GPU", krep["status"]
    mods = {}
    for kir, gl, _ in LAYOUTS.values():
        mods[kir], mods[gl] = krep["modules"][kir], krep["glslangReferences"]["modules"][gl]["module"]
    for kir, gl in ARGMAX:
        mods[kir], mods[gl] = krep["modules"][kir], krep["glslangReferences"]["modules"][gl]["module"]
    kdir = art / "kernels"
    kdir.mkdir()
    for n, p in mods.items():
        src = kernels / ("spv" if n.startswith("kir2-") else "refs") / n
        assert pin(src) == p, (n, "changed since the kernels' build")
        shutil.copy(src, kdir / n)
    prep = json.loads((provider / "gpu-provider.json").read_text())
    report = dict(status="BUILT", compiler=pin(compiler), host=[platform.system(), platform.machine()], guests=guests, kernels=mods,
                  provider=dict(images={k: pin(provider / v) for k, v in prep["images"].items()}),
                  sources={p: pin(ROOT / p) for p in ["scripts/seed/check-gpu-kernel-exec.py"]})
    (output / "exec-build.json").write_text(json.dumps(report, indent=2) + "\n")
    print("BUILT", len(guests), "guests", len(mods), "kernels", flush=True)


# ---- the run

def parse_report(stdout):
    """the launcher's receipt line, and the provider report inside it"""
    line = stdout[stdout.rindex(b"{:receipt "):].decode()
    m = re.search(r':report "((?:[^"\\]|\\.)*)"', line)
    rep = m.group(1).encode().decode("unicode_escape") if m else ""
    return line, rep


def run(output, provider, speed_gate=True, max_workgroups=VULKAN_MIN_WORKGROUPS):
    assert platform.system() == "Linux" and platform.machine() in ("x86_64", "AMD64"), "run phase: x86_64 Linux with a Vulkan driver"
    spec = __import__("importlib.util").util.spec_from_file_location("cgp", ROOT / "scripts/seed/check-gpu-provider.py")
    cgp = __import__("importlib.util").util.module_from_spec(spec)
    spec.loader.exec_module(cgp)
    fx = json.loads((output / "fixtures.json").read_text())
    rf = json.loads((output / "ref.json").read_text())
    br = json.loads((output / "exec-build.json").read_text())
    assert sorted(fx["fixtures"]) == sorted(f["name"] for f in FIXTURES) == sorted(rf["fixtures"]) and sorted(br["guests"]) == sorted(GUESTS)
    assert rf["x"] == fx["x"] and all(rf["fixtures"][n]["fixture"] == f["data"] for n, f in fx["fixtures"].items()), \
        "the references are not of these fixtures"
    prep = json.loads((provider / "gpu-provider.json").read_text())
    launcher, vulkan = provider / prep["images"]["launcher"], provider / prep["images"]["provider-vulkan"]
    assert pin(launcher) == br["provider"]["images"]["launcher"] and pin(vulkan) == br["provider"]["images"]["provider-vulkan"]
    box = output / "box"
    box.mkdir(exist_ok=False)
    for n in br["kernels"]:
        shutil.copy(output / "artifacts" / "kernels" / n, box / n)
    rows, skipped = {}, {}
    for name, (fixture, layouts) in GUESTS.items():
        f = fx["fixtures"][fixture]
        if br["guests"][name]["workgroups"] > max_workgroups:
            skipped[name] = f"{br['guests'][name]['workgroups']} workgroups exceed --max-workgroups {max_workgroups}"
            continue
        guest = output / "artifacts" / f"guest-{name}.elf"
        assert pin(guest) == br["guests"][name]["image"]
        for n in (fixture + ".bin", "x.f32"):
            dst = box / n
            if not dst.exists():
                shutil.copy(output / "fixtures" / n, dst)
        assert pin(box / (fixture + ".bin")) == f["data"]
        arts = [(fixture + ".bin", f["data"]["sha256"], "model"), ("x.f32", fx["x"]["sha256"], "model")]
        arts += [(n, p["sha256"], "spirv") for n, p in br["kernels"].items()]
        g = box / f"{name}.grant.edn"
        g.write_bytes(cgp.grant(arts, cap=1 << 31))
        t0 = time.monotonic()
        z = subprocess.run([str(launcher), str(WALL), "37,38,39,42", str(g), str(vulkan), "--", str(guest)],
                           env={"PATH": "/usr/bin:/bin"}, cwd=box, capture_output=True, timeout=WALL + 60)
        seconds = round(time.monotonic() - t0, 1)
        (box / f"{name}.stdout").write_bytes(z.stdout)
        (box / f"{name}.stderr").write_bytes(z.stderr)
        line, rep = parse_report(z.stdout)
        assert z.returncode == 0 and ":verdict :ok" in line, (name, z.returncode, line[:600], z.stderr[-400:])
        refv = struct.unpack(f"<{f['rows']}d", (output / "ref" / (fixture + ".f64")).read_bytes())
        assert pin(output / "ref" / (fixture + ".f64")) == rf["fixtures"][fixture]["ref"]
        layout_rows, chain_got = {}, None
        for ln in z.stdout.decode().splitlines():
            if ln.startswith("L "):
                p = ln.split()
                lay, same = p[1], p[2] == "1"
                ri = 5 + ROUNDS
                assert p[3] == "K" and p[ri] == "R" and len(p) == ri + ROUNDS + 3, (name, lay, p[:ri + ROUNDS + 2])
                kt, rt = [int(v) for v in p[4:ri]], [int(v) for v in p[ri + 1:ri + ROUNDS + 2]]
                got = struct.unpack(f"<{f['rows']}f", bytes.fromhex(p[ri + ROUNDS + 2]))
                if lay == layouts[0]:
                    chain_got = got
                assert same, (name, lay, "KIR v2's outputs differ from glslang's module")
                assert all(math.isfinite(v) for v in got), (name, lay, "non-finite outputs")
                rel = max(abs(a - b) / max(abs(b), 1e-2) for a, b in zip(got, refv))
                rms = (sum(b * b for b in refv) / len(refv)) ** 0.5
                over_rms = max(abs(a - b) for a, b in zip(got, refv)) / rms
                assert rel <= REL_MAX[lay] if lay in REL_MAX else over_rms <= RMS_MAX[lay], (name, lay, "error vs f64", rel, over_rms)
                kmed, rmed = sorted(kt[1:])[ROUNDS // 2], sorted(rt[1:])[ROUNDS // 2]
                ratio, gated = kmed / rmed, rmed >= SPEED_MIN_NS
                assert ratio <= SPEED_MAX or not gated or not speed_gate, (name, lay, "KIR v2 slower than glslang's module", ratio, kt, rt)
                gbs = 10 * f["data"]["bytes"] / kmed
                layout_rows[lay] = dict(identicalToGlslang=True, maxRelErrVsF64=rel, maxErrOverRms=over_rms, kirNs=kt, glslangNs=rt,
                                        speedRatio=round(ratio, 3), speedGated=gated,
                                        kirGBs=round(gbs, 1), outputSHA256=hashlib.sha256(bytes.fromhex(p[ri + ROUNDS + 2])).hexdigest())
        assert sorted(layout_rows) == sorted(br["guests"][name]["layouts"]), (name, "missing layouts", sorted(layout_rows))
        assert rep, (name, "no provider report in the receipt")
        row = dict(fixture=fixture, rows=f["rows"], tt=f["tt"], seconds=seconds, layouts=layout_rows, receipt=line.strip(),
                   confinement=cgp.confined(rep, True))
        if fixture == "output":
            a = [ln for ln in z.stdout.decode().splitlines() if ln.startswith("A ")]
            assert len(a) == 1, "the argmax line"
            q = a[0].split()[1:]
            assert len(q) == 14 and all(v.isdigit() for v in q[:6]), ("a chain dispatch was refused", q[:6])
            kp, rp, km, rm, ks, ki, rs, ri = q[6:]
            kpick, rpick = struct.unpack("<I", bytes.fromhex(kp))[0], struct.unpack("<I", bytes.fromhex(rp))[0]
            assert kpick == rpick and km == rm and ks == rs and ki == ri, ("the argmax chains differ", kpick, rpick)
            # the chain against the logits it ran on (the first layout's): each partial is its segment's
            # max at the lowest index, the pick the lowest index of the overall max
            parts = -(-f["rows"] // 4096)
            sv, si = struct.unpack(f"<{parts}f", bytes.fromhex(ks)), struct.unpack(f"<{parts}I", bytes.fromhex(ki))
            for w in range(parts):
                seg = range(w * 4096, min(w * 4096 + 4096, f["rows"]))
                j = min(seg, key=lambda k: (-chain_got[k], k))
                assert si[w] == j and sv[w] == chain_got[j], ("partial", w, si[w], j)
            top = min(range(f["rows"]), key=lambda k: (-chain_got[k], k))
            assert kpick == top and struct.unpack("<f", bytes.fromhex(km))[0] == chain_got[top], ("the pick vs the logits", kpick, top)
            want = rf["fixtures"]["output"]["argmax"]
            assert kpick == want, ("the argmax chain's pick vs the f64 argmax", kpick, want, rf["fixtures"]["output"]["top8"][:3])
            row["argmax"] = dict(pick=kpick, f64Argmax=want, f64Gap=rf["fixtures"]["output"]["gap"], identicalToGlslang=True,
                                 partials=parts, logitsOf=layouts[0], partialsMatchLogits=True, maxLogit=struct.unpack("<f", bytes.fromhex(km))[0])
        rows[name] = row
        print("RAN", name, seconds, "s", sorted(layout_rows), flush=True)
    slow = [(n, lay, l["speedRatio"]) for n, r in rows.items() for lay, l in r["layouts"].items() if l["speedRatio"] > SPEED_MAX and l["speedGated"]]
    report = dict(status="PASS_GPU_KERNEL_EXEC" if speed_gate else "PASS_GPU_KERNEL_EXEC_SPEED_RECORDED", slowerThanGate=slow,
                  maxWorkgroups=max_workgroups, skipped=skipped, host=[platform.system(), platform.machine(), platform.release()], node=platform.node(),
                  fixtures=rows, gates=dict(relMax=REL_MAX, rmsMax=RMS_MAX, speedMax=SPEED_MAX, speedMinNs=SPEED_MIN_NS, rounds=ROUNDS), wallSeconds=WALL,
                  note="glslang's modules and the f64 reference are oracles; the guests, the launcher and the provider are the product route")
    (output / "gpu-kernel-exec.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], len(rows), "guests", "skipped:", sorted(skipped), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("phase", choices=["fixtures", "ref", "build", "run"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--kdot-dir", type=Path, help="fixtures: the directory of the kdot fixture files")
    parser.add_argument("--gguf", type=Path, help="fixtures: Qwen3.6-35B-A3B-Q4_K_M.gguf")
    parser.add_argument("--jobs", type=int, default=multiprocessing.cpu_count(), help="ref: worker processes")
    parser.add_argument("--compiler", type=Path, help="build: the pinned root")
    parser.add_argument("--kernels", type=Path, help="build: a check-gpu-kernel-spirv.py --suite kir2 output (oracle phase done)")
    parser.add_argument("--provider", type=Path, help="build, run: a check-gpu-provider.py build output (launcher, provider-vulkan)")
    parser.add_argument("--max-workgroups", type=int, default=VULKAN_MIN_WORKGROUPS,
                        help="run: the device's maxComputeWorkGroupCount (default Vulkan's guaranteed 65535; RADV and NVIDIA allow more)")
    parser.add_argument("--speed-recorded", action="store_true",
                        help="run: record the speed ratios without gating on them (diagnosis; the receipt's status says so)")
    args = parser.parse_args()
    out = args.output.resolve()
    if args.phase == "fixtures":
        fixtures(out, args.kdot_dir.resolve(), args.gguf.resolve())
    elif args.phase == "ref":
        ref(out, args.jobs)
    elif args.phase == "build":
        build(args.compiler.resolve(), out, args.kernels.resolve(), args.provider.resolve())
    else:
        run(out, args.provider.resolve(), not args.speed_recorded, args.max_workgroups)
