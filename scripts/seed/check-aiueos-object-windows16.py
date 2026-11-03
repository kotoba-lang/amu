#!/usr/bin/env python3
"""The aiueos kernel object route's 16 KiB tier for u8 / u16 / u64 window accesses (JUN-556 C).

kernel-<load|store>-<u8|u16|u64>-16k are the accesses of check-aiueos-object-windows.py with the length bound 16384
instead of 512 (the tier kernel-load-u32-16k already has). Compiles with a native Amu compiler and decodes every
inlined window with a decoder written here (Python stages and observes; it emits nothing):

  cmp rcx,BOUND; ja TRAP; test rdx,rdx; jz TRAP; cmp INDEX,rcx; jae TRAP;
  [width > 1: mov rsi,rcx; sub rsi,INDEX; cmp rsi,WIDTH; jl TRAP; test INDEX,WIDTH-1; ja TRAP;]
  ACCESS; jmp +2; TRAP: ud2

with every branch landing on that ud2.

* six-16k: one object with the six 16 KiB accesses, in order, each with BOUND 16384;
* mixed: the 512-byte and the 16 KiB u8 load in one object keep their own bounds (the ids stay positional);
* unchanged: the object of check-aiueos-object-windows.py's source is byte-identical to the one the 512-byte tier has
  always produced (its SHA-256 is pinned below), so no object that does not name a 16 KiB stub changes;
* refused (E7106, nothing written): a base that is not rooted, and a length that is not the region's own.

Not shown here: execution. docs/evidence/windows16-20261030/ ran the six-16k object under QEMU by hand.
"""

import argparse
import hashlib
import importlib.util
import json
import struct
from pathlib import Path

MAC_GATE = Path(__file__).with_name("check-aiueos-user-macos-native.py")
FUEL = "1024"
WIDTHS_SHA256 = "a8ac4f073c599331986dbf50e9fd59dccbca14dc6bc89ef053918e47f1991738"
WIDTHS_SOURCE = """(ns widths (:export [ld8 st8 ld16 st16 ld64 st64]))
(defn ld8 [b :i64 n :i64 i :i64] :i64 (kernel-load-u8 b n i))
(defn st8 [b :i64 n :i64 i :i64 v :i64] :i64 (kernel-store-u8 b n i v))
(defn ld16 [b :i64 n :i64 i :i64] :i64 (kernel-load-u16 b n i))
(defn st16 [b :i64 n :i64 i :i64 v :i64] :i64 (kernel-store-u16 b n i v))
(defn ld64 [b :i64 n :i64 i :i64] :i64 (kernel-load-u64 b n i))
(defn st64 [b :i64 n :i64 i :i64 v :i64] :i64 (kernel-store-u64 b n i v))
"""
SOURCE16 = WIDTHS_SOURCE.replace("(ns widths", "(ns widths16").replace(" b n i)", "-16k b n i)").replace(" b n i v)", "-16k b n i v)")
MIXED = """(ns mixed (:export [f g]))
(defn f [b :i64 n :i64 i :i64] :i64 (kernel-load-u8 b n i))
(defn g [b :i64 n :i64 i :i64] :i64 (kernel-load-u8-16k b n i))
"""
EXPECTED = [("load", 1), ("store", 1), ("load", 2), ("store", 2), ("load", 8), ("store", 8)]
ACCESS = {("load", 1): "0fb60402", ("load", 2): "0fb70402", ("load", 8): "488b0402",
          ("store", 1): "88043a", ("store", 2): "6689043a", ("store", 8): "4889043a"}
REFUSALS = {
    "unrooted-base": "(ns refused (:export [f]))\n(defn f [b :i64 n :i64 i :i64] :i64 (kernel-load-u8-16k (+ b 1) n i))\n",
    "free-length": "(ns refused (:export [f]))\n(defn f [b :i64 n :i64 i :i64 v :i64] :i64 (kernel-store-u64-16k b 16 i v))\n",
}


def gate_module():
    spec = importlib.util.spec_from_file_location("mac_native_gate", MAC_GATE)
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    return gate


def text_section(path):
    blob = path.read_bytes()
    shoff, = struct.unpack_from("<Q", blob, 40)
    shnum, shstrndx = struct.unpack_from("<HH", blob, 60)
    secs = [struct.unpack_from("<IIQQQQIIQQ", blob, shoff + 64 * i) for i in range(shnum)]
    shstr = blob[secs[shstrndx][4]:secs[shstrndx][4] + secs[shstrndx][5]]
    for s in secs:
        if shstr[s[0]:shstr.index(b"\0", s[0])] == b".text":
            return blob[s[4]:s[4] + s[5]]
    raise ValueError("no .text")


def head(bound):
    return bytes.fromhex("4881f9") + struct.pack("<I", bound)


def decode_window(text, at, bound):
    """Decode one window access starting at its `cmp rcx,BOUND`; return (kind, width)."""
    pos = at
    jumps = []

    def take(want):
        nonlocal pos
        want = bytes.fromhex(want) if isinstance(want, str) else want
        if text[pos:pos + len(want)] != want:
            raise ValueError(f"at {pos:#x}: want {want.hex()}, have {text[pos:pos + len(want)].hex()}")
        pos += len(want)

    def jcc(opcode):
        nonlocal pos
        take(opcode)
        rel, = struct.unpack_from("<i", text, pos)
        pos += 4
        jumps.append(pos + rel)

    take(head(bound))
    jcc("0f87")
    take("4885d2")
    jcc("0f84")
    store = text[pos:pos + 3] == bytes.fromhex("4839cf")
    take("4839cf" if store else "4839c8")
    jcc("0f83")
    width = 1
    if text[pos:pos + 3] == bytes.fromhex("4889ce"):
        take("4889ce")
        take("4829fe" if store else "4829c6")
        take("4881fe")
        width, = struct.unpack_from("<i", text, pos)
        pos += 4
        jcc("0f8c")
        take("48f7c7" if store else "48f7c0")
        mask, = struct.unpack_from("<i", text, pos)
        pos += 4
        if mask != width - 1 or width not in (2, 8):
            raise ValueError(f"width {width} mask {mask}")
        jcc("0f87")
    kind = "store" if store else "load"
    take(ACCESS[(kind, width)])
    take("eb02")
    trap = pos
    take("0f0b")
    if any(target != trap for target in jumps):
        raise ValueError(f"a branch misses the ud2 at {trap:#x}: {[hex(j) for j in jumps]}")
    return kind, width


def windows(text, bound):
    found, i = [], text.find(head(bound))
    while i >= 0:
        found.append((i, decode_window(text, i, bound)))
        i = text.find(head(bound), i + 1)
    return found


def compile_source(gate, compiler, output, name, source, expected=0):
    (output / f"{name}.kotoba").write_text(source)
    result = gate.native_run(compiler, output, "compile", f"{name}.kotoba", "--target", "x86_64-aiueos-kernel-v1",
                             "--output", f"{name}.o", "--fuel", FUEL, expected=expected)
    return result, output / f"{name}.o"


def main(compiler, output):
    gate = gate_module()
    gate.verify_macho(compiler)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    report = {}

    _, obj = compile_source(gate, compiler, output, "widths16", SOURCE16)
    text = text_section(obj)
    found = [w for _, w in windows(text, 16384)]
    if found != EXPECTED or windows(text, 512):
        raise ValueError(f"16 KiB windows {found}, 512-byte windows {windows(text, 512)}; want {EXPECTED} and none")
    report["six16k"] = {"windows": len(found), "sha256": hashlib.sha256(obj.read_bytes()).hexdigest()}

    _, obj = compile_source(gate, compiler, output, "mixed", MIXED)
    text = text_section(obj)
    small, large = windows(text, 512), windows(text, 16384)
    if [w for _, w in small] != [("load", 1)] or [w for _, w in large] != [("load", 1)] or small[0][0] > large[0][0]:
        raise ValueError(f"mixed: 512-byte {small}, 16 KiB {large}")
    report["mixed"] = "f keeps 512, g has 16384"

    _, obj = compile_source(gate, compiler, output, "widths", WIDTHS_SOURCE)
    digest = hashlib.sha256(obj.read_bytes()).hexdigest()
    if digest != WIDTHS_SHA256:
        raise ValueError(f"the 512-byte width object changed: {digest}")
    report["widthsUnchanged"] = digest

    for name, source in REFUSALS.items():
        result, obj = compile_source(gate, compiler, output, name, source, expected=1)
        message = (result.stdout + result.stderr).decode(errors="replace")
        if "E7106" not in message or obj.exists():
            raise ValueError(f"{name} was not refused with E7106 and no output: {message}")
        report[name] = "refused E7106"
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS_AIUEOS_OBJECT_WINDOWS16 " + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
