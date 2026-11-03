#!/usr/bin/env python3
"""The aiueos kernel object route can hand out the address of a data cell (JUN-556 D6, ADR 0382).

A private function cell-addr-<k> [] (k canonical decimal below 64, body the placeholder 0) returns the address of
cell k: `lea rax,[rip+disp32]` with an R_X86_64_PC32 relocation against the context symbol, addend 80 + 8k - 4, the
same relocation as a cell access. It is how an extern function is given somewhere to write: the cells k, k+1, ... the
function also loads are the region, and .data holds exactly the cells some stub names. The address is an ordinary value, not
a rooted base, so no window access and no record access accepts it.

Compiles sources with a native Amu compiler and reads the objects back with the independent ELF parser of
check-aiueos-object-exports.py. Positive: an export that passes cell-addr-1 to a declared extern and reads cells 1 and 2;
the lea site is checked byte by byte and its relocation (offset, PC32, addend 84) is found exactly once. Refused: a
malformed name or a parameter (E7102), the address used as a window base or a record base (E7106), the image route (E7102).
In every refusal nothing is written.

No x86 machine ran this object in this gate; the QEMU differential check in the kotoba repository runs the consumer.
"""

import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).parent

POSITIVE = ("(ns celladdr (:export [f]))\n"
            "(defn- extern-sink [a :i64] :i64 0)\n"
            "(defn- cell-addr-1 [] :i64 0)\n(defn- cell-load-1 [] :i64 0)\n(defn- cell-load-2 [] :i64 0)\n"
            "(defn f [x :i64] :i64 (+ (extern-sink (cell-addr-1)) (+ (cell-load-1) (cell-load-2))))\n")
LEA = b"\x48\x8d\x05\x00\x00\x00\x00"


def refused_source(decl, call, params="x :i64"):
    return ("(ns r (:export [f]))\n(defn- extern-sink [a :i64] :i64 0)\n" + decl +
            f"\n(defn f [{params}] :i64 {call})\n")


CASES_7102 = {
    "k-64": refused_source("(defn- cell-addr-64 [] :i64 0)", "(extern-sink (cell-addr-64))"),
    "leading-zero": refused_source("(defn- cell-addr-01 [] :i64 0)", "(extern-sink (cell-addr-01))"),
    "not-a-number": refused_source("(defn- cell-addr-x [] :i64 0)", "(extern-sink (cell-addr-x))"),
    "with-param": refused_source("(defn- cell-addr-1 [v :i64] :i64 0)", "(extern-sink (cell-addr-1 x))"),
    "body-not-zero": refused_source("(defn- cell-addr-1 [] :i64 7)", "(extern-sink (cell-addr-1))"),
}

CASES_7106 = {
    "address-as-window-base": refused_source(
        "(defn- cell-addr-1 [] :i64 0)", "(kernel-load-u32 (cell-addr-1) n 0)", "n :i64"),
    "address-as-record-base": refused_source(
        "(defn- cell-addr-1 [] :i64 0)\n(defn- record-load-u32-0-40 [b :i64] :i64 0)", "(record-load-u32-0-40 (cell-addr-1))"),
}


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(exports, path):
    obj = exports.read_elf(path)
    text = obj["text"]
    if text.count(LEA) != 1:
        raise ValueError(f"expected exactly one lea rax,[rip+0], found {text.count(LEA)}")
    site = text.index(LEA) + 3
    context_pc32 = 1 << 32 | 2
    addends = sorted(a for off, info, a in obj["relas"] if off == site and info == context_pc32)
    if addends != [80 + 8 * 1 - 4]:
        raise ValueError(f"the lea site {site} has relocations {addends}, want one PC32 against context with addend 84")
    others = sorted((off, a) for off, info, a in obj["relas"] if info == context_pc32 and off != site and a != -4)
    if sorted(a for _, a in others) != [84, 92]:
        raise ValueError(f"cell access relocations {others}, want addends 84 and 92")


def refused(gate, exports, compiler, output, name, source, code):
    result, bad = exports.compile_object(gate, compiler, output, name, source, expected=1)
    if bad.exists() or code not in (result.stdout + result.stderr).decode(errors="replace"):
        raise ValueError(f"{name}: not refused with {code} and no output")
    return f"refused {code}"


def main(compiler, output):
    exports = load("check-aiueos-object-exports")
    gate = exports.gate_module()
    gate.verify_macho(compiler)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    report = {}
    _, path = exports.compile_object(gate, compiler, output, "celladdr", POSITIVE)
    check(exports, path)
    report["celladdr"] = {"bytes": path.stat().st_size}
    for name, source in CASES_7102.items():
        report[name] = refused(gate, exports, compiler, output, name, source, "E7102")
    for name, source in CASES_7106.items():
        report[name] = refused(gate, exports, compiler, output, name, source, "E7106")
    (output / "image.kotoba").write_text("(ns i (:export [main]))\n(defn- cell-addr-1 [] :i64 0)\n(defn main [] :i64 (cell-addr-1))\n")
    result = gate.native_run(compiler, output, "compile", "image.kotoba", "--target", "x86_64-aiueos-kernel-v1",
                             "--artifact", "image", "--output", "image.elf", "--fuel", "1024", expected=1)
    if (output / "image.elf").exists() or "E7102" not in (result.stdout + result.stderr).decode(errors="replace"):
        raise ValueError("a cell-addr declaration on the image route was not refused with E7102")
    report["image"] = "refused E7102"
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS_AIUEOS_OBJECT_CELLADDR " + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
