#!/usr/bin/env python3
"""Native keyword-keyed map literals are closed records, and records hold :f64 fields (JUN-728).

lang/guest-grammar.edn :map-literal :value-types :keyword-keys and the amu
ladder floor :literal-typing (docs/language-ladder.edn): a keyword map literal
is a closed record wherever it is written. seed/21-check (ck-kwrec) types it by
its values; literals with the same keys and field types share one anonymous
record type; 30-lower (lw-kwrec) builds the pair chain in the printed-text order
of the keys. A record field may be :f64 (an i64 word of IEEE-754 bits).

This gate, on Apple Silicon:

* builds seed/tests/native-keyword-map-record.kotoba with --compiler (the Mac
  fixed point of this tree) and the descriptor's packager and runs it: exit 0;
* checks that each refusal below is refused at check time with its named code;
* negative controls: two mutant full compilers built from this tree's
  FULL-MANIFEST -- one without the keyword-literal route (the typed-map literal
  only, as before JUN-728), one that refuses :f64 record fields again -- must
  refuse the corpus with E2105 and E2128;
* runs the corpus through the public CLI (bin/amu run), which must print 0.

Python stages sources and observes processes; every compiler and program is a
native Amu-built Mach-O.
"""

import argparse
import importlib.util
import os
import platform
import subprocess
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "seed/tests/native-keyword-map-record.kotoba"
CHECK = "seed/21-check.kotoba"
LITERAL = "(if (= (nm-kind M (nm-first M n)) ND-KW) (ck-kwrec M n fx) (ck-maplit2 M n fx))"
F64 = ["(= ty ck-ty-f32) (ck-err M1 E-CHECK-SCHEMA k 0)", "(= ty ck-ty-f32) (ck-err M1 E-CHECK-SCHEMA c 0)"]
MUTANTS = [
    ("no-keyword-literal", [(LITERAL, "(ck-maplit2 M n fx)")], "E2105"),
    ("no-f64-field", [(x, x.replace("(= ty ck-ty-f32)", "(or (= ty TY-F64) (= ty ck-ty-f32))")) for x in F64], "E2128"),
]
REFUSALS = [
    ("assoc-new-key", "(defn main [] :i64 (let [m (assoc {:a 1} :b 2)] (:b m)))", "E2127"),
    ("absent-key", "(defn main [] :i64 (let [m {:a 1}] (:z m)))", "E2127"),
    ("mixed-key-kinds", "(defn main [] :i64 (let [m {:a 1 \"b\" 2}] 0))", "E2105"),
    ("repeated-key", "(defn main [] :i64 (let [m {:a 1 :a 2}] 0))", "E2128"),
    ("fn-value", "(defn main [] :i64 (let [m {:f (fn [x] x)}] 0))", "E2128"),
    ("f32-field", "(defrecord W [x :f32])\n(defn main [] :i64 0)", "E2128"),
    ("33-fields", "(defn main [] :i64 (let [m {" + " ".join(f":k{i} {i}" for i in range(33)) + "}] 0))", "E2128"),
    ("empty", "(defn main [] :i64 (let [m {}] 0))", "E2133"),
    ("declared-record-parameter",
     "(defn g [m [:record :kotoba.map-literal/a+b [[:a :i64] [:b :string]]]] :i64 (:a m))\n"
     "(defn main [] :i64 (g {:a 4 :b \"x\"}))", "E2104"),
]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(compiler, directory, name, source):
    """Run `compiler check name.kotoba` with directory as the FD3 root; return (exit, output)."""
    (directory / f"{name}.kotoba").write_text(source)
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    saved = None
    try:
        try:
            saved = os.dup(3)
        except OSError:
            pass
        os.dup2(fd, 3)
        result = subprocess.run([str(compiler), "check", f"{name}.kotoba"], cwd=directory, pass_fds=(3,),
                                env={"PATH": "/usr/bin:/bin", "LANG": "C"}, capture_output=True, timeout=600)
    finally:
        if saved is None:
            os.close(3)
        else:
            os.dup2(saved, 3)
            os.close(saved)
        os.close(fd)
    return result.returncode, (result.stdout + result.stderr).decode(errors="replace")


def main(compiler, output):
    if platform.system() != "Darwin" or platform.machine() not in ("arm64", "aarch64"):
        raise ValueError("Apple Silicon native host required")
    scope = load("scope", ROOT / "scripts/seed/check-macos-arena-scope.py")
    gate = scope.module()
    _, _, packager, _, _, _ = gate.bootstrap_inputs(SimpleNamespace(
        compiler_image=None, compiler_sha256=None, packager_image=None, packager_sha256=None))
    gate.verify_macho(compiler)
    gate.verify_macho(packager)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)

    fixed = output / "fixed"; fixed.mkdir(mode=0o700)
    image = scope.build(gate, compiler, packager, fixed, "corpus", CORPUS)
    gate.native_run(image, fixed, expected=0)
    print("fixed compiler: corpus exit 0", flush=True)

    refusals = output / "refusals"; refusals.mkdir(mode=0o700)
    for name, source, code in REFUSALS:
        status, text = check(compiler, refusals, name, source)
        if status == 0 or code not in text:
            raise ValueError(f"{name}: expected a check-time {code}, got exit {status}: {text[-300:]!r}")
        print(f"refused {name}: {code}", flush=True)

    names = [line for line in (ROOT / "seed/FULL-MANIFEST").read_text().splitlines()
             if line and not line.startswith("#")]
    if CHECK not in names:
        raise ValueError("FULL-MANIFEST no longer lists " + CHECK)
    original = (ROOT / CHECK).read_text()
    for label, edits, code in MUTANTS:
        text = original
        for old, new in edits:
            if text.count(old) != 1:
                raise ValueError(f"cannot construct the {label} negative control")
            text = text.replace(old, new)
        mutant = output / label; mutant.mkdir(mode=0o700)
        with (mutant / "full-unity.kotoba").open("w") as stream:
            for name in names:
                stream.write((text if name == CHECK else (ROOT / name).read_text()) + "\n")
        mutant_compiler = scope.build(gate, compiler, packager, mutant, "full-unity",
                                      (mutant / "full-unity.kotoba").read_text())
        if gate.pin(mutant_compiler) == gate.pin(compiler):
            raise ValueError("mutant compiler is identical to the compiler under test: " + label)
        status, out = check(mutant_compiler, mutant, "corpus", CORPUS.read_text())
        if status == 0 or code not in out:
            raise ValueError(f"{label} mutant: expected the corpus refused with {code}, got exit {status}: {out[-300:]!r}")
        print(f"{label} (mutant compiler): corpus refused with {code}", flush=True)

    public = output / "public"; public.mkdir(mode=0o700)
    (public / "corpus.kotoba").write_bytes(CORPUS.read_bytes())
    result = subprocess.run([str(ROOT / "bin/amu"), "run", "corpus.kotoba"], cwd=public,
                            env={"PATH": "/usr/bin:/bin", "LANG": "C"},
                            capture_output=True, timeout=600)
    if result.returncode != 0 or result.stdout != b"0\n" or result.stderr:
        raise ValueError(f"bin/amu run: exit {result.returncode}, stdout {result.stdout!r}, "
                         f"stderr {result.stderr[-400:]!r}")
    print("bin/amu run corpus: 0", flush=True)
    print("PASS_NATIVE_KEYWORD_MAP_RECORD_WITH_NEGATIVE_CONTROLS", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
