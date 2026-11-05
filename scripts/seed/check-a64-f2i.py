#!/usr/bin/env python3
"""f32 -> i64 (JUN-633, ADR 0398) and f64 -> i64 (JUN-846) truncation on the aarch64 route (seed/41).

seed/41's gn-fl-un emits `f32-to-i64-truncating` (SIR UOP 37) with ADR 0395's semantics, as the x86 object route
does: truncation toward zero; a NaN, +-Inf or any operand outside [-2^63, 2^63) reaches brk #0 instead of fcvtzs's
saturated answer. Compiles with a native Amu compiler for --target aarch64-macos, packages with the pinned Mac
packager and runs natively (Python stages and observes; it emits nothing):

* guard: the payload exporting the conversion carries, exactly once,
    fmov s0,wX ; movz xD,#0xdf00,lsl #16 ; fmov s1,wD ; fcmp s0,s1 ; b.lt +4 ; fneg s1,s1 ; fcmp s1,s0 ; b.gt +2 ;
    brk #0 ; fcvtzs xD,s0
  with one D, and no single-precision fcvtzs anywhere else; a function with two conversions carries two guards;
* f64 -> i64 (UOP 32, JUN-846) is the same guard at double precision, once per use (the reference traps NaN, +-Inf and
  every |x| >= 2^63; fcvtzs would saturate):
    fmov d0,xX ; movz xD,#0xc3e0,lsl #48 ; fmov d1,xD ; fcmp d0,d1 ; b.lt +4 ; fneg d1,d1 ; fcmp d1,d0 ; b.gt +2 ;
    brk #0 ; fcvtzs xD,d0
* opt-in: payloads that do not name the conversion keep the SHA-256 they have under the main 26833b16 root;
* execution, packaged and signed on this Mac: in-range operands return the truncated integer (including -2^63 ->
  INT64_MIN, 2^63 - 2^39, +-0, denormals, +-0.99999994, +-2.5); NaNs (quiet, signalling, negative), +-Inf, 2^63,
  the f32 neighbour below -2^63 and the finite extremes each die by SIGTRAP with no output.

Against the main root (saturating fcvtzs) the gate is red: no guard, and the trap programs exit with an answer.
docs/evidence/f32-to-i64-a64-20261031/ runs every 2^32 pattern natively on macOS and Linux arm64 against the x86
run's integer C reference.
"""

import argparse
import hashlib
import importlib.util
import json
import re
import struct
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
MAC_GATE = Path(__file__).with_name("check-aiueos-user-macos-native.py")
PACKAGER = ROOT / "seed/bootstrap/aarch64-macos/kotoba-packager-root.macho"
FLOAT_CASES = ROOT / "seed/float-cases.json"
SOURCE = """(ns f2i (:export [kotoba_aiueos_f32_to_i64]))
(defn kotoba_aiueos_f32_to_i64 [bits :i64] :i64 (f32-to-i64-truncating (f32-from-bits bits)))
"""
TWICE = """(ns f2i2 (:export [f]))
(defn f [a :i64 b :i64] :i64 (+ (f32-to-i64-truncating (f32-from-bits a)) (f32-to-i64-truncating (f32-from-bits b))))
"""
F64 = """(ns d2i (:export [f]))
(defn f [bits :i64] :i64 (f64-to-i64-truncating (f64-from-bits bits)))
"""
SIGTRAP = -5
INT64_MIN = -(1 << 63)
# float-cases.json entries that do not use f32-to-i64-truncating: their aarch64-macos payloads (extract-native main)
# use the main 26833b16 pins except the three decimal-literal cases, whose source now lowers
# literals directly to f64 bits. Their native results are checked separately in this integration.
# JUN-846: the cases that name f64-to-i64-truncating (basic, literal, div-trunc, neg-abs-sqrt, min-max, f32-conv) now carry
# the double guard and moved; float-f64-cmp, float-f64-unordered and float-f32-cmp name no conversion and are unchanged.
UNCHANGED = {
    "float-f64-basic": "a2c90acedf196f84213e55d3209be6cdcb62bb65a31a3b0c595e1c024d52eff5",
    "float-f64-literal": "efba8429890323d8aec4a405b6bc8f65f0c0ca773135c6341904e9021bb1a0ee",
    "float-f64-div-trunc": "abb54f6f44af7f68ed3d21f7727b12e9fc1555606ca63ba9c2d5736efa7038fc",
    "float-f64-neg-abs-sqrt": "3230bc36caee3e893faadb51b5f2274de38df1b279dcd428f982f428c806ddde",
    "float-f64-cmp": "9f1bc1bec464d34e3e307f7d425f91138fd539a099c07fe98072a6dd6eb6816c",
    "float-f64-min-max": "73a3bef116536c368de53a4675668befa5907e1a4f7bfb11a3563d1bf71847cf",
    "float-f32-conv": "0509db2448d7b2b695558b85d85ec521de1615c12fb3d70ebb362b774e5fac82",
    "float-f64-unordered": "96d77de223bed4e18a5768a5abdb55cc7e2df6c02944ebb082ad2b99b187cc54",
    "float-f32-cmp": "2629d0afcd6fb9520f037a8c40678e735bf00a6eb44912e86163d20422eb3264",
}
D64 = "7d9f1baa1962dd3c4c3f03d0c090bd4707ed9605d6684991875b26d8327c1619"   # the F64 payload under the same root
IN_RANGE = [0x00000000, 0x80000000, 0x00000001, 0x807fffff, 0x3f7fffff, 0xbf7fffff, 0x3f800000, 0xbfc00000,
            0x40200000, 0xc0200000, 0x4b000001, 0xcaffffff, 0x4f000000, 0xcf800001, 0x5e800000, 0x5effffff,
            0xdeffffff, 0xdf000000]
TRAPS = [0x7f800000, 0xff800000, 0x7fc00000, 0xffc00000, 0x7f800001, 0xffa5a5a5, 0x7fffffff, 0x5f000000,
         0x5f000001, 0xdf000001, 0xdf800000, 0x7f7fffff, 0xff7fffff]
# f64 patterns: zeros, denormals, +-0.99999999999999989, +-1, +-2.5, 2^53+1 region, 2^63 - 1024 (the largest double below
# 2^63), -2^63 (exact), the first double above -2^63
IN_RANGE64 = [0x0000000000000000, 0x8000000000000000, 0x0000000000000001, 0x800fffffffffffff, 0x3fefffffffffffff,
              0xbfefffffffffffff, 0x3ff0000000000000, 0xbff0000000000000, 0x4004000000000000, 0xc004000000000000,
              0x4340000000000001, 0xc340000000000001, 0x43dfffffffffffff, 0xc3e0000000000000, 0xc3dfffffffffffff]
# NaNs (quiet, signalling, negative, payload), +-Inf, 2^63, the double below -2^63, the finite extremes
TRAPS64 = [0x7ff0000000000000, 0xfff0000000000000, 0x7ff8000000000000, 0xfff8000000000000, 0x7ff0000000000001,
           0xfff4a5a5a5a5a5a5, 0x7fffffffffffffff, 0x43e0000000000000, 0xc3e0000000000001, 0x7fefffffffffffff,
           0xffefffffffffffff, 0x43f0000000000000]


def ref(bits):
    """ADR 0395 from the bit pattern alone (docs/evidence/f32-to-i64-20261031/ref.c): an integer, or None (trap)."""
    s, e, m = bits >> 31, (bits >> 23) & 0xFF, bits & 0x7FFFFF
    if e == 0xFF:
        return None
    if e < 127:
        return 0
    sh = e - 127
    if sh >= 63:
        return INT64_MIN if (s and sh == 63 and m == 0) else None
    sig = m | 0x800000
    mag = sig << (sh - 23) if sh >= 23 else sig >> (23 - sh)
    return -mag if s else mag


def signed32(bits):
    return bits - (1 << 32) if bits & 0x80000000 else bits


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def words(raw):
    return list(struct.unpack(f"<{len(raw) // 4}I", raw[: len(raw) // 4 * 4]))


def guards(ws):
    """Start indices of the guarded sequence; checks that its register fields agree."""
    found = []
    for i in range(len(ws) - 9):
        w = ws[i:i + 10]
        d = w[1] & 31
        if (w[0] & 0xFFFFFC1F == 0x1E270000 and w[1] == 0xD2BBE000 | d and w[2] == 0x1E270001 | d << 5
                and w[3:9] == [0x1E202000 | 1 << 16, 0x5400008B, 0x1E214021, 0x1E202020, 0x5400004C, 0xD4200000]
                and w[9] == 0x9E380000 | d):
            found.append(i)
    return found


def guards64(ws):
    """Start indices of the double-precision guarded sequence (fmov d0,xX ; movz xD,#0xc3e0,lsl #48 ; ... ; fcvtzs xD,d0)."""
    found = []
    for i in range(len(ws) - 9):
        w = ws[i:i + 10]
        d = w[1] & 31
        if (w[0] & 0xFFFFFC1F == 0x9E670000 and w[1] == 0xD2F87C00 | d and w[2] == 0x9E670001 | d << 5
                and w[3:9] == [0x1E602000 | 1 << 16, 0x5400008B, 0x1E614021, 0x1E602020, 0x5400004C, 0xD4200000]
                and w[9] == 0x9E780000 | d):
            found.append(i)
    return found


def ref64(bits):
    """The reference f64 -> i64 truncation from the bit pattern alone: an integer, or None (trap)."""
    s, e, m = bits >> 63, (bits >> 52) & 0x7FF, bits & 0xFFFFFFFFFFFFF
    if e == 0x7FF:
        return None
    if e < 1023:
        return 0
    sh = e - 1023
    if sh >= 63:
        return INT64_MIN if (s and sh == 63 and m == 0) else None
    sig = m | (1 << 52)
    mag = sig << (sh - 52) if sh >= 52 else sig >> (52 - sh)
    return -mag if s else mag


def signed64(bits):
    return bits - (1 << 64) if bits >> 63 else bits


def fcvtzs(ws, single):
    base = 0x9E380000 if single else 0x9E780000
    return [i for i, w in enumerate(ws) if w & 0xFFFFFC00 == base]


def compile_raw(gate, compiler, out, name, source, symbol):
    (out / f"{name}.kotoba").write_text(source)
    gate.native_run(compiler, out, "compile", f"{name}.kotoba", "--target", "aarch64-macos", "--output", f"{name}.kseed")
    extracted = gate.native_run(compiler, out, "extract-native", f"{name}.kseed", "--symbol", symbol,
                                "--output", f"{name}.raw")
    match = re.search(rb":offset (\d+), :length (\d+), :arity \d+}", extracted.stdout)
    raw = (out / f"{name}.raw").read_bytes()
    if match is None or int(match.group(2)) != len(raw):
        raise ValueError("native extraction did not match raw bytes: " + name)
    return raw, int(match.group(1))


def program(gate, compiler, out, name, source):
    raw, entry = compile_raw(gate, compiler, out, name, source, "main")
    gate.native_run(PACKAGER, out, f"{name}-unsigned.macho", f"{name}.raw", "fs2-cli-stdio-general", str(entry))
    gate.sign(out / f"{name}-unsigned.macho", out / f"{name}.macho")
    return gate.process([out / f"{name}.macho"], cwd=out, timeout=120)


def main(compiler, output, measure):
    gate = load(MAC_GATE, "mac_native_gate")
    gate.verify_macho(compiler)
    gate.verify_macho(PACKAGER)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    report = {}

    cases = {c["name"]: c["source"] for c in json.loads(FLOAT_CASES.read_text())["cases"]}
    digests = {}
    for name in UNCHANGED:
        raw, _ = compile_raw(gate, compiler, output, name, cases[name], "main")
        digests[name] = hashlib.sha256(raw).hexdigest()
    raw, _ = compile_raw(gate, compiler, output, "d2i", F64, "f")
    digests["d2i"] = hashlib.sha256(raw).hexdigest()
    if measure:
        print(json.dumps(digests, indent=2))
        return
    ws = words(raw)
    at64 = guards64(ws)
    if guards(ws) or len(at64) != 1 or sorted(fcvtzs(ws, False)) != [i + 9 for i in at64] or fcvtzs(ws, True):
        raise ValueError(f"f64 -> i64 is not exactly one guarded double fcvtzs: guards {at64}")
    want = dict(UNCHANGED, d2i=D64)
    if digests != want:
        raise ValueError(f"payloads without the conversion changed: {digests}")
    report["unchanged"] = digests
    report["f64Guard"] = [4 * i for i in at64]

    # These literals intentionally lower to different bytes in the decimal
    # frontend. Execute each result as well as pinning its emitted payload.
    literal_results = {}
    for name in ("float-f64-literal", "float-f32-conv", "float-f64-unordered"):
        expected = next(c["result"] for c in json.loads(FLOAT_CASES.read_text())["cases"] if c["name"] == name)
        result = program(gate, compiler, output, "execute-" + name, cases[name])
        if result.returncode != expected or result.stdout or result.stderr:
            raise ValueError(f"{name}: exit {result.returncode}, expected {expected}; {result.stderr!r}")
        literal_results[name] = result.returncode
    report["decimalLiteralResults"] = literal_results

    for name, source, symbol, n in (("f2i", SOURCE, "kotoba_aiueos_f32_to_i64", 1), ("f2i2", TWICE, "f", 2)):
        raw, _ = compile_raw(gate, compiler, output, name, source, symbol)
        ws = words(raw)
        at = guards(ws)
        if len(at) != n or sorted(fcvtzs(ws, True)) != [i + 9 for i in at] or fcvtzs(ws, False):
            raise ValueError(f"{name}: guard at {at}, f32 fcvtzs at {fcvtzs(ws, True)}, expected {n} guards")
        report[name] = {"guards": [4 * i for i in at], "sha256": hashlib.sha256(raw).hexdigest()}

    checks = "".join(f"\n        (not= (f32-to-i64-truncating (f32-from-bits {signed32(b)})) {ref(b)}) {k + 1}"
                     for k, b in enumerate(IN_RANGE))
    result = program(gate, compiler, output, "inrange",
                     f"(ns inrange (:export [main]))\n(defn main [] :i64\n  (cond{checks}\n        :else 0))\n")
    if result.returncode != 0 or result.stdout or result.stderr:
        raise ValueError(f"in-range answers wrong: exit {result.returncode} (case number), {result.stderr!r}")
    report["inRange"] = len(IN_RANGE)

    for b in TRAPS:
        assert ref(b) is None
        name = f"trap-{b:08x}"
        result = program(gate, compiler, output, name, f"(ns t (:export [main]))\n(defn main [] :i64 "
                         f"(bit-and (f32-to-i64-truncating (f32-from-bits {signed32(b)})) 255))\n")
        if result.returncode != SIGTRAP or result.stdout or result.stderr:
            raise ValueError(f"{name}: exit {result.returncode}, expected SIGTRAP; {result.stderr!r}")
    report["traps"] = [f"{b:08x}" for b in TRAPS]

    checks64 = "".join(f"\n        (not= (f64-to-i64-truncating (f64-from-bits {signed64(b)})) {ref64(b)}) {k + 1}"
                       for k, b in enumerate(IN_RANGE64))
    result = program(gate, compiler, output, "inrange64",
                     f"(ns inrange64 (:export [main]))\n(defn main [] :i64\n  (cond{checks64}\n        :else 0))\n")
    if result.returncode != 0 or result.stdout or result.stderr:
        raise ValueError(f"f64 in-range answers wrong: exit {result.returncode} (case number), {result.stderr!r}")
    report["inRange64"] = len(IN_RANGE64)

    for b in TRAPS64:
        assert ref64(b) is None
        name = f"trap64-{b:016x}"
        result = program(gate, compiler, output, name, f"(ns t (:export [main]))\n(defn main [] :i64 "
                         f"(bit-and (f64-to-i64-truncating (f64-from-bits {signed64(b)})) 255))\n")
        if result.returncode != SIGTRAP or result.stdout or result.stderr:
            raise ValueError(f"{name}: exit {result.returncode}, expected SIGTRAP; {result.stderr!r}")
    report["traps64"] = [f"{b:016x}" for b in TRAPS64]
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS_A64_F2I " + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--measure-unchanged", action="store_true",
                        help="print the opt-in payload digests under this compiler and stop (used to set the pins)")
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve(), args.measure_unchanged)
