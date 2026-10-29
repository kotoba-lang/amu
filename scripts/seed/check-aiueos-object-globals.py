#!/usr/bin/env python3
"""The aiueos kernel object route exports data cells as GLOBAL OBJECT symbols (JUN-556 D3b, ADR 0380).

A private cell-name-<k>-<symbol> [] gives cell k (the 8-byte cell cell-load-<k> and cell-store-<k> address,
.data offset 80 + 8k) the symbol <symbol>: GLOBAL OBJECT, size 8, defined in .data. Other objects (entry.S,
C) link to it by name, the way kernel/entry.S links aiueos_apic_timer_ticks. Symbols come after the exports
and the externs in .symtab; sh_info still names the first global; the context stays the only LOCAL symbol.

Reads objects back with the independent ELF parser of check-aiueos-object-exports.py. Positive: two symbols
(cell 0 and cell 3) next to an export and an extern, .data large enough for cell 3. Refused (E7102, nothing
written): k = 64, a bad symbol, a symbol equal to an export, to an extern or to another data symbol, a
parameter on the declaration, a body other than the placeholder 0, more than sixteen symbols, and the image
route. No x86 machine ran these symbols; the linker does the linking.
"""

import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).parent
SOURCE = ("(ns globals (:export [f]))\n"
          "(defn- extern-sink [a :i64] :i64 0)\n"
          "(defn- cell-load-0 [] :i64 0)\n(defn- cell-store-3 [v :i64] :i64 0)\n"
          "(defn- cell-name-0-aiueos_apic_timer_ticks [] :i64 0)\n"
          "(defn- cell-name-3-aiueos_apic_mmio_base [] :i64 0)\n"
          "(defn f [x :i64] :i64 (extern-sink (cell-store-3 (cell-load-0))))\n")


def refused(decl, call="x"):
    return f"(ns r (:export [f]))\n(defn- extern-sink [a :i64] :i64 0)\n{decl}\n(defn f [x :i64] :i64 {call})\n"


CASES = {
    "k64": refused("(defn- cell-name-64-a [] :i64 0)"),
    "bad-symbol": refused("(defn- cell-name-1-Bad [] :i64 0)"),
    "no-dash": refused("(defn- cell-name-1 [] :i64 0)"),
    "equals-export": refused("(defn- cell-name-1-f [] :i64 0)"),
    "equals-extern": refused("(defn- cell-name-1-sink [] :i64 0)"),
    "equals-other": "(ns r (:export [f]))\n(defn- cell-name-1-dup [] :i64 0)\n(defn- cell-name-2-dup [] :i64 0)\n(defn f [x :i64] :i64 x)\n",
    "with-param": refused("(defn- cell-name-1-a [v :i64] :i64 0)"),
    "body-not-zero": refused("(defn- cell-name-1-a [] :i64 5)"),
    "seventeen": "(ns r (:export [f]))\n" + "".join(f"(defn- cell-name-{i}-s{i} [] :i64 0)\n" for i in range(17)) + "(defn f [x :i64] :i64 x)\n",
}


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(exports, path):
    obj = exports.read_elf(path)
    syms = obj["symbols"]
    names = [s[0] for s in syms]
    if names != ["", "context", "f", "sink", "aiueos_apic_timer_ticks", "aiueos_apic_mmio_base"]:
        raise ValueError(f"symbols {names}")
    if obj["sym_info"] != 2:
        raise ValueError("sh_info must name the first global (index 2)")
    for sym, value in ((syms[4], 80), (syms[5], 80 + 24)):
        if sym[1] != 0x11 or sym[2] != obj["data_index"] or sym[3] != value or sym[4] != 8:
            raise ValueError(f"data symbol {sym}, want GLOBAL OBJECT in .data at {value} size 8")
    if syms[3][1:] != (0x10, 0, 0, 0):
        raise ValueError(f"extern {syms[3]}")
    if [s[1] for s in syms].count(0x01) != 1:
        raise ValueError("the context must stay the only LOCAL symbol")


def main(compiler, output):
    exports = load("check-aiueos-object-exports")
    gate = exports.gate_module()
    gate.verify_macho(compiler)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    report = {}
    _, path = exports.compile_object(gate, compiler, output, "globals", SOURCE)
    check(exports, path)
    report["globals"] = {"bytes": path.stat().st_size}
    for name, source in CASES.items():
        result, bad = exports.compile_object(gate, compiler, output, name, source, expected=1)
        if bad.exists() or "E7102" not in (result.stdout + result.stderr).decode(errors="replace"):
            raise ValueError(f"{name}: not refused with E7102 and no output")
        report[name] = "refused E7102"
    (output / "image.kotoba").write_text("(ns i (:export [main]))\n(defn- cell-name-0-a [] :i64 0)\n(defn main [] :i64 0)\n")
    result = gate.native_run(compiler, output, "compile", "image.kotoba", "--target", "x86_64-aiueos-kernel-v1",
                             "--artifact", "image", "--output", "image.elf", "--fuel", "1024", expected=1)
    if (output / "image.elf").exists() or "E7102" not in (result.stdout + result.stderr).decode(errors="replace"):
        raise ValueError("a data symbol on the image route was not refused with E7102")
    report["image"] = "refused E7102"
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS_AIUEOS_OBJECT_GLOBALS " + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
