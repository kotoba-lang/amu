#!/usr/bin/env python3
"""Native f32 / f64 on the aiueos kernel object route (JUN-633 slice 3, ADR 0391).

seed/70-x86_64-linux.kotoba emits scalar SSE for the float SIR codes and seed/74's xo-check-sir admits them on the
object artifact only. A float is its bit pattern in an i64 slot (an f32 sign-extended from 32 bits). Compiles with a
native Amu compiler and checks (Python stages and observes; it emits nothing):

* fops: one object exporting every admitted operation behind an op selector (the source of
  docs/evidence/f32-sse-20261030/fops.kotoba), whose text carries each operation's instruction exactly once
  (addss subss mulss divss and the sd forms, sqrtss / sqrtsd, cvtsi2ss / cvtsi2sd, cvtsd2ss / cvtss2sd, six
  ucomiss and six ucomisd, two setnp for the two eq, btc / btr rax,63 for f64 neg / abs) and no minss / maxss /
  cvttss2si / cvttsd2si;
* trap: f32-from-bits is this route's definition, an out-of-range pattern reaching ud2 rather than a vector access;
* unchanged: the 512-byte width object keeps its pinned SHA-256 (an integer object's bytes do not move);
* refused, nothing written: f32-min / f64-max and f64 -> i64 truncation (E7101), and an export whose parameter or
  result is a float (System V would pass it in an xmm register): E7102, or the shared check stage's E2104 before it.
  f32 -> i64 truncation is admitted since slice 7 (ADR 0395); check-aiueos-object-f2i.py covers it.

Not shown here: execution. docs/evidence/f32-sse-20261030/ runs fops under QEMU against the same operations in C.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

MAC_GATE = Path(__file__).with_name("check-aiueos-user-macos-native.py")
WINDOWS16 = Path(__file__).with_name("check-aiueos-object-windows16.py")
FOPS = Path(__file__).resolve().parents[2] / "docs/evidence/f32-sse-20261030/fops.kotoba"
EXPECTED = {
    "addss": ("f30f5885", 1), "subss": ("f30f5c85", 1), "mulss": ("f30f5985", 1), "divss": ("f30f5e85", 1),
    "addsd": ("f20f5885", 1), "subsd": ("f20f5c85", 1), "mulsd": ("f20f5985", 1), "divsd": ("f20f5e85", 1),
    "sqrtss": ("f30f5185", 1), "sqrtsd": ("f20f5185", 1),
    "cvtsi2ss": ("f3480f2a85", 1), "cvtsi2sd": ("f2480f2a85", 1), "cvtsd2ss": ("f20f5a85", 1), "cvtss2sd": ("f30f5a85", 1),
    "ucomisd": ("660f2e85", 6), "setnp-cl": ("0f9bc1", 2),
    "btc-rax-63": ("480fbaf83f", 1), "btr-rax-63": ("480fbaf03f", 1),
    "minss": ("f30f5d", 0), "maxss": ("f30f5f", 0), "minsd": ("f20f5d", 0), "maxsd": ("f20f5f", 0),
    "cvttss2si": ("f3480f2c", 0), "cvttsd2si": ("f2480f2c", 0),
}
TRAP = """(ns t (:export [kotoba_aiueos_t]))
(defn kotoba_aiueos_t [x :i64] :i64 (f32-to-bits (f32-from-bits x)))
"""
REFUSALS = {
    "f32-min": ("(ns r (:export [f]))\n(defn f [x :i64] :i64 (f32-to-bits (f32-min (f32-from-bits x) (f32-from-bits x))))\n", "E7101"),
    "f64-max": ("(ns r (:export [f]))\n(defn f [x :i64] :i64 (f64-to-bits (f64-max (f64-from-bits x) (f64-from-bits x))))\n", "E7101"),
    "f64-to-i64": ("(ns r (:export [f]))\n(defn f [x :i64] :i64 (f64-to-i64-truncating (f64-from-bits x)))\n", "E7101"),
    "export-f32-param": ("(ns r (:export [f]))\n(defn f [x :f32] :i64 (f32-to-bits x))\n", ("E7102", "E2104")),
    "export-f64-result": ("(ns r (:export [f]))\n(defn f [x :i64] :f64 (f64-from-bits x))\n", ("E7102", "E2104")),
}


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(compiler, output):
    gate = load(MAC_GATE, "mac_native_gate")
    windows16 = load(WINDOWS16, "windows16_gate")
    gate.verify_macho(compiler)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    report = {}

    _, obj = windows16.compile_source(gate, compiler, output, "fops", FOPS.read_text())
    text = windows16.text_section(obj)
    found = {name: text.count(bytes.fromhex(seq)) for name, (seq, _) in EXPECTED.items()}
    found["ucomiss"] = text.count(bytes.fromhex("0f2e85")) - found["ucomisd"]
    want = {name: n for name, (_, n) in EXPECTED.items()} | {"ucomiss": 6}
    if found != want:
        raise ValueError(f"float sequences {found}")
    report["fops"] = {"sequences": found, "sha256": hashlib.sha256(obj.read_bytes()).hexdigest()}

    _, obj = windows16.compile_source(gate, compiler, output, "trap", TRAP)
    text = windows16.text_section(obj)
    # the range check: cmp against INT32_MIN / INT32_MAX feeding (assert ...)'s ud2, and no runtime vector call
    if text.count(bytes.fromhex("0f0b")) < 2 or bytes.fromhex("ffffff7f") not in text:
        raise ValueError("f32-from-bits carries no range trap")
    report["trap"] = hashlib.sha256(obj.read_bytes()).hexdigest()

    _, obj = windows16.compile_source(gate, compiler, output, "widths", windows16.WIDTHS_SOURCE)
    digest = hashlib.sha256(obj.read_bytes()).hexdigest()
    if digest != windows16.WIDTHS_SHA256:
        raise ValueError(f"the 512-byte width object changed: {digest}")
    report["widthsUnchanged"] = digest

    for name, (source, codes) in REFUSALS.items():
        codes = (codes,) if isinstance(codes, str) else codes
        result, obj = windows16.compile_source(gate, compiler, output, name, source, expected=1)
        message = (result.stdout + result.stderr).decode(errors="replace")
        hit = [code for code in codes if code in message]
        if not hit or obj.exists():
            raise ValueError(f"{name} was not refused with {codes} and no output: {message}")
        report[name] = "refused " + hit[0]
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS_AIUEOS_OBJECT_F32 " + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
