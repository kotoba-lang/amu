#!/usr/bin/env python3
"""The aiueos kernel object route's extended-state setup (JUN-633 slice 2, ADR 0390).

kernel-cr4-set-bits [mask], kernel-xcr0-set-bits [mask], kernel-read-cr4 [] and kernel-xgetbv [] are ids 24..27 of
seed/74-x86_64-aiueos-object.kotoba. The two writes OR a LITERAL mask into the register; the verifier admits only
CR4 OSFXSR / OSXMMEXCPT / OSXSAVE (0x40600) and XCR0 x87 / SSE / AVX (0x7). Compiles with a native Amu compiler and checks
(Python stages and observes; it emits nothing):

* four: one object exporting the four, each body carrying exactly its sequence --
    cr4-set-bits:  mov rcx,[mask]; mov rax,cr4; or rax,rcx; mov cr4,rax
    xcr0-set-bits: mov rsi,[mask]; xor ecx,ecx; xgetbv; or rax,rsi; xsetbv; shl rdx,32; or rax,rdx
    read-cr4:      mov rax,cr4
    xgetbv:        xor ecx,ecx; xgetbv; shl rdx,32; or rax,rdx
* unchanged: the 512-byte width object keeps its pinned SHA-256;
* refused E7107, nothing written: a CR4 bit outside the set (PGE), an XCR0 bit outside it (bit 3), a mask that is a
  parameter rather than a literal, and a zero mask.

Not shown here: execution. docs/evidence/xstate-intrinsics-20261030/ runs the four under QEMU against inline-asm C.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

MAC_GATE = Path(__file__).with_name("check-aiueos-user-macos-native.py")
WINDOWS16 = Path(__file__).with_name("check-aiueos-object-windows16.py")
SOURCE = """(ns xs (:export [cr4on xcr0on rc xg]))
(defn cr4on [] :i64 (kernel-cr4-set-bits 263680))
(defn xcr0on [] :i64 (kernel-xcr0-set-bits 7))
(defn rc [] :i64 (kernel-read-cr4))
(defn xg [] :i64 (kernel-xgetbv))
"""
CR4_SET = "0f20e0" + "4809c8" + "0f22e0"
XCR0_SET = "31c9" + "0f01d0" + "4809f0" + "0f01d1" + "48c1e220" + "4809d0"
XGETBV = "31c9" + "0f01d0" + "48c1e220" + "4809d0"
REFUSALS = {
    "cr4-pge": "(ns r (:export [f]))\n(defn f [] :i64 (kernel-cr4-set-bits 128))\n",
    "xcr0-bit3": "(ns r (:export [f]))\n(defn f [] :i64 (kernel-xcr0-set-bits 8))\n",
    "mask-parameter": "(ns r (:export [f]))\n(defn f [m :i64] :i64 (kernel-cr4-set-bits m))\n",
    "mask-zero": "(ns r (:export [f]))\n(defn f [] :i64 (kernel-xcr0-set-bits 0))\n",
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

    _, obj = windows16.compile_source(gate, compiler, output, "xstate", SOURCE)
    text = windows16.text_section(obj).hex()
    found = {"cr4-set-bits": text.count(CR4_SET), "xcr0-set-bits": text.count(XCR0_SET),
             "xgetbv": text.count(XGETBV), "mov-from-cr4": text.count("0f20e0"), "mov-to-cr4": text.count("0f22e0"),
             "xsetbv": text.count("0f01d1")}
    if found != {"cr4-set-bits": 1, "xcr0-set-bits": 1, "xgetbv": 1, "mov-from-cr4": 2, "mov-to-cr4": 1, "xsetbv": 1}:
        raise ValueError(f"extended-state sequences {found}")
    report["four"] = {"sequences": found, "sha256": hashlib.sha256(obj.read_bytes()).hexdigest()}

    _, obj = windows16.compile_source(gate, compiler, output, "widths", windows16.WIDTHS_SOURCE)
    digest = hashlib.sha256(obj.read_bytes()).hexdigest()
    if digest != windows16.WIDTHS_SHA256:
        raise ValueError(f"the 512-byte width object changed: {digest}")
    report["widthsUnchanged"] = digest

    for name, source in REFUSALS.items():
        result, obj = windows16.compile_source(gate, compiler, output, name, source, expected=1)
        message = (result.stdout + result.stderr).decode(errors="replace")
        if "E7107" not in message or obj.exists():
            raise ValueError(f"{name} was not refused with E7107 and no output: {message}")
        report[name] = "refused E7107"
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS_AIUEOS_OBJECT_XSTATE " + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
