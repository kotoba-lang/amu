#!/usr/bin/env python3
"""The aiueos kernel object route's bounded MSR and port-input accesses (JUN-600, ADR 0399).

kernel-read-msr [index], kernel-write-msr [index value] and kernel-in-u32 [port] are ids 32, 33 and 34 of
seed/74-x86_64-aiueos-object.kotoba, each a block of its own. The index and the port must be integer LITERALS in closed
lists (E7107): MSRs 0x1b IA32_APIC_BASE, 0xc0000080 IA32_EFER, 0xc0000081 IA32_STAR, 0xc0000082 IA32_LSTAR and
0xc0000084 IA32_FMASK; port 0xcfc. A write of APIC_BASE may only set bit 11 and a write of EFER only bits 0 and 11 of the
current value (a run-time bound, ud2 otherwise). Compiles with a native Amu compiler and checks (Python stages and
observes; it emits nothing):

* sequences: one object exporting an MSR read and an MSR write, each selecting one of the five literal indices by the
  run-time index (as the kernel's msr-read / msr-write objects do), and a PCI configuration read carries
    read-msr:  mov rcx,[index]; rdmsr; shl rdx,32; or rax,rdx                                   five times
    write-msr: mov rcx,[index]; mov rsi,[value]; the APIC_BASE / EFER bound (cmp ecx,0x1b ... ud2); wrmsr   five times
    in-u32:    mov rdx,[port]; in eax,dx                                                            once
  and no other rdmsr, wrmsr or in;
* opt-in: the fused-reduction gate's dot object, which names none of the three, keeps the bytes it had before the blocks
  existed, and the 512-byte width object keeps its pinned SHA-256;
* refused, nothing written: an index outside the list (IA32_CSTAR 0xc0000083, between two admitted ones; IA32_TSC 0x10;
  IA32_PAT 0x277 for a write), an index that is a parameter or computed, a port outside the list (0xcf8, 0xcfd) or a
  parameter port (E7107); each with the wrong number of arguments (E2103).

Not shown here: execution. docs/evidence/msr-in-intrinsics-20261031/ runs the object under QEMU against inline-asm C.
"""

import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path

MAC_GATE = Path(__file__).with_name("check-aiueos-user-macos-native.py")
WINDOWS16 = Path(__file__).with_name("check-aiueos-object-windows16.py")
FUSED = Path(__file__).with_name("check-aiueos-object-fused-dot.py")
# the fused-reduction gate's dot object under amu c2c9dfbe (main before these blocks): it must keep its bytes
DOT_SHA256 = "30261e7d172802a0561c3c7053655a80faadbfc174cc5a121dcd75d5736f4706"
MSRS = {"apic": 27, "efer": 3221225600, "star": 3221225601, "lstar": 3221225602, "fmask": 3221225604}
# kotoba_aiueos_msr_read / _write select one of the five literal indices by the run-time index, as the kernel's objects do
SOURCE = ("(ns msr (:export [kotoba_aiueos_msr_read kotoba_aiueos_msr_write pcr]))\n"
          "(defn kotoba_aiueos_msr_read [i :i64] :i64\n  (cond "
          + " ".join(f"(= i {v}) (kernel-read-msr {v})" for v in MSRS.values()) + " :else 0))\n"
          "(defn kotoba_aiueos_msr_write [i :i64 v :i64] :i64\n  (cond "
          + " ".join(f"(= i {v}) (kernel-write-msr {v} v)" for v in MSRS.values()) + " :else 0))\n"
          "(defn pcr [a :i64] :i64 (let [x (kernel-out-u32 3320 a)] (kernel-in-u32 3324)))\n")
READ = "0f32" + "48c1e220" + "4809d0"
WRITE = ("83f91b" + "7410" + "81f9800000c0" + "7522" + "41b801080000" + "eb06" + "41b800080000"
         + "0f32" + "48c1e220" + "4809d0" + "4921f0" + "4909c0" + "4939f0" + "750e"
         + "4889f0" + "4889f2" + "48c1ea20" + "0f30" + "eb02" + "0f0b")
REFUSALS = {
    "read-cstar": ("(ns r (:export [f]))\n(defn f [] :i64 (kernel-read-msr 3221225603))\n", "E7107"),
    "read-tsc": ("(ns r (:export [f]))\n(defn f [] :i64 (kernel-read-msr 16))\n", "E7107"),
    "read-parameter": ("(ns r (:export [f]))\n(defn f [i :i64] :i64 (kernel-read-msr i))\n", "E7107"),
    "read-computed": ("(ns r (:export [f]))\n(defn f [i :i64] :i64 (kernel-read-msr (bit-or i 27)))\n", "E7107"),
    "write-cstar": ("(ns r (:export [f]))\n(defn f [v :i64] :i64 (kernel-write-msr 3221225603 v))\n", "E7107"),
    "write-pat": ("(ns r (:export [f]))\n(defn f [v :i64] :i64 (kernel-write-msr 631 v))\n", "E7107"),
    "write-parameter": ("(ns r (:export [f]))\n(defn f [i :i64 v :i64] :i64 (kernel-write-msr i v))\n", "E7107"),
    "in-index-port": ("(ns r (:export [f]))\n(defn f [] :i64 (kernel-in-u32 3320))\n", "E7107"),
    "in-cfd": ("(ns r (:export [f]))\n(defn f [] :i64 (kernel-in-u32 3325))\n", "E7107"),
    "in-parameter": ("(ns r (:export [f]))\n(defn f [p :i64] :i64 (kernel-in-u32 p))\n", "E7107"),
    "read-two": ("(ns r (:export [f]))\n(defn f [] :i64 (kernel-read-msr 27 0))\n", "E2103"),
    "write-one": ("(ns r (:export [f]))\n(defn f [] :i64 (kernel-write-msr 27))\n", "E2103"),
    "in-none": ("(ns r (:export [f]))\n(defn f [] :i64 (kernel-in-u32))\n", "E2103"),
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

    _, obj = windows16.compile_source(gate, compiler, output, "msr", SOURCE)
    text = windows16.text_section(obj)
    seq = lambda pattern: len(re.findall(pattern, text, re.DOTALL))
    found = {"read-msr": seq(b"\x48\x8b\x8d.{4}" + bytes.fromhex(READ)),
             "write-msr": seq(b"\x48\x8b\x8d.{4}\x48\x8b\xb5.{4}" + bytes.fromhex(WRITE)),
             "in-u32": seq(b"\x48\x8b\x95.{4}\xed"), "rdmsr": text.count(b"\x0f\x32"),
             "wrmsr": text.count(b"\x0f\x30"), "in": text.count(b"\xed")}
    want = {"read-msr": 5, "write-msr": 5, "in-u32": 1, "rdmsr": 10, "wrmsr": 5, "in": 1}
    if found != want:
        raise ValueError(f"MSR / port-input sequences {found}, want {want}")
    report["sequences"] = {"found": found, "sha256": hashlib.sha256(obj.read_bytes()).hexdigest()}

    fused = load(FUSED, "fused_gate")
    _, obj = windows16.compile_source(gate, compiler, output, "dot", fused.DOT)
    digest = hashlib.sha256(obj.read_bytes()).hexdigest()
    if digest != DOT_SHA256:
        raise ValueError(f"the fused-reduction dot object changed: {digest}")
    report["optIn"] = digest

    _, obj = windows16.compile_source(gate, compiler, output, "widths", windows16.WIDTHS_SOURCE)
    digest = hashlib.sha256(obj.read_bytes()).hexdigest()
    if digest != windows16.WIDTHS_SHA256:
        raise ValueError(f"the 512-byte width object changed: {digest}")
    report["widthsUnchanged"] = digest

    for name, (source, code) in REFUSALS.items():
        result, obj = windows16.compile_source(gate, compiler, output, name, source, expected=1)
        message = (result.stdout + result.stderr).decode(errors="replace")
        if code not in message or obj.exists():
            raise ValueError(f"{name} was not refused with {code} and no output: {message}")
        report[name] = f"refused {code}"
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS_AIUEOS_OBJECT_MSR " + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
