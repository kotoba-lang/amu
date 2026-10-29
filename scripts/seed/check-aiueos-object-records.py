#!/usr/bin/env python3
"""The aiueos kernel object route has fixed-size record accesses (JUN-556 D5, ADR 0381).

Private functions record-load-<w>-<off>-<N> [b] and record-store-<w>-<off>-<N> [b v] (w one of u8 u16 u32 u64,
off and N canonical decimals, N a multiple of 4 in 8..256, off a multiple of the width, off + width <= N) read or write
the N-byte record that an exported function's parameter b points at, at the literal offset off. An access is
`mov rdx,[b]; (mov rax,[v];) test rdx,rdx; jz ud2; <access [rdx+off32]>; jmp +2; ud2`. The object gets no new
relocation, symbol or data, only the bytes below in .text.

The base must be an unassigned parameter of an exported function, every access to one parameter names the same N,
and that parameter is not also a window base.

Compiles sources with a native Amu compiler and reads the objects back with the independent ELF parser of
check-aiueos-object-exports.py. Positive: a 40-byte record written at the offsets of
struct aiueos_device_worker_poll (u64 at 0 and 8, u32 at 16, u8 at 20..23) and read back at 16 and 20, plus the other
widths at their own offsets; the instruction bytes are checked one by one. Refused: malformed names and sizes (E7102);
a base that is a literal, arithmetic, a non-export parameter, a second N for one parameter, a parameter used as a record
and as a window base (E7106); the image route (E7102). In every refusal nothing is written.

No x86 machine ran these accesses in this gate; the QEMU differential check is scripts/apic-x86-smoke in the kotoba
repository for the same shape of object.
"""

import argparse
import importlib.util
import json
import struct
from pathlib import Path

HERE = Path(__file__).parent

# (name, params, access bytes before the 32-bit offset, jz distance)
ACCESS = {
    ("load", "u8"): (b"\x0f\xb6\x82", 9), ("load", "u16"): (b"\x0f\xb7\x82", 9),
    ("load", "u32"): (b"\x8b\x82", 8), ("load", "u64"): (b"\x48\x8b\x82", 9),
    ("store", "u8"): (b"\x88\x82", 8), ("store", "u16"): (b"\x66\x89\x82", 9),
    ("store", "u32"): (b"\x89\x82", 8), ("store", "u64"): (b"\x48\x89\x82", 9),
}

POSITIVE = [  # (direction, width, offset)
    ("store", "u64", 0), ("store", "u64", 8), ("store", "u32", 16), ("store", "u8", 20), ("store", "u8", 21),
    ("store", "u16", 22), ("load", "u32", 16), ("load", "u8", 20), ("load", "u16", 22), ("load", "u64", 8),
]


def declaration(direction, width, off, n=40):
    params = "[b :i64]" if direction == "load" else "[b :i64 v :i64]"
    return f"(defn- record-{direction}-{width}-{off}-{n} {params} :i64 0)\n"


def positive_source():
    decls = "".join(declaration(d, w, o) for d, w, o in POSITIVE)
    calls = []
    for d, w, o in POSITIVE:
        calls.append(f"(record-{d}-{w}-{o}-40 poll {'x' if d == 'store' else ''})".replace(" )", ")"))
    body = calls[0]
    for call in calls[1:]:
        body = f"(+ {body} {call})"
    return ("(ns records (:export [f]))\n" + decls +
            f"(defn f [http :i64 len :i64 poll :i64 x :i64] :i64 {body})\n")


def sequence(direction, width, off):
    prefix, distance = ACCESS[(direction, width)]
    # test rdx,rdx; jz rel32 (over the access and the two-byte jmp); the access; jmp +2; ud2
    return (b"\x48\x85\xd2\x0f\x84" + struct.pack("<i", distance) + prefix + struct.pack("<I", off) + b"\xeb\x02\x0f\x0b")


def refused_name(decl, call, params="poll :i64"):
    return f"(ns r (:export [f]))\n{decl}\n(defn f [{params}] :i64 {call})\n"


CASES_7102 = {  # malformed declarations
    "past-the-end": refused_name("(defn- record-load-u64-36-40 [b :i64] :i64 0)", "(record-load-u64-36-40 poll)"),
    "misaligned": refused_name("(defn- record-load-u32-2-40 [b :i64] :i64 0)", "(record-load-u32-2-40 poll)"),
    "size-not-multiple-of-4": refused_name("(defn- record-load-u8-0-42 [b :i64] :i64 0)", "(record-load-u8-0-42 poll)"),
    "size-below-8": refused_name("(defn- record-load-u32-0-4 [b :i64] :i64 0)", "(record-load-u32-0-4 poll)"),
    "size-above-256": refused_name("(defn- record-load-u8-0-260 [b :i64] :i64 0)", "(record-load-u8-0-260 poll)"),
    "leading-zero": refused_name("(defn- record-load-u32-08-40 [b :i64] :i64 0)", "(record-load-u32-08-40 poll)"),
    "unknown-width": refused_name("(defn- record-load-u24-0-40 [b :i64] :i64 0)", "(record-load-u24-0-40 poll)"),
    "no-offset": refused_name("(defn- record-load-u32-40 [b :i64] :i64 0)", "(record-load-u32-40 poll)"),
    "load-with-two-params": refused_name("(defn- record-load-u32-0-40 [b :i64 v :i64] :i64 0)", "(record-load-u32-0-40 poll 1)"),
    "store-with-one-param": refused_name("(defn- record-store-u32-0-40 [b :i64] :i64 0)", "(record-store-u32-0-40 poll)"),
    "body-not-zero": refused_name("(defn- record-load-u32-0-40 [b :i64] :i64 5)", "(record-load-u32-0-40 poll)"),
}

CASES_7106 = {  # well-formed declarations used badly
    "literal-base": refused_name("(defn- record-load-u32-0-40 [b :i64] :i64 0)", "(record-load-u32-0-40 0)"),
    "arithmetic-base": refused_name("(defn- record-load-u32-0-40 [b :i64] :i64 0)", "(record-load-u32-0-40 (+ poll 8))"),
    "two-sizes-one-parameter": refused_name(
        "(defn- record-load-u32-0-40 [b :i64] :i64 0)\n(defn- record-load-u32-4-48 [b :i64] :i64 0)",
        "(+ (record-load-u32-0-40 poll) (record-load-u32-4-48 poll))"),
    "record-and-window-base": ("(ns r (:export [f]))\n(defn- record-load-u32-0-40 [b :i64] :i64 0)\n"
                               "(defn f [b :i64 n :i64] :i64 (+ (record-load-u32-0-40 b) (kernel-load-u32 b n 0)))\n"),
    "private-helper-base": ("(ns r (:export [f]))\n(defn- record-load-u32-0-40 [b :i64] :i64 0)\n"
                            "(defn- helper [p :i64] :i64 (record-load-u32-0-40 p))\n"
                            "(defn f [poll :i64] :i64 (helper poll))\n"),
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
    if [s[0] for s in obj["symbols"]] != ["", "context", "f"]:
        raise ValueError(f"symbols {[s[0] for s in obj['symbols']]}: a record access adds none")
    text = obj["text"]
    for direction, width, off in POSITIVE:
        seq = sequence(direction, width, off)
        if text.count(seq) != 1:
            raise ValueError(f"expected exactly one {direction} {width} at {off} ({seq.hex()}), found {text.count(seq)}")


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
    _, path = exports.compile_object(gate, compiler, output, "records", positive_source())
    check(exports, path)
    report["records"] = {"bytes": path.stat().st_size}
    for name, source in CASES_7102.items():
        report[name] = refused(gate, exports, compiler, output, name, source, "E7102")
    for name, source in CASES_7106.items():
        report[name] = refused(gate, exports, compiler, output, name, source, "E7106")
    (output / "image.kotoba").write_text("(ns i (:export [main]))\n(defn- record-load-u32-0-40 [b :i64] :i64 0)\n"
                                         "(defn main [] :i64 0)\n")
    result = gate.native_run(compiler, output, "compile", "image.kotoba", "--target", "x86_64-aiueos-kernel-v1",
                             "--artifact", "image", "--output", "image.elf", "--fuel", "1024", expected=1)
    if (output / "image.elf").exists() or "E7102" not in (result.stdout + result.stderr).decode(errors="replace"):
        raise ValueError("a record declaration on the image route was not refused with E7102")
    report["image"] = "refused E7102"
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS_AIUEOS_OBJECT_RECORDS " + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
