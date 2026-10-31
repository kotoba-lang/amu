#!/usr/bin/env python3
"""The aiueos kernel object route's fused f32 reductions (JUN-633 slice 6, ADR 0394).

kernel-dot-f32 [a a-len b b-len count] and kernel-dequant-dot-ptq1-0 [weights w-len input i-len blocks] are ids 30 and
31 of seed/74-x86_64-aiueos-object.kotoba. Compiles with a native Amu compiler and checks (Python stages and observes;
it emits nothing):

* each object carries its guards (both lengths against 0x10000, the count against 0x4000 / the blocks against 0x80),
  the cpuid / xgetbv arm choice once, both arms (AVX2: vhaddps x2 and vzeroupper; scalar: the (l0+l1)+(l2+l3)
  reduction once) and, for PTQ1_0, sixteen eight-lane groups in the AVX2 arm;
* opt-in: the pause gate's object, which does not name the block, keeps the bytes it had before the block existed,
  and the 512-byte width object keeps its pinned SHA-256;
* refused, nothing written: either builtin called with four or six arguments (E2103), and a window whose length is
  computed rather than its owner's length parameter (E7106) -- the rooted-base rule holds for both windows.

Not shown here: execution. docs/evidence/fused-dot-20261031/ runs both objects under QEMU against the
kotoba-compiler/1 object they replace.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

MAC_GATE = Path(__file__).with_name("check-aiueos-user-macos-native.py")
WINDOWS16 = Path(__file__).with_name("check-aiueos-object-windows16.py")
PAUSE = Path(__file__).with_name("check-aiueos-object-pause.py")
# the pause object's SHA-256 under slice 5 (amu fd84f7e9, unchanged on main 4ece027c): the new block must leave it
PAUSE_SHA256 = "c24f9c962e000ead3c1672975f74f941960c169d9c22bfe824a89a3c7a909403"
DOT = """(ns fdot (:export [kotoba_aiueos_dot_f32]))
(defn kotoba_aiueos_dot_f32 [a :i64 an :i64 b :i64 bn :i64 c :i64] :i64 (kernel-dot-f32 a an b bn c))
"""
PTQ1 = """(ns fptq1 (:export [kotoba_aiueos_dequant_dot_ptq1_0]))
(defn kotoba_aiueos_dequant_dot_ptq1_0 [w :i64 wn :i64 x :i64 xn :i64 c :i64] :i64 (kernel-dequant-dot-ptq1-0 w wn x xn c))
"""
GUARD = bytes.fromhex("31c031c90fa283f807")          # xor eax,eax; xor ecx,ecx; cpuid; cmp eax,7
XGETBV = bytes.fromhex("31c90f01d0")
COMMON = {"span-a": bytes.fromhex("4881f900000100"), "span-b": bytes.fromhex("4881fa00000100"),
          "vhaddps": bytes.fromhex("c5fb7cc0c5fb7cc0"), "vzeroupper": bytes.fromhex("c5f877"),
          "scalar-tree": bytes.fromhex("f30f58c1f30f58d3f30f58c2")}
LIMIT = {"dot": bytes.fromhex("483d00400000"), "ptq1": bytes.fromhex("483d80000000")}
LANES = bytes.fromhex("c5f858c1c5f858c2")              # vaddps xmm0 += lower half, then upper half
REFUSALS = {
    "dot-four": ("(ns r (:export [f]))\n(defn f [a :i64 b :i64] :i64 (kernel-dot-f32 a 64 b 64))\n", "E2103"),
    "dot-six": ("(ns r (:export [f]))\n(defn f [a :i64 an :i64 b :i64 bn :i64] :i64 (kernel-dot-f32 a an b bn 8 0))\n",
                "E2103"),
    "ptq1-four": ("(ns r (:export [f]))\n(defn f [a :i64 b :i64] :i64 (kernel-dequant-dot-ptq1-0 a 28 b 512))\n", "E2103"),
    "ptq1-six": ("(ns r (:export [f]))\n(defn f [a :i64 an :i64 b :i64 bn :i64] :i64 "
                 "(kernel-dequant-dot-ptq1-0 a an b bn 1 0))\n", "E2103"),
    "dot-computed-length": ("(ns r (:export [f]))\n(defn f [a :i64 an :i64 b :i64 bn :i64 c :i64] :i64 "
                            "(kernel-dot-f32 a (* c 4) b (* c 4) c))\n", "E7106"),
    "ptq1-computed-length": ("(ns r (:export [f]))\n(defn f [a :i64 an :i64 b :i64 bn :i64 c :i64] :i64 "
                             "(kernel-dequant-dot-ptq1-0 a an b (* c 512) c))\n", "E7106"),
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

    for name, source, lanes in (("dot", DOT, 1), ("ptq1", PTQ1, 16)):
        _, obj = windows16.compile_source(gate, compiler, output, name, source)
        text = windows16.text_section(obj)
        found = {key: text.count(value) for key, value in COMMON.items()}
        found.update(guard=text.count(GUARD), xgetbv=text.count(XGETBV), limit=text.count(LIMIT[name]),
                     lanes=text.count(LANES))
        want = {key: 1 for key in COMMON}
        want.update(guard=1, xgetbv=1, limit=1, lanes=lanes)
        if found != want:
            raise ValueError(f"{name} sequence {found}, expected {want}")
        report[name] = {"sequence": found, "textBytes": len(text), "sha256": hashlib.sha256(obj.read_bytes()).hexdigest()}

    pause = load(PAUSE, "pause_gate")
    _, obj = windows16.compile_source(gate, compiler, output, "pause", pause.SOURCE)
    digest = hashlib.sha256(obj.read_bytes()).hexdigest()
    if GUARD in windows16.text_section(obj) or digest != PAUSE_SHA256:
        raise ValueError(f"the pause object changed or carries the block: {digest}")
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
        report[name] = "refused " + code
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS_AIUEOS_OBJECT_FUSED_DOT " + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
