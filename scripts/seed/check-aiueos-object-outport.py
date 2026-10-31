#!/usr/bin/env python3
"""The aiueos kernel object route's literal-bounded output ports (JUN-600, ADR 0400).

kernel-out-u8 [port value] and kernel-out-u32 [port value] are ids 4 and 5 of seed/74-x86_64-aiueos-object.kotoba. The
port must be an integer LITERAL in its width's closed list (E7107), as kernel-in-u32's is (ADR 0399):
  out-u8:  0x20, 0x21 (master 8259), 0xa0, 0xa1 (slave 8259), 0x80 (the io_wait delay)   -- pic-disable
  out-u32: 0xcf8, 0xcfc (PCI configuration address and data)                              -- pci-config-read / -write
The value stays a run-time operand. Compiles with a native Amu compiler and checks (Python stages and observes; it
emits nothing):

* sequences: one object writing every listed port, the values literal, a parameter and computed, in the shapes the
  kernel's pic-disable, pci-config-read and pci-config-write objects use, carries
    out-u8:  mov rdx,[port]; mov rax,[value]; out dx,al    seven times
    out-u32: mov rdx,[port]; mov rax,[value]; out dx,eax   three times
  and its bytes are those main's root (amu fe7b5b1c) emitted for the same source: the rule changes no admitted object;
* the plain image artifact (--artifact image) shares the check: a listed port compiles, an unlisted one is refused;
* refused, nothing written, for each width: an unlisted literal (out-u8: 0x3f8 COM1, 0xe9 the debug console, 0x22,
  0xcf9 reset control; out-u32: 0xcfd, 0xcf9, 0xf4 the QEMU exit port), the other width's port (out-u8 0xcf8, out-u32
  0x20), a parameter port, a computed port, a let-bound literal, a port selected by a branch (E7107); each with the
  wrong number of arguments (E2103).

Not shown here: execution. The bytes are main's, so the QEMU port traces of the kernel objects that use these stubs are
unchanged; kotoba's port-trace differentials cover them.
"""

import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path

MAC_GATE = Path(__file__).with_name("check-aiueos-user-macos-native.py")
WINDOWS16 = Path(__file__).with_name("check-aiueos-object-windows16.py")
U8_PORTS = (32, 33, 128, 160, 161)
U32_PORTS = (3320, 3324)
# every listed port, with literal, parameter and computed values, as pic-disable / pci-config-read / pci-config-write
SOURCE = ("(ns outport (:export [pic pcw pcr]))\n"
          "(defn pic [m :i64 s :i64] :i64\n"
          "  (if (and (>= m 32) (>= s 32))\n"
          "    (let [c1 (kernel-out-u8 32 17) d1 (kernel-out-u8 128 0) c2 (kernel-out-u8 160 17)\n"
          "          c3 (kernel-out-u8 33 m) c4 (kernel-out-u8 161 s) c9 (kernel-out-u8 33 255) c10 (kernel-out-u8 161 255)]\n"
          "      1)\n"
          "    0))\n"
          "(defn pcw [a :i64 v :i64] :i64\n"
          "  (let [x (kernel-out-u32 3320 (bit-or 2147483648 (bit-and a 252))) y (kernel-out-u32 3324 v)] 1))\n"
          "(defn pcr [a :i64] :i64 (let [x (kernel-out-u32 3320 (bit-or 2147483648 a))] (kernel-in-u32 3324)))\n")
# SOURCE compiled by main's root (seed/bootstrap/aarch64-macos/amu-full-root.macho at amu fe7b5b1c), before this rule
SOURCE_SHA256 = "6377fce8f681ff0c760798f8fb41281e247f5b8627000ba5348c24464b1fd0d7"
OUT8, OUT32 = rb"\x48\x8b\x95.{4}\x48\x8b\x85.{4}\xee", rb"\x48\x8b\x95.{4}\x48\x8b\x85.{4}\xef"
IMAGE_OK = "(ns i (:export [main]))\n(defn main [] :i64 (let [x (kernel-out-u8 128 0)] 42))\n"
IMAGE_BAD = "(ns i (:export [main]))\n(defn main [] :i64 (let [x (kernel-out-u8 1016 65)] 42))\n"


def one(form, params=""):
    return f"(ns r (:export [f]))\n(defn f [{params}] :i64 {form})\n"


REFUSALS = {
    "u8-com1": (one("(kernel-out-u8 1016 65)"), "E7107"),
    "u8-debugcon": (one("(kernel-out-u8 233 65)"), "E7107"),
    "u8-elcr-neighbour": (one("(kernel-out-u8 34 0)"), "E7107"),
    "u8-reset": (one("(kernel-out-u8 3321 6)"), "E7107"),
    "u8-u32-port": (one("(kernel-out-u8 3320 0)"), "E7107"),
    "u8-parameter": (one("(kernel-out-u8 p 0)", "p :i64"), "E7107"),
    "u8-computed": (one("(kernel-out-u8 (bit-or p 32) 0)", "p :i64"), "E7107"),
    "u8-let-bound": (one("(let [p 32] (kernel-out-u8 p 0))"), "E7107"),
    "u8-branch": (one("(kernel-out-u8 (if (= s 0) 32 160) 0)", "s :i64"), "E7107"),
    "u32-cfd": (one("(kernel-out-u32 3325 0)"), "E7107"),
    "u32-reset": (one("(kernel-out-u32 3321 6)"), "E7107"),
    "u32-qemu-exit": (one("(kernel-out-u32 244 16)"), "E7107"),
    "u32-u8-port": (one("(kernel-out-u32 32 0)"), "E7107"),
    "u32-parameter": (one("(kernel-out-u32 p 0)", "p :i64"), "E7107"),
    "u32-computed": (one("(kernel-out-u32 (+ p 3320) 0)", "p :i64"), "E7107"),
    "u32-let-bound": (one("(let [p 3320] (kernel-out-u32 p 0))"), "E7107"),
    "u32-branch": (one("(kernel-out-u32 (if (= s 0) 3320 3324) 0)", "s :i64"), "E7107"),
    "u8-one": (one("(kernel-out-u8 32)"), "E2103"),
    "u8-three": (one("(kernel-out-u8 32 0 0)"), "E2103"),
    "u32-one": (one("(kernel-out-u32 3320)"), "E2103"),
    "u32-three": (one("(kernel-out-u32 3320 0 0)"), "E2103"),
}


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def image(gate, compiler, output, name, source, expected):
    (output / f"{name}.kotoba").write_text(source)
    result = gate.native_run(compiler, output, "compile", f"{name}.kotoba", "--target", "x86_64-aiueos-kernel-v1",
                             "--artifact", "image", "--output", f"{name}.elf", "--fuel", "1000000", expected=expected)
    return result, output / f"{name}.elf"


def main(compiler, output):
    gate = load(MAC_GATE, "mac_native_gate")
    windows16 = load(WINDOWS16, "windows16_gate")
    gate.verify_macho(compiler)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    report = {}

    _, obj = windows16.compile_source(gate, compiler, output, "outport", SOURCE)
    text = windows16.text_section(obj)
    found = {"out-u8": len(re.findall(OUT8, text, re.DOTALL)), "out-u32": len(re.findall(OUT32, text, re.DOTALL))}
    want = {"out-u8": 7, "out-u32": 3}
    if found != want:
        raise ValueError(f"output-port sequences {found}, want {want}")
    digest = hashlib.sha256(obj.read_bytes()).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError(f"the admitted output-port object changed: {digest}, main's root gave {SOURCE_SHA256}")
    report["sequences"] = {"found": found, "sha256": digest}

    _, elf = image(gate, compiler, output, "image-ok", IMAGE_OK, 0)
    if not elf.exists():
        raise ValueError("the image artifact with a listed port was not written")
    result, elf = image(gate, compiler, output, "image-bad", IMAGE_BAD, 1)
    message = (result.stdout + result.stderr).decode(errors="replace")
    if "E7107" not in message or elf.exists():
        raise ValueError(f"the image artifact with port 0x3f8 was not refused with E7107: {message}")
    report["image"] = {"listed": "compiled", "unlisted": "refused E7107"}

    for name, (source, code) in REFUSALS.items():
        result, obj = windows16.compile_source(gate, compiler, output, name, source, expected=1)
        message = (result.stdout + result.stderr).decode(errors="replace")
        if code not in message or obj.exists():
            raise ValueError(f"{name} was not refused with {code} and no output: {message}")
        report[name] = f"refused {code}"
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS_AIUEOS_OBJECT_OUTPORT " + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
