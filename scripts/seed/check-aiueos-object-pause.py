#!/usr/bin/env python3
"""The aiueos kernel object route's spin-wait hint (JUN-633 slice 5, ADR 0393).

kernel-pause [] is id 29 of seed/74-x86_64-aiueos-object.kotoba: pause, returning 0. Compiles with a native Amu compiler
and checks (Python stages and observes; it emits nothing):

* pause: an object exporting one pause carries exactly pause; xor eax,eax once;
* opt-in: the wait object of check-aiueos-object-halt.py, which does not name the stub, carries no pause and keeps the
  bytes it had before this block existed;
* unchanged: the 512-byte width object keeps its pinned SHA-256;
* refused, nothing written: the stub called with an argument.

Not shown here: execution. docs/evidence/pause-intrinsic-20261031/ runs the pause under QEMU.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

MAC_GATE = Path(__file__).with_name("check-aiueos-user-macos-native.py")
WINDOWS16 = Path(__file__).with_name("check-aiueos-object-windows16.py")
HALT = Path(__file__).with_name("check-aiueos-object-halt.py")
# the wait object's SHA-256 under slice 4 (amu 0de77b5e): the pause block must leave it as it was
HALT_WAIT_SHA256 = "83d8375aba61aab71cde8cc6625ba41d43c566c5281de7caf4c9c7a6c25414f7"
SOURCE = """(ns ps (:export [kotoba_aiueos_spin]))
(defn kotoba_aiueos_spin [] :i64 (kernel-pause))
"""
PAUSE = "f390" + "31c0"
REFUSALS = {
    "argument": "(ns r (:export [f]))\n(defn f [] :i64 (kernel-pause 1))\n",
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

    _, obj = windows16.compile_source(gate, compiler, output, "pause", SOURCE)
    text = windows16.text_section(obj)
    found = {"pause": text.hex().count(PAUSE), "f390": text.count(b"\xf3\x90")}
    if found != {"pause": 1, "f390": 1}:
        raise ValueError(f"pause sequence {found}")
    report["pause"] = {"sequence": found, "sha256": hashlib.sha256(obj.read_bytes()).hexdigest()}

    halt = load(HALT, "halt_gate")
    _, obj = windows16.compile_source(gate, compiler, output, "wait", halt.SOURCE)
    digest = hashlib.sha256(obj.read_bytes()).hexdigest()
    if bytes.fromhex("f390") in windows16.text_section(obj) or digest != HALT_WAIT_SHA256:
        raise ValueError(f"the wait object changed or carries a pause: {digest}")
    report["optIn"] = digest

    _, obj = windows16.compile_source(gate, compiler, output, "widths", windows16.WIDTHS_SOURCE)
    digest = hashlib.sha256(obj.read_bytes()).hexdigest()
    if digest != windows16.WIDTHS_SHA256:
        raise ValueError(f"the 512-byte width object changed: {digest}")
    report["widthsUnchanged"] = digest

    for name, source in REFUSALS.items():
        result, obj = windows16.compile_source(gate, compiler, output, name, source, expected=1)
        message = (result.stdout + result.stderr).decode(errors="replace")
        if "E2103" not in message or obj.exists():
            raise ValueError(f"{name} was not refused with E2103 and no output: {message}")
        report[name] = "refused E2103"
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS_AIUEOS_OBJECT_PAUSE " + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
