#!/usr/bin/env python3
"""The aiueos kernel object route's CPU feature reads (JUN-633).

kernel-cpuid-<eax|ebx|ecx|edx> [leaf subleaf], kernel-rdtsc [] and kernel-rdrand [] are ids 18..23 of
seed/74-x86_64-aiueos-object.kotoba, named and encoded as seed/86's kernel runtime has them (km-cpu, km-entropy), with
lfence before rdtsc. Compiles with a native Amu compiler and checks the emitted bytes (Python stages and observes; it
emits nothing):

* six: one object exporting the six, each body carrying exactly its sequence --
    cpuid:  mov rax,[leaf]; mov rcx,[subleaf]; push rbx; cpuid; [mov eax,ebx|ecx|edx]; pop rbx
    rdtsc:  lfence; rdtsc; shl rdx,32; or rax,rdx
    rdrand: mov ecx,10; L: rdrand rax; jc +6; dec ecx; jnz L; xor eax,eax
* unchanged: the 512-byte width object of check-aiueos-object-windows.py's source keeps its pinned SHA-256, so no
  object that does not name a CPU stub changes;
* refused, nothing written: a CPU read used as a window base (E7106, it is not a rooted region), and a call with the
  wrong arity.

Not shown here: execution. docs/evidence/cpu-intrinsics-20261030/ runs the six-object under QEMU against inline-asm C.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

MAC_GATE = Path(__file__).with_name("check-aiueos-user-macos-native.py")
WINDOWS16 = Path(__file__).with_name("check-aiueos-object-windows16.py")
FUEL = "1024"
SOURCE = """(ns cpu (:export [ca cb cc cd ts rr]))
(defn ca [l :i64 s :i64] :i64 (kernel-cpuid-eax l s))
(defn cb [l :i64 s :i64] :i64 (kernel-cpuid-ebx l s))
(defn cc [l :i64 s :i64] :i64 (kernel-cpuid-ecx l s))
(defn cd [l :i64 s :i64] :i64 (kernel-cpuid-edx l s))
(defn ts [] :i64 (kernel-rdtsc))
(defn rr [] :i64 (kernel-rdrand))
"""
CPUID_CORE = "53" + "0fa2"
CPUID_MOVE = {"eax": "", "ebx": "89d8", "ecx": "89c8", "edx": "89d0"}
RDTSC = "0faee8" + "0f31" + "48c1e220" + "4809d0"
RDRAND = "b90a000000" + "480fc7f0" + "7206" + "ffc9" + "75f6" + "31c0"
REFUSALS = {
    "cpu-as-base": ("(ns refused (:export [f]))\n(defn f [n :i64 i :i64] :i64 (kernel-load-u8 (kernel-rdtsc) n i))\n", "E7106"),
    "arity": ("(ns refused (:export [f]))\n(defn f [l :i64] :i64 (kernel-cpuid-eax l))\n", None),
}


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(compiler, output):
    gate = load(MAC_GATE, "mac_native_gate")
    windows16 = load(WINDOWS16, "windows16_gate")
    gate.verify_macho(compiler)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    report = {}

    _, obj = windows16.compile_source(gate, compiler, output, "cpu", SOURCE)
    text = windows16.text_section(obj).hex()
    found = {}
    for reg, move in CPUID_MOVE.items():
        # the leaf and subleaf come from their frame slots: mov rax,[rbp+d]; mov rcx,[rbp+d]; then the core
        sequence = CPUID_CORE + move + "5b"
        count = text.count(sequence) if move else text.count(CPUID_CORE + "5b")
        found["cpuid-" + reg] = count
    found["rdtsc"] = text.count(RDTSC)
    found["rdrand"] = text.count(RDRAND)
    if found != {"cpuid-eax": 1, "cpuid-ebx": 1, "cpuid-ecx": 1, "cpuid-edx": 1, "rdtsc": 1, "rdrand": 1}:
        raise ValueError(f"CPU sequences {found}; want each exactly once")
    if text.count("0fa2") != 4 or text.count("0f31") != 1 or text.count("0fc7f0") != 1:
        raise ValueError("a CPU instruction appears outside its sequence")
    report["six"] = {"sequences": found, "sha256": hashlib.sha256(obj.read_bytes()).hexdigest()}

    _, obj = windows16.compile_source(gate, compiler, output, "widths", windows16.WIDTHS_SOURCE)
    digest = hashlib.sha256(obj.read_bytes()).hexdigest()
    if digest != windows16.WIDTHS_SHA256:
        raise ValueError(f"the 512-byte width object changed: {digest}")
    report["widthsUnchanged"] = digest

    for name, (source, code) in REFUSALS.items():
        result, obj = windows16.compile_source(gate, compiler, output, name, source, expected=1)
        message = (result.stdout + result.stderr).decode(errors="replace")
        if obj.exists() or (code and code not in message):
            raise ValueError(f"{name} was not refused{' with ' + code if code else ''} and no output: {message}")
        report[name] = "refused " + (code or message.strip().split(";")[0][:60])
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS_AIUEOS_OBJECT_CPU " + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
