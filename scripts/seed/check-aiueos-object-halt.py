#!/usr/bin/env python3
"""The aiueos kernel object route's halt-until-interrupt (JUN-633 slice 4, ADR 0392).

kernel-wait-interrupt [] is id 28 of seed/74-x86_64-aiueos-object.kotoba: sti; hlt; cli, returning 0. Compiles with a
native Amu compiler and checks (Python stages and observes; it emits nothing):

* wait: an object exporting one wait carries exactly sti; hlt; cli; xor eax,eax once, and no other sti / hlt / cli;
* opt-in: an object that does not name the stub (the extended-state source of check-aiueos-object-xstate.py) carries no
  sti, hlt or cli at all;
* unchanged: the 512-byte width object keeps its pinned SHA-256;
* refused, nothing written: the stub called with an argument.

Not shown here: execution. docs/evidence/halt-intrinsic-20261031/ runs the wait under a 100 Hz PIT interrupt in QEMU.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

MAC_GATE = Path(__file__).with_name("check-aiueos-user-macos-native.py")
WINDOWS16 = Path(__file__).with_name("check-aiueos-object-windows16.py")
XSTATE = Path(__file__).with_name("check-aiueos-object-xstate.py")
SOURCE = """(ns hw (:export [kotoba_aiueos_wait]))
(defn kotoba_aiueos_wait [] :i64 (kernel-wait-interrupt))
"""
WAIT = "fb" + "f4" + "fa" + "31c0"
REFUSALS = {
    "argument": "(ns r (:export [f]))\n(defn f [] :i64 (kernel-wait-interrupt 1))\n",
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

    _, obj = windows16.compile_source(gate, compiler, output, "wait", SOURCE)
    text = windows16.text_section(obj)
    found = {"wait": text.hex().count(WAIT), "sti": text.count(b"\xfb"), "hlt": text.count(b"\xf4"), "cli": text.count(b"\xfa")}
    if found["wait"] != 1 or bytes.fromhex(WAIT) not in text:
        raise ValueError(f"wait sequence {found}")
    report["wait"] = {"sequence": found, "sha256": hashlib.sha256(obj.read_bytes()).hexdigest()}

    xstate = load(XSTATE, "xstate_gate")
    _, obj = windows16.compile_source(gate, compiler, output, "no-wait", xstate.SOURCE)
    if bytes.fromhex("fbf4fa") in windows16.text_section(obj):
        raise ValueError("an object that names no wait carries the halt sequence")
    report["optIn"] = hashlib.sha256(obj.read_bytes()).hexdigest()

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
    print("PASS_AIUEOS_OBJECT_HALT " + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
