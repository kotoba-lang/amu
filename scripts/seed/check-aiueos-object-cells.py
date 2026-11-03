#!/usr/bin/env python3
"""The aiueos kernel object route has 8-byte data cells after the context (JUN-556 D3, ADR 0380).

Private functions cell-load-<k> [] and cell-store-<k> [v] (k < 64, canonical decimal) name cell k at
.data offset 80 + 8k. A load is `mov rax,[rip+disp]`, a store `mov [rip+disp],rax`; each access has an
R_X86_64_PC32 relocation against the context symbol with addend 80 + 8k - 4 and a zero displacement.
.data grows to 80 + 8 * (highest named cell + 1) zero bytes; sections and symbols stay as they were.

Compiles sources with a native Amu compiler and reads the objects back with the independent ELF parser of
check-aiueos-object-exports.py. Positive: cells 0 and 3 read and written by one export; the .data size, the
relocations and the access bytes are checked. A source without a cell compiles to the bytes it always did
(the one-export gate pins that). Refused (E7102, nothing written): k = 64, a leading zero, a non-digit
suffix, a load with a parameter, a store without one, a body other than the placeholder 0, cells on the
image route. The extern gate's cases are unaffected.

No x86 machine ran these accesses here.
"""

import argparse
import importlib.util
import json
import struct
from pathlib import Path

HERE = Path(__file__).parent
SOURCE = ("(ns cells (:export [f]))\n"
          "(defn- cell-load-0 [] :i64 0)\n(defn- cell-store-0 [v :i64] :i64 0)\n"
          "(defn- cell-load-3 [] :i64 0)\n(defn- cell-store-3 [v :i64] :i64 0)\n"
          "(defn f [x :i64] :i64\n"
          "  (+ (cell-store-3 (+ (cell-load-0) x)) (+ (cell-store-0 x) (cell-load-3))))\n")
LOAD, STORE = bytes.fromhex("488b05"), bytes.fromhex("488905")


def refused(name, decl, call):
    return (f"(ns r (:export [f]))\n{decl}\n(defn f [x :i64] :i64 {call})\n")


CASES = {
    "k64": refused("k64", "(defn- cell-load-64 [] :i64 0)", "(cell-load-64)"),
    "leading-zero": refused("lz", "(defn- cell-load-07 [] :i64 0)", "(cell-load-07)"),
    "non-digit": refused("nd", "(defn- cell-load-x [] :i64 0)", "(cell-load-x)"),
    "load-with-param": refused("lp", "(defn- cell-load-1 [a :i64] :i64 0)", "(cell-load-1 x)"),
    "store-without-param": refused("sp", "(defn- cell-store-1 [] :i64 0)", "(cell-store-1)"),
    "body-not-zero": refused("bz", "(defn- cell-load-1 [] :i64 5)", "(cell-load-1)"),
}


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sections(blob):
    shoff, = struct.unpack_from("<Q", blob, 40)
    shnum, shstr = struct.unpack_from("<HH", blob, 60)
    secs = [struct.unpack_from("<IIQQQQIIQQ", blob, shoff + 64 * i) for i in range(shnum)]
    table = secs[shstr][4]
    name = lambda o: blob[table + o:blob.index(b"\0", table + o)].decode()
    return {name(s[0]): s for s in secs}


def check(path):
    blob = path.read_bytes()
    by = sections(blob)
    data = by[".data"]
    if data[5] != 80 + 8 * 4:
        raise ValueError(f".data is {data[5]} bytes, want {80 + 8 * 4}")
    if blob[data[4] + 80:data[4] + data[5]] != b"\0" * 32:
        raise ValueError("cells are not zero")
    text = blob[by[".text"][4]:by[".text"][4] + by[".text"][5]]
    rela = by[".rela.text"]
    rels = [struct.unpack_from("<QQq", blob, rela[4] + 24 * i) for i in range(rela[5] // 24)]
    if rels[0] != (3, 1 << 32 | 2, -4):
        raise ValueError(f"context relocation {rels[0]}")
    cells = sorted(rels[1:], key=lambda r: r[0])
    if len(cells) != 4:
        raise ValueError(f"{len(cells)} cell relocations, want 4")
    seen = {}
    for offset, info, addend in cells:
        if info != (1 << 32 | 2) or addend not in (80 - 4, 80 + 24 - 4):
            raise ValueError(f"cell relocation {(offset, info, addend)}")
        if text[offset:offset + 4] != b"\0\0\0\0":
            raise ValueError(f"displacement at {offset} is not zero")
        opcode = text[offset - 3:offset]
        if opcode not in (LOAD, STORE):
            raise ValueError(f"access at {offset - 3} is {opcode.hex()}")
        seen[(opcode, addend)] = seen.get((opcode, addend), 0) + 1
    want = {(LOAD, 76): 1, (STORE, 76): 1, (LOAD, 100): 1, (STORE, 100): 1}
    if seen != want:
        raise ValueError(f"accesses {seen}, want {want}")


def main(compiler, output):
    exports = load("check-aiueos-object-exports")
    gate = exports.gate_module()
    gate.verify_macho(compiler)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    report = {}
    _, path = exports.compile_object(gate, compiler, output, "cells", SOURCE)
    check(path)
    report["cells"] = {"bytes": path.stat().st_size}
    for name, source in CASES.items():
        result, bad = exports.compile_object(gate, compiler, output, name, source, expected=1)
        if bad.exists() or "E7102" not in (result.stdout + result.stderr).decode(errors="replace"):
            raise ValueError(f"{name}: not refused with E7102 and no output")
        report[name] = "refused E7102"
    (output / "image.kotoba").write_text("(ns i (:export [main]))\n(defn- cell-load-0 [] :i64 0)\n(defn main [] :i64 (cell-load-0))\n")
    result = gate.native_run(compiler, output, "compile", "image.kotoba", "--target", "x86_64-aiueos-kernel-v1",
                             "--artifact", "image", "--output", "image.elf", "--fuel", "1024", expected=1)
    if (output / "image.elf").exists() or "E7102" not in (result.stdout + result.stderr).decode(errors="replace"):
        raise ValueError("a cell on the image route was not refused with E7102")
    report["image"] = "refused E7102"
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS_AIUEOS_OBJECT_CELLS " + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
