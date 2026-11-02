#!/usr/bin/env python3
"""JUN-595: T2 must not derive whole-program facts from import stubs.

A project compile gives each required module's export an import stub in the
importer, a typing self call whose first instruction the linker replaces with
`b <export>`. T2's whole-program RET0 ("returns its parameter-0 vector"),
may-change-descriptors and least-length facts used to read that SIR as if it
were the export's code. RET0 = 1 for a slice export made the result of a call
alias its first argument, so a later vector-at read the argument's element.

The compiler under test builds a two-module program (an imported slice used
through two private helpers, exit = s[10] = 85) and an identity import
(exit = 7). The negative control is a compiler built by the compiler under test
from the same unity with the four stub guards removed: it must read the wrong
element. Python stages bytes, launches native programs and signs copies.
"""
import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("mac_native", ROOT / "scripts/seed/check-aiueos-user-macos-native.py")
mac = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mac)
_spec = importlib.util.spec_from_file_location("macos_native_image", ROOT / "scripts/seed/macos_native_image.py")
image = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(image)

LIB = """(ns m.lib (:export [slice ident]))
(defn slice [v :vector-i64 start :i64 count :i64] :vector-i64
  (loop [i 0 out (vector-i64)]
    (if (= i count) out (recur (+ i 1) (vector-conj out (vector-at v (+ start i)))))))
(defn ident [v :vector-i64] :vector-i64 v)
"""
MAIN = """(ns m.main (:export [main]) (:require [m.lib :as c]))
(defn- at [batch :vector-i64 offset :i64] :vector-i64
  (c/slice batch offset (vector-at batch (- offset 1))))
(defn- state [a :vector-i64] :vector-i64 (c/slice a 8 (vector-at a 6)))
;; s = [1 0 1 0 0 0 0 0 0 0 85 0 0 0 0]; batch[10] = 1, s[10] = 85
(defn- pick [batch :vector-i64 offset :i64 top :i64] :i64
  (let [s (state (at batch offset))] (vector-at s 10)))
(defn main [] :i64
  (let [batch (c/slice (vector-i64 9 23 1 0 0 0 0 0 15 0 1 0 1 0 0 0 0 0 0 0 85 0 0 0 0) 0 25)]
    (pick batch 2 1)))
"""
IDENT = """(ns m.main (:export [main]) (:require [m.lib :as c]))
(defn- middle [v :vector-i64] :i64 (let [w (c/ident v)] (vector-at w 1)))
(defn main [] :i64 (middle (vector-i64 3 7 9)))
"""
# The four guards of this change; removing them restores the pre-fix behaviour.
GUARDS = [
    (" (not (gn-clamp-open M g)))\n                (t2-mcd-scan M (inc p)) 1)]", ")\n                (t2-mcd-scan M (inc p)) 1)]"),
    ("\n                                                             (not (gn-clamp-open m f)))", ")"),
    (" (lw-spec? M f) (lw-tmpl? M f) (gn-clamp-open M f))", " (lw-spec? M f) (lw-tmpl? M f))"),
    (" (= (t2-g M (+ t2-a-ret0 g)) 1) (not (gn-clamp-open M g)))))", " (= (t2-g M (+ t2-a-ret0 g)) 1))))"),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def project(compiler, packager, out, main_source):
    """Compile lib + main through the source-lock project route and run it."""
    src = out / "src" / "m"
    src.mkdir(parents=True)
    (src / "lib.kotoba").write_text(LIB)
    (src / "main.kotoba").write_text(main_source)
    lock = out / "p.ksl"
    lock.write_text("KSL1\nentry /src/m/main.kotoba\nroot /src\n"
                    + "".join(f"file {sha((src / n).read_bytes())} /src/m/{n}\n" for n in ("lib.kotoba", "main.kotoba")))
    flags = ["--source-path", "/src", "--source-lock", lock.name, "--source-lock-sha256", sha(lock.read_bytes())]
    mac.native_run(compiler, out, "compile", "/src/m/main.kotoba", "--target", "aarch64-macos", "--output", "p.kseed", *flags)
    r = mac.native_run(compiler, out, "extract-native", "p.kseed", "--symbol", "main", "--output", "p.raw")
    match = re.search(rb":offset (\d+), :length (\d+), :arity 0}", r.stdout)
    assert match and int(match[2]) == (out / "p.raw").stat().st_size, r.stdout[-300:]
    mac.native_run(packager, out, "p-unsigned.macho", "p.raw", "fs2-cli-stdio-general", match[1].decode())
    mac.sign(out / "p-unsigned.macho", out / "p.macho")
    return image.run(out / "p.macho", out, []).returncode


def mutant(compiler, packager, out):
    """A compiler built by the compiler under test from the unity without the guards."""
    out.mkdir()
    mac.stage_unity(out)
    text = (out / "full-unity.kotoba").read_bytes()
    for fixed, old in GUARDS:
        assert text.count(fixed.encode()) == 1, ("guard drifted", fixed)
        text = text.replace(fixed.encode(), old.encode())
    (out / "full-unity.kotoba").write_bytes(text)
    return mac.generation(1, compiler, packager, out)[0]


def main(compiler, out):
    assert image.available(), "Apple Silicon host required"
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    _, packager = image.root_images()
    report = dict(schema="amu.macos-import-stub-facts.v1", compiler=mac.pin(compiler), packager=mac.pin(packager))
    report["slice"] = project(compiler, packager, out / "slice", MAIN)
    assert report["slice"] == 85, ("imported slice result aliased its argument", report["slice"])
    report["identity"] = project(compiler, packager, out / "identity", IDENT)
    assert report["identity"] == 7, ("identity import", report["identity"])
    control = mutant(compiler, packager, out / "mutant")
    report["mutant"] = mac.pin(control)
    report["control"] = project(control, packager, out / "control", MAIN)
    assert report["control"] == 1, ("the unguarded compiler must read the argument's element", report["control"])
    report["status"] = "PASS_MACOS_IMPORT_STUB_FACTS"
    (out / "import-stub-facts.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--compiler", type=Path, required=True, help="signed Mac compiler under test")
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    main(a.compiler.resolve(), a.output.resolve())
