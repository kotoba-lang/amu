#!/usr/bin/env python3
"""The aiueos kernel object route's u8 / u16 / u64 window accesses (JUN-556 B).

Compiles one object whose six exports use kernel-load-u8, kernel-store-u8,
kernel-load-u16, kernel-store-u16, kernel-load-u64 and kernel-store-u64, and
reads each inlined window back with a small decoder written here (Python stages
and observes; it emits nothing). For each access the decoder requires, in order:

  cmp rcx,512; ja TRAP; test rdx,rdx; jz TRAP; cmp INDEX,rcx; jae TRAP;
  [width > 1: mov rsi,rcx; sub rsi,INDEX; cmp rsi,WIDTH; jl TRAP;
              test INDEX,WIDTH-1; ja TRAP;]
  ACCESS; jmp +2; TRAP: ud2

and that every branch lands exactly on that ud2, so no path reaches the access
unless the base is non-null, the length is at most 512, the index is below the
length, the access fits (index + width <= length without wrapping) and, above one
byte, the index is aligned. These are the sequences of kotoba-native's x86_64.cljk
(`emit-kernel-load-u8`, `emit-kernel-store-u8`, `emit-memwidth-window`), with the
operands read from their frame slots as the plain u32 pair does.

Refusals: a base that is not a rooted parameter, and a length that is not the
region's own length, are refused (E7106) for the new accesses as for the old.

Not shown: the machine code was decoded, not executed; no emitted object has run
in a kernel.
"""

import argparse
import hashlib
import importlib.util
import json
import struct
from pathlib import Path

MAC_GATE = Path(__file__).with_name("check-aiueos-user-macos-native.py")
FUEL = "1024"
SOURCE = """(ns widths (:export [ld8 st8 ld16 st16 ld64 st64]))
(defn ld8 [b :i64 n :i64 i :i64] :i64 (kernel-load-u8 b n i))
(defn st8 [b :i64 n :i64 i :i64 v :i64] :i64 (kernel-store-u8 b n i v))
(defn ld16 [b :i64 n :i64 i :i64] :i64 (kernel-load-u16 b n i))
(defn st16 [b :i64 n :i64 i :i64 v :i64] :i64 (kernel-store-u16 b n i v))
(defn ld64 [b :i64 n :i64 i :i64] :i64 (kernel-load-u64 b n i))
(defn st64 [b :i64 n :i64 i :i64 v :i64] :i64 (kernel-store-u64 b n i v))
"""
EXPECTED = [("load", 1), ("store", 1), ("load", 2), ("store", 2), ("load", 8), ("store", 8)]
ACCESS = {("load", 1): "0fb60402", ("load", 2): "0fb70402", ("load", 8): "488b0402",
          ("store", 1): "88043a", ("store", 2): "6689043a", ("store", 8): "4889043a"}
REFUSALS = {
    "unrooted-base": "(ns refused (:export [f]))\n(defn f [b :i64 n :i64 i :i64] :i64 (kernel-load-u8 (+ b 1) n i))\n",
    "free-length": "(ns refused (:export [f]))\n(defn f [b :i64 n :i64 i :i64 v :i64] :i64 (kernel-store-u64 b 16 i v))\n",
    "unrooted-base-store16": "(ns refused (:export [f]))\n(defn f [b :i64 n :i64 i :i64 v :i64] :i64 (kernel-store-u16 (+ b 2) n i v))\n",
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


def decode_window(text, at):
    """Decode one window access starting at its `cmp rcx,512`; return (kind, width, end)."""
    pos = at
    jumps = []

    def take(hexbytes):
        nonlocal pos
        want = bytes.fromhex(hexbytes)
        if text[pos:pos + len(want)] != want:
            raise ValueError(f"at {pos:#x}: want {hexbytes}, have {text[pos:pos + len(want)].hex()}")
        pos += len(want)

    def jcc(opcode):
        nonlocal pos
        take(opcode)
        rel, = struct.unpack_from("<i", text, pos)
        pos += 4
        jumps.append(pos + rel)

    take("4881f900020000")            # cmp rcx,512
    jcc("0f87")                       # ja trap
    take("4885d2")                    # test rdx,rdx
    jcc("0f84")                       # jz trap
    store = text[pos:pos + 3] == bytes.fromhex("4839cf")
    take("4839cf" if store else "4839c8")   # cmp rdi|rax,rcx
    jcc("0f83")                       # jae trap
    width = 1
    if text[pos:pos + 3] == bytes.fromhex("4889ce"):
        take("4889ce")                          # mov rsi,rcx
        take("4829fe" if store else "4829c6")   # sub rsi,rdi|rax
        take("4881fe")
        width, = struct.unpack_from("<i", text, pos)
        pos += 4
        jcc("0f8c")                             # jl trap
        take("48f7c7" if store else "48f7c0")   # test rdi|rax,imm32
        mask, = struct.unpack_from("<i", text, pos)
        pos += 4
        if mask != width - 1 or width not in (2, 8):
            raise ValueError(f"width {width} mask {mask}")
        jcc("0f87")                             # ja trap
    kind = "store" if store else "load"
    take(ACCESS[(kind, width)])
    take("eb02")
    trap = pos
    take("0f0b")
    if any(target != trap for target in jumps):
        raise ValueError(f"a branch misses the ud2 at {trap:#x}: {[hex(j) for j in jumps]}")
    return kind, width, pos, len(jumps)


def main(compiler, output):
    gate = gate_module()
    gate.verify_macho(compiler)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    (output / "w.kotoba").write_text(SOURCE)
    gate.native_run(compiler, output, "compile", "w.kotoba", "--target", "x86_64-aiueos-kernel-v1",
                    "--output", "w.o", "--fuel", FUEL)
    text = text_section(output / "w.o")
    head = bytes.fromhex("4881f900020000")
    starts = []
    i = text.find(head)
    while i >= 0:
        starts.append(i)
        i = text.find(head, i + 1)
    found = []
    for at in starts:
        kind, width, end, njumps = decode_window(text, at)
        found.append((kind, width))
    if found != EXPECTED:
        raise ValueError(f"windows {found}, want {EXPECTED}")
    report = {"windows": [{"kind": k, "width": w} for k, w in found],
              "object": hashlib.sha256((output / "w.o").read_bytes()).hexdigest()}

    refused = []
    for name, source in REFUSALS.items():
        (output / f"{name}.kotoba").write_text(source)
        result = gate.native_run(compiler, output, "compile", f"{name}.kotoba", "--target",
                                 "x86_64-aiueos-kernel-v1", "--output", f"{name}.o", "--fuel", FUEL, expected=1)
        message = (result.stdout + result.stderr).decode(errors="replace")
        if "E7106" not in message or (output / f"{name}.o").exists():
            raise ValueError(f"{name} was not refused with E7106 and no output: {message}")
        refused.append(name)
    report["refused"] = refused
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS_AIUEOS_OBJECT_WINDOWS " + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True,
                        help="a signed Mac native Amu compiler image (the Mac gate's F*-signed.macho)")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
