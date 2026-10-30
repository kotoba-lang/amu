#!/usr/bin/env python3
"""Window accesses on the aiueos object route's own .bss / .high_bss arrays (JUN-553, ADR 0387).

The address an array stub bss-addr-<k>-<N> / highbss-addr-<k>-<N> returns (ADR 0385) is a rooted base whose region is the
array: the ordinary window accesses (kernel-load-* / kernel-store-*, their 16 KiB tier, kernel-subregion) accept it when the
length operand is the literal N. Compiles with a native Amu compiler:

* positive: one object whose five exports store, load and sum u8 / u64 windows over a 64-byte .bss array, use the 16 KiB tier
  on a 4096-byte .high_bss array and read through a subregion. Each window's inlined check starts with `cmp rcx,BOUND` (512 or
  16384) and every one sits after the array's `lea rax,[rip+disp]` (an R_X86_64_PC32 against the section symbol);
* refused (E7106, nothing written): a length that is a parameter, a literal other than N, the address as a record base, and
  arithmetic on the address;
* unchanged: an object that names no array is byte-identical to check-aiueos-object-exports.py's pinned one-export object.

docs/evidence/array-windows-20261030/ ran the positive object under QEMU by hand.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).parent
POSITIVE = """(ns pos (:export [put get sum big part]))
(defn- bss-addr-0-64 [] :i64 0)
(defn- highbss-addr-0-4096 [] :i64 0)
(defn put [i :i64 v :i64] :i64 (kernel-store-u8 (bss-addr-0-64) 64 i v))
(defn get [i :i64] :i64 (kernel-load-u8 (bss-addr-0-64) 64 i))
(defn sum [] :i64 (+ (kernel-load-u64 (bss-addr-0-64) 64 0) (kernel-load-u64 (bss-addr-0-64) 64 56)))
(defn big [i :i64 v :i64] :i64 (let [w (kernel-store-u16-16k (highbss-addr-0-4096) 4096 i v)] (kernel-load-u16-16k (highbss-addr-0-4096) 4096 i)))
(defn part [i :i64] :i64 (let [s (kernel-subregion (bss-addr-0-64) 64 32 16)] (kernel-load-u8 s 16 i)))
"""


def refused(decl, body):
    return f"(ns r (:export [f]))\n(defn- bss-addr-0-64 [] :i64 0)\n{decl}\n(defn f [i :i64 n :i64] :i64 {body})\n"


REFUSALS = {
    "param-length": refused("", "(kernel-load-u8 (bss-addr-0-64) n i)"),
    "wrong-literal": refused("", "(kernel-load-u8 (bss-addr-0-64) 128 i)"),
    "record-base": refused("(defn- record-load-u32-0-64 [b :i64] :i64 0)", "(record-load-u32-0-64 (bss-addr-0-64))"),
    "arithmetic": refused("", "(kernel-load-u8 (+ (bss-addr-0-64) 1) 64 i)"),
}
LEA = bytes.fromhex("488d0500000000")


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(compiler, output):
    exports = load("check-aiueos-object-exports")
    arrays = load("check-aiueos-object-arrays")
    gate = exports.gate_module()
    gate.verify_macho(compiler)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    report = {}
    _, path = exports.compile_object(gate, compiler, output, "pos", POSITIVE)
    obj = arrays.read_elf(path)
    if obj["names"][7:] != [".bss", ".high_bss"] or obj["secs"][7][5] != 64 or obj["secs"][8][5] != 4096:
        raise ValueError(f"sections {obj['names']} sizes {[s[5] for s in obj['secs'][7:]]}")
    text = obj["text"]
    small, large = text.count(bytes.fromhex("4881f900020000")), text.count(bytes.fromhex("4881f900400000"))
    if (small, large) != (5, 2):
        raise ValueError(f"windows: {small} at 512 and {large} at 16384, want 5 and 2")
    leas = [off for off, info, a in obj["relas"] if text[off - 3:off + 4] == LEA and info & 0xFFFFFFFF == 2 and info >> 32 in (2, 3)]
    if len(leas) != 7:
        raise ValueError(f"{len(leas)} array lea relocations, want 7")
    report["positive"] = {"bytes": path.stat().st_size, "windows512": small, "windows16k": large, "arrayLeas": len(leas)}
    for name, source in REFUSALS.items():
        result, bad = exports.compile_object(gate, compiler, output, name, source, expected=1)
        if bad.exists() or "E7106" not in (result.stdout + result.stderr).decode(errors="replace"):
            raise ValueError(f"{name}: not refused with E7106 and no output")
        report[name] = "refused E7106"
    _, one = exports.compile_object(gate, compiler, output, "one", exports.ONE_SOURCE)
    if hashlib.sha256(one.read_bytes()).hexdigest() != exports.ONE_SHA256:
        raise ValueError("an object without arrays changed its bytes")
    report["withoutArrays"] = "byte-identical"
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS_AIUEOS_OBJECT_ARRAY_WINDOWS " + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
