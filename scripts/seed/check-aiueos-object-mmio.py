#!/usr/bin/env python3
"""The aiueos kernel object route has fixed-address MMIO accesses (JUN-556 D4, ADR 0380).

Private functions mmio-load32-<addr> [] and mmio-store32-<addr> [v] name one of five local-APIC registers
(addr: eight lowercase hex digits, fee00020 fee000f0 fee00320 fee00380 fee003e0; no other address is
admitted). A load is `movabs rax,addr; mov eax,[rax]`, a store `movabs rcx,addr; mov [rcx],eax`. The address
is an immediate: the object gets no new relocation, symbol or data, only the bytes below in .text.

Compiles sources with a native Amu compiler and reads the objects back with the independent ELF parser of
check-aiueos-object-exports.py. Positive: reads of fee00320 and fee000f0 and writes of fee00380 and fee00320
by one export; the .text bytes and the single context relocation are checked. Refused (E7102, nothing written):
an address outside the list, uppercase hex, a short or long address, a load with a parameter, a store without
one, a body other than the placeholder 0, and the image route.

No x86 machine ran these accesses here, and the registers are only addressed, never touched.
"""

import argparse
import importlib.util
import json
import struct
from pathlib import Path

HERE = Path(__file__).parent
SOURCE = ("(ns mmio (:export [f]))\n"
          "(defn- mmio-load32-fee00320 [] :i64 0)\n(defn- mmio-store32-fee00320 [v :i64] :i64 0)\n"
          "(defn- mmio-load32-fee000f0 [] :i64 0)\n(defn- mmio-store32-fee00380 [v :i64] :i64 0)\n"
          "(defn f [x :i64] :i64\n"
          "  (+ (mmio-store32-fee00380 (+ (mmio-load32-fee00320) x)) (+ (mmio-store32-fee00320 x) (mmio-load32-fee000f0))))\n")


def load_seq(addr):
    return b"\x48\xb8" + struct.pack("<Q", addr) + b"\x8b\x00"


def store_seq(addr):
    return b"\x48\xb9" + struct.pack("<Q", addr) + b"\x89\x01"


def refused(decl, call):
    return f"(ns r (:export [f]))\n{decl}\n(defn f [x :i64] :i64 {call})\n"


CASES = {
    "address-not-listed": refused("(defn- mmio-load32-fee00330 [] :i64 0)", "(mmio-load32-fee00330)"),
    "uppercase-hex": refused("(defn- mmio-load32-FEE00320 [] :i64 0)", "(mmio-load32-FEE00320)"),
    "short-address": refused("(defn- mmio-load32-ee00320 [] :i64 0)", "(mmio-load32-ee00320)"),
    "long-address": refused("(defn- mmio-load32-0fee00320 [] :i64 0)", "(mmio-load32-0fee00320)"),
    "load-with-param": refused("(defn- mmio-load32-fee00320 [a :i64] :i64 0)", "(mmio-load32-fee00320 x)"),
    "store-without-param": refused("(defn- mmio-store32-fee00320 [] :i64 0)", "(mmio-store32-fee00320)"),
    "body-not-zero": refused("(defn- mmio-load32-fee00320 [] :i64 5)", "(mmio-load32-fee00320)"),
}


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(exports, path):
    obj = exports.read_elf(path)
    if len(obj["relas"]) != 1 or obj["relas"][0] != (3, 1 << 32 | 2, -4):
        raise ValueError(f"relocations {obj['relas']}: only the context relocation is expected")
    text = obj["text"]
    for seq in (load_seq(0xfee00320), load_seq(0xfee000f0), store_seq(0xfee00380), store_seq(0xfee00320)):
        if text.count(seq) != 1:
            raise ValueError(f"expected exactly one {seq.hex()}, found {text.count(seq)}")


def main(compiler, output):
    exports = load("check-aiueos-object-exports")
    gate = exports.gate_module()
    gate.verify_macho(compiler)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    report = {}
    _, path = exports.compile_object(gate, compiler, output, "mmio", SOURCE)
    check(exports, path)
    report["mmio"] = {"bytes": path.stat().st_size}
    for name, source in CASES.items():
        result, bad = exports.compile_object(gate, compiler, output, name, source, expected=1)
        if bad.exists() or "E7102" not in (result.stdout + result.stderr).decode(errors="replace"):
            raise ValueError(f"{name}: not refused with E7102 and no output")
        report[name] = "refused E7102"
    (output / "image.kotoba").write_text("(ns i (:export [main]))\n(defn- mmio-load32-fee00320 [] :i64 0)\n(defn main [] :i64 (mmio-load32-fee00320))\n")
    result = gate.native_run(compiler, output, "compile", "image.kotoba", "--target", "x86_64-aiueos-kernel-v1",
                             "--artifact", "image", "--output", "image.elf", "--fuel", "1024", expected=1)
    if (output / "image.elf").exists() or "E7102" not in (result.stdout + result.stderr).decode(errors="replace"):
        raise ValueError("an MMIO access on the image route was not refused with E7102")
    report["image"] = "refused E7102"
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS_AIUEOS_OBJECT_MMIO " + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
