#!/usr/bin/env python3
"""The aiueos kernel object route can call declared functions of other objects (JUN-556 D1, ADR 0380).

A private function named extern-<symbol> declares a function the linker supplies. The
object route turns each call of it into `call rel32` plus `mov r9,[rbp-8]` and an
R_X86_64_PLT32 addend -4 relocation against an undefined GLOBAL NOTYPE symbol <symbol>.

Compiles sources with a native Amu compiler and reads the objects back with the same
independent ELF parser as check-aiueos-object-exports.py (Python stages and observes;
it emits nothing):

* one extern called twice and a second extern called once: three PLT32 relocations,
  two undefined symbols in declaration order, sh_info still naming the first global,
  every call site `e8 00000000 4c 8b 4d f8` (the displacement is the linker's);
* a source with no extern declaration compiles as before (its digest is the
  one-export gate's pinned one, checked there);
* seventeen declarations: refused (E7102), nothing written;
* an extern that takes six parameters: refused, nothing written;
* a declaration whose body is not the placeholder 0, whose symbol is not [a-z_][a-z0-9_]*,
  or that is named like an export: refused, nothing written (review of amu#1662);
* the same declaration on the image route (--artifact image): refused, no image.

The byte sequence after each call was assembled independently with clang's integrated
assembler (ADR 0380); no x86 machine ran it here.
"""

import argparse
import hashlib
import importlib.util
import json
import struct
from pathlib import Path

HERE = Path(__file__).parent
CALL_TAIL = bytes.fromhex("4c8b4df8")        # mov r9, [rbp-8]

SOURCE = ("(ns ext (:export [f]))\n"
          "(defn- extern-sink_a [a :i64 b :i64] :i64 0)\n"
          "(defn- extern-sink_b [a :i64] :i64 0)\n"
          "(defn f [x :i64] :i64\n"
          "  (+ (extern-sink_a x 7) (+ (extern-sink_b x) (extern-sink_a 1 2))))\n")
TOO_MANY = ("(ns many (:export [f]))\n"
            + "".join(f"(defn- extern-e{i} [a :i64] :i64 0)\n" for i in range(17))
            + "(defn f [x :i64] :i64 (extern-e0 x))\n")
SIX_PARAMS = ("(ns six (:export [f]))\n"
              "(defn- extern-six [a :i64 b :i64 c :i64 d :i64 e :i64 g :i64] :i64 0)\n"
              "(defn f [x :i64] :i64 (extern-six x x x x x x))\n")


BODY_NOT_ZERO = ("(ns b (:export [f]))\n(defn- extern-sink [x :i64] :i64 (+ x 99))\n"
                 "(defn f [x :i64] :i64 (extern-sink x))\n")
BODY_CONST = ("(ns c (:export [f]))\n(defn- extern-sink [x :i64] :i64 7)\n"
              "(defn f [x :i64] :i64 (extern-sink x))\n")
BAD_NAME = ("(ns n (:export [f]))\n(defn- extern-Bad [x :i64] :i64 0)\n"
            "(defn f [x :i64] :i64 (extern-Bad x))\n")
CLASH = ("(ns k (:export [sink]))\n(defn- extern-sink [x :i64] :i64 0)\n"
         "(defn sink [x :i64] :i64 (extern-sink x))\n")
IMAGE = ("(ns i (:export [main]))\n(defn- extern-sink [] :i64 0)\n"
         "(defn main [] :i64 (extern-sink))\n")


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_externs(obj):
    syms, relas, text = obj["symbols"], obj["relas"], obj["text"]
    names = [s[0] for s in syms]
    if names != ["", "context", "f", "sink_a", "sink_b"]:
        raise ValueError(f"symbols {names}")
    for sym in syms[3:]:
        if sym[1] != 0x10 or sym[2] != 0 or sym[3] != 0 or sym[4] != 0:
            raise ValueError(f"extern {sym[0]} is {sym[1:]}, want GLOBAL NOTYPE UNDEF")
    if obj["sym_info"] != 2:
        raise ValueError("sh_info must name the first global (index 2)")
    if len(relas) != 4:
        raise ValueError(f"{len(relas)} relocations, want 1 context + 3 calls")
    if relas[0] != (3, 1 << 32 | 2, -4):
        raise ValueError(f"context relocation {relas[0]}")
    wanted = [3, 4, 3]       # sink_a (symbol 3), sink_b (symbol 4), sink_a again, in code order
    calls = sorted(relas[1:], key=lambda r: r[0])
    for (offset, info, addend), sym in zip(calls, wanted):
        if info != (sym << 32 | 4) or addend != -4:
            raise ValueError(f"call relocation {(offset, info, addend)}, want symbol {sym} PLT32 -4")
        if text[offset - 1] != 0xE8 or text[offset:offset + 4] != b"\0\0\0\0":
            raise ValueError(f"call at {offset - 1} is not e8 00000000")
        if text[offset + 4:offset + 8] != CALL_TAIL:
            raise ValueError(f"call at {offset - 1} is not followed by mov r9,[rbp-8]: {text[offset + 4:offset + 8].hex()}")


def main(compiler, output):
    exports = load("check-aiueos-object-exports")
    gate = exports.gate_module()
    gate.verify_macho(compiler)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    report = {}

    _, path = exports.compile_object(gate, compiler, output, "ext", SOURCE)
    check_externs(exports.read_elf(path))
    report["externs"] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}

    for name, source in (("many", TOO_MANY), ("six", SIX_PARAMS), ("body-not-zero", BODY_NOT_ZERO),
                         ("body-const", BODY_CONST), ("bad-name", BAD_NAME), ("export-clash", CLASH)):
        result, bad = exports.compile_object(gate, compiler, output, name, source, expected=1)
        if bad.exists():
            raise ValueError(f"{name}: an object was written")
        report[name] = "refused: " + (result.stdout + result.stderr).decode(errors="replace").strip()[:120]

    (output / "image.kotoba").write_text(IMAGE)
    result = gate.native_run(compiler, output, "compile", "image.kotoba", "--target", "x86_64-aiueos-kernel-v1",
                             "--artifact", "image", "--output", "image.elf", "--fuel", "1024", expected=1)
    if (output / "image.elf").exists() or "E7102" not in (result.stdout + result.stderr).decode(errors="replace"):
        raise ValueError("an extern declaration on the image route was not refused with E7102")
    report["image"] = "refused E7102"

    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS_AIUEOS_OBJECT_EXTERNS " + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
