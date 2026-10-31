#!/usr/bin/env python3
"""f32 -> i64 truncation on the aiueos kernel object route (JUN-633 slice 7, ADR 0395).

seed/70's xg-fun emits `f32-to-i64-truncating` (SIR UOP 37) and seed/74's xo-check-sir admits it on the object
artifact only. The semantics: truncation toward zero; a NaN or an operand outside [-2^63, 2^63) reaches ud2, so the
route never answers cvttss2si's integer indefinite except for -2^63 itself. Compiles with a native Amu compiler and
checks (Python stages and observes; it emits nothing):

* guard: the object exporting the conversion carries, exactly once, cvttss2si rax,[rbp+d]; mov rcx,rax; neg rcx;
  jno +14; cmp dword [rbp+d],0xdf000000 (the same slot); je +2; ud2 -- and no cvtss2si (rounding) or cvttsd2si;
* opt-in: objects that do not name the conversion keep their bytes -- slice 3's fops object, the pause object and the
  512-byte width object keep the SHA-256 they have on main 3d160442;
* refused, nothing written, on the object route: one or two operands short or over (E2103), a non-f32 operand (E2104),
  and f64 -> i64 truncation (E7101, still not emitted);
* refused on every other x86 route: x86_64-linux and the kernel image artifact answer E7101 detail 37 for the same
  conversion, so only the object artifact admits it.

Not shown here: execution. docs/evidence/f32-to-i64-20261031/ runs the object under QEMU against a C reference.
"""

import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path

MAC_GATE = Path(__file__).with_name("check-aiueos-user-macos-native.py")
WINDOWS16 = Path(__file__).with_name("check-aiueos-object-windows16.py")
PAUSE = Path(__file__).with_name("check-aiueos-object-pause.py")
FOPS = Path(__file__).resolve().parents[2] / "docs/evidence/f32-sse-20261030/fops.kotoba"
# the objects' SHA-256 under amu main 3d160442 (slice 6), before the conversion existed
FOPS_SHA256 = "77838ccc70c641f2b52596e312e834c0db5dcbe5aea85b356964fdde86de0115"
PAUSE_SHA256 = "c24f9c962e000ead3c1672975f74f941960c169d9c22bfe824a89a3c7a909403"
SOURCE = """(ns f2i (:export [kotoba_aiueos_f32_to_i64]))
(defn kotoba_aiueos_f32_to_i64 [bits :i64] :i64 (f32-to-i64-truncating (f32-from-bits bits)))
"""
GUARD = re.compile(rb"\xf3\x48\x0f\x2c\x85(....)\x48\x89\xc1\x48\xf7\xd9\x71\x0e\x81\xbd(....)\x00\x00\x00\xdf\x74\x02\x0f\x0b",
                   re.DOTALL)
ABSENT = {"cvtss2si": bytes.fromhex("f3480f2d"), "cvttsd2si": bytes.fromhex("f2480f2c")}
OBJECT_REFUSALS = {
    "two-operands": ("(ns r (:export [f]))\n(defn f [x :i64] :i64 "
                     "(f32-to-i64-truncating (f32-from-bits x) (f32-from-bits x)))\n", "E2103"),
    "no-operand": ("(ns r (:export [f]))\n(defn f [x :i64] :i64 (f32-to-i64-truncating))\n", "E2103"),
    "i64-operand": ("(ns r (:export [f]))\n(defn f [x :i64] :i64 (f32-to-i64-truncating x))\n", "E2104"),
    "f64-to-i64": ("(ns r (:export [f]))\n(defn f [x :i64] :i64 (f64-to-i64-truncating (f64-from-bits x)))\n", "E7101"),
}
# the conversion is the first float SIR in each source, so detail 37 names it
ROUTE_REFUSALS = {
    "x86_64-linux": ("(defn main [] :i64 (f32-to-i64-truncating (__r6-as :f32 1065353216)))\n",
                     ("--target", "x86_64-linux")),
    "kernel-image": ("(ns g (:export [kotoba_aiueos_f]))\n"
                     "(defn kotoba_aiueos_f [x :i64] :i64 (f32-to-i64-truncating (__r6-as :f32 x)))\n",
                     ("--target", "x86_64-aiueos-kernel-v1", "--artifact", "image")),
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

    _, obj = windows16.compile_source(gate, compiler, output, "f2i", SOURCE)
    text = windows16.text_section(obj)
    hits = GUARD.findall(text)
    if len(hits) != 1 or hits[0][0] != hits[0][1]:
        raise ValueError(f"guarded cvttss2si sequence found {len(hits)} times: {hits}")
    absent = {name: text.count(seq) for name, seq in ABSENT.items()}
    if any(absent.values()) or text.count(bytes.fromhex("f3480f2c")) != 1:
        raise ValueError(f"unexpected conversions {absent}")
    report["guard"] = {"slot": int.from_bytes(hits[0][0], "little", signed=True),
                       "sha256": hashlib.sha256(obj.read_bytes()).hexdigest()}

    pause = load(PAUSE, "pause_gate")
    for name, source, want in (("fops", FOPS.read_text(), FOPS_SHA256), ("pause", pause.SOURCE, PAUSE_SHA256),
                               ("widths", windows16.WIDTHS_SOURCE, windows16.WIDTHS_SHA256)):
        _, obj = windows16.compile_source(gate, compiler, output, name, source)
        digest = hashlib.sha256(obj.read_bytes()).hexdigest()
        if digest != want or GUARD.search(windows16.text_section(obj)):
            raise ValueError(f"the {name} object changed: {digest}")
        report[name + "Unchanged"] = digest

    for name, (source, code) in OBJECT_REFUSALS.items():
        result, obj = windows16.compile_source(gate, compiler, output, name, source, expected=1)
        message = (result.stdout + result.stderr).decode(errors="replace")
        if code not in message or obj.exists():
            raise ValueError(f"{name} was not refused with {code} and no output: {message}")
        report[name] = "refused " + code

    for name, (source, target) in ROUTE_REFUSALS.items():
        (output / f"{name}.kotoba").write_text(source)
        dest = output / f"{name}.out"
        result = gate.native_run(compiler, output, "compile", f"{name}.kotoba", *target, "--output", dest.name,
                                 "--fuel", "1000000", expected=1)
        message = (result.stdout + result.stderr).decode(errors="replace")
        if "E7101" not in message or not message.rstrip().endswith("detail 37") or dest.exists():
            raise ValueError(f"{name} did not refuse the conversion (E7101 detail 37): {message}")
        report[name] = "refused E7101 detail 37"
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS_AIUEOS_OBJECT_F2I " + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
