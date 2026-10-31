#!/usr/bin/env python3
"""Native destructuring is reader sugar for the plain temp-bound form (JUN-729).

lang/guest-grammar.edn :nested-destructuring (L2) and
lang/surface-equivalence-corpus.edn :destructuring: a vector / map pattern in a
let or loop binding or a defn parameter desugars to sequential temp-bound
nth / vector-drop / get bindings, and the sugar and the pure spelling must mint
the same Definition CID. seed/21-check (ck-dx-*) expands the patterns before
typing; seed/20-names counts a pattern parameter as one parameter.

This gate, on Apple Silicon:

* builds seed/tests/native-destructuring.kotoba with --compiler (the Mac fixed
  point of this tree) and the descriptor's packager and runs it: exit 0;
* checks that each refusal below is refused at check time with its named code;
* Definition CIDs (`definition-cids`, profile 6 / desugar 2): every sugar/pure
  pair prints the same report; for the MEASURED pairs that report holds CIDs
  (no refusal) and each control prints a different one. The UNMEASURED pairs are
  refused identically on both sides by the definition bridge (`get`, and the
  vector-drop library group), so equality is not observable there;
* negative controls: two mutant full compilers built from this tree's
  FULL-MANIFEST -- one without the let/loop expansion, one without the
  parameter expansion -- must refuse the corpus (E2111 at a let pattern, E2111
  at the `&` of a pattern rest parameter), and the
  first one must not reproduce the pure CID of the corpus vector pair;
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
CORPUS = ROOT / "seed/tests/native-destructuring.kotoba"
CHECK = "seed/21-check.kotoba"
HOOK = "          (and (= k ND-LIST) (ck-dx-let? M n)) (ck-ds-walk (ck-dx M S n) S n)   ; JUN-729: destructuring\n"
PARAMS = "(if (= (nm-kind M p) ND-VEC) (ck-dx-params M p) (nm-put M MM-R0 0))"
MUTANTS = [
    ("no-let-loop-expansion", [(HOOK, "")], "E2111"),
    # the first refusal is the variadic pattern rest of prest (ck-ds-rest admits only a symbol after &)
    ("no-parameter-expansion", [(PARAMS, "(nm-put M MM-R0 0)")], "E2111 malformed binding vector in '&'"),
]
NS = "(ns d (:export [main]))\n"
REFUSALS = [
    ("strs-keys", "(defn main [] :i64 (let [{:strs [a]} {:a 1}] a))", "E2111"),
    ("syms-keys", "(defn main [] :i64 (let [{:syms [a]} {:a 1}] a))", "E2111"),
    ("keyword-in-vector", "(defn main [] :i64 (let [[a :b] [1 2]] a))", "E2111"),
    ("after-rest", "(defn main [] :i64 (let [[a & r b] [1 2 3]] a))", "E2111"),
    ("dangling-amp", "(defn main [] :i64 (let [[a &] [1 2 3]] a))", "E2111"),
    ("as-not-symbol", "(defn main [] :i64 (let [[a :as [b]] [1 2]] a))", "E2111"),
    ("or-not-map", "(defn main [] :i64 (let [{:keys [a] :or [a 1]} {:a 1}] a))", "E2111"),
    ("unspelled-key", "(defn main [] :i64 (let [{:keys [nope] :or {nope 1}} (typed-map-new [:map :keyword :i64] :a 1)] nope))", "E2111"),
    ("string-key", "(defn main [] :i64 (let [{a \"a\"} {:a 1}] a))", "E2111"),
    ("rest-of-list", "(defn main [] :i64 (let [[a & r] (typed-list-new [:list :i64] 1 2)] a))", "E2104"),
    ("or-on-record", "(defn main [] :i64 (let [{:keys [a] :or {a 1}} {:a 2}] a))", "E2104"),
    # JUN-734: (get g :a) on a typed map is [:option :i64], so `a` is an option and main's :i64 result refuses
    ("typed-map-no-default", "(defn main [] :i64 (let [{:keys [a]} (typed-map-new [:map :keyword :i64] :a 2)] a))", "E2121"),
    ("untyped-pattern-param", "(defn f [[a b]] :i64 (+ a b))\n(defn main [] :i64 (f 1))", "E2104"),
    ("fn-literal-pattern", "(defn main [] :i64 ((fn [[a b]] (+ a b)) [1 2]))", "E2139"),
    ("duplicate-name", "(defn main [] :i64 (let [[a a] [1 2]] a))", "E2112"),
]
MAIN = "\n(defn main [] (run))\n"
# (id, sugar, pure, control or None, measured)
PAIRS = [
    ("vector (surface-equivalence-corpus :destructuring :vector)",
     NS + "(defn run [] (let [[a b] [1 2]] (+ a b)))" + MAIN,
     NS + "(defn run [] (let [t [1 2] a (nth t 0) b (nth t 1)] (+ a b)))" + MAIN,
     NS + "(defn run [] (let [[a b] [2 2]] (+ a b)))" + MAIN, True),
    ("vector :as and _",
     NS + "(defn run [] (let [[a _ c :as v] [1 2 3]] (+ a (+ c (count v)))))" + MAIN,
     NS + "(defn run [] (let [t [1 2 3] a (nth t 0) c (nth t 2) v t] (+ a (+ c (count v)))))" + MAIN,
     NS + "(defn run [] (let [[a _ c :as v] [1 2 3]] (+ a (- c (count v)))))" + MAIN, True),
    ("nested vector",
     NS + "(defn run [] (let [[[a b] [c]] (typed-list-new [:list :vector-i64] [1 2] [3])] (+ a (+ b c))))" + MAIN,
     NS + "(defn run [] (let [t (typed-list-new [:list :vector-i64] [1 2] [3]) u (nth t 0) a (nth u 0) b (nth u 1)"
          " w (nth t 1) c (nth w 0)] (+ a (+ b c))))" + MAIN,
     NS + "(defn run [] (let [[[a b] [c]] (typed-list-new [:list :vector-i64] [1 2] [4])] (+ a (+ b c))))" + MAIN, True),
    ("defn parameter",
     NS + "(defn f [[a b] :vector-i64] :i64 (+ a b))\n(defn main [] (f [1 2]))\n",
     NS + "(defn f [t :vector-i64] :i64 (let [a (nth t 0) b (nth t 1)] (+ a b)))\n(defn main [] (f [1 2]))\n",
     NS + "(defn f [[a b] :vector-i64] :i64 (- a b))\n(defn main [] (f [1 2]))\n", True),
    ("loop (clojure.core/loop expansion)",
     NS + "(defn run [] :i64 (loop [[a b] [1 2] n 0] (if (> n 3) (+ a b) (recur [b a] (+ n 1)))))" + MAIN,
     NS + "(defn run [] :i64 (let [g [1 2] a (nth g 0) b (nth g 1) n 0] (loop [g g n n] (let [a (nth g 0) b (nth g 1)"
          " n n] (if (> n 3) (+ a b) (recur [b a] (+ n 1)))))))" + MAIN,
     NS + "(defn run [] :i64 (loop [[a b] [1 2] n 0] (if (> n 4) (+ a b) (recur [b a] (+ n 1)))))" + MAIN, True),
    ("map :keys/:or (surface-equivalence-corpus :destructuring :map-keys-or)",
     NS + "(defn run [] (let [{:keys [x y] :or {x 0 y 0}} (typed-map-new [:map :keyword :i64] :x 2 :y 3)] (+ x y)))" + MAIN,
     NS + "(defn run [] (let [m (typed-map-new [:map :keyword :i64] :x 2 :y 3) x (get m :x 0) y (get m :y 0)] (+ x y)))" + MAIN,
     None, False),
    ("record :keys/:as",
     NS + "(defn run [] (let [{:keys [x y] :as m} {:x 2 :y 3}] (+ x (+ y (:x m)))))" + MAIN,
     NS + "(defn run [] (let [t {:x 2 :y 3} x (get t :x) y (get t :y) m t] (+ x (+ y (:x m)))))" + MAIN,
     None, False),
    ("vector & rest",
     NS + "(defn run [] (let [[a & r] [1 2 3]] (+ a (count r))))" + MAIN,
     NS + "(defn run [] (let [t [1 2 3] a (nth t 0) r (vector-drop t 1)] (+ a (count r))))" + MAIN,
     None, False),
]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def native(compiler, directory, command, name, source):
    """Run `compiler <command> name.kotoba` with directory as the FD3 root; return (exit, stdout, stderr)."""
    (directory / f"{name}.kotoba").write_text(source)
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    saved = None
    try:
        try:
            saved = os.dup(3)
        except OSError:
            pass
        os.dup2(fd, 3)
        result = subprocess.run([str(compiler), command, f"{name}.kotoba"], cwd=directory, pass_fds=(3,),
                                env={"PATH": "/usr/bin:/bin", "LANG": "C"}, capture_output=True, timeout=600)
    finally:
        if saved is None:
            os.close(3)
        else:
            os.dup2(saved, 3)
            os.close(saved)
        os.close(fd)
    return result.returncode, result.stdout.decode(errors="replace"), result.stderr.decode(errors="replace")


def cids(compiler, directory, name, source):
    status, out, err = native(compiler, directory, "definition-cids", name, source)
    return f"exit {status}\n{out}{err}"


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
        status, out, err = native(compiler, refusals, "check", name, NS + source + "\n")
        if status == 0 or code not in out + err:
            raise ValueError(f"{name}: expected a check-time {code}, got exit {status}: {(out + err)[-300:]!r}")
        print(f"refused {name}: {code}", flush=True)

    identity = output / "cids"; identity.mkdir(mode=0o700)
    vector_pure = None
    for index, (label, sugar, pure, control, measured) in enumerate(PAIRS):
        a = cids(compiler, identity, f"s{index}", sugar)
        b = cids(compiler, identity, f"p{index}", pure)
        if a != b:
            raise ValueError(f"{label}: sugar and pure reports differ:\n{a}\n--\n{b}")
        if index == 0:
            vector_pure = b
        if measured:
            if not a.startswith("exit 0\n") or "REFUSED" in a or "SCANNED" not in a:
                raise ValueError(f"{label}: expected identified definitions, got {a!r}")
            c = cids(compiler, identity, f"c{index}", control)
            if not c.startswith("exit 0\n") or c == a:
                raise ValueError(f"{label}: the control does not change the CID: {c!r}")
            run = [line for line in a.splitlines() if line.startswith(("run\t", "f\t"))]
            print(f"CID sugar == pure, control differs: {label}: {run[0] if run else a!r}", flush=True)
        else:
            print(f"CID not observable (both sides print the same refusal): {label}: {a.splitlines()[1:2]}", flush=True)

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
        status, out, err = native(mutant_compiler, mutant, "check", "corpus", CORPUS.read_text())
        if status == 0 or code not in out + err:
            raise ValueError(f"{label} mutant: expected the corpus refused with {code}, got exit {status}: "
                             f"{(out + err)[-300:]!r}")
        print(f"{label} (mutant compiler): corpus refused with {code}", flush=True)
        if label == "no-let-loop-expansion":
            a = cids(mutant_compiler, mutant, "s0", PAIRS[0][1])
            if a == vector_pure or "2111" not in a:
                raise ValueError(f"{label} mutant: the vector sugar still reproduces the pure CID: {a!r}")
            print(f"{label} (mutant compiler): vector sugar has no CID: {a.splitlines()[1:2]}", flush=True)

    public = output / "public"; public.mkdir(mode=0o700)
    (public / "corpus.kotoba").write_bytes(CORPUS.read_bytes())
    result = subprocess.run([str(ROOT / "bin/amu"), "run", "corpus.kotoba"], cwd=public,
                            env={"PATH": "/usr/bin:/bin", "LANG": "C"},
                            capture_output=True, timeout=600)
    if result.returncode != 0 or result.stdout != b"0\n" or result.stderr:
        raise ValueError(f"bin/amu run: exit {result.returncode}, stdout {result.stdout!r}, "
                         f"stderr {result.stderr[-400:]!r}")
    print("bin/amu run corpus: 0", flush=True)
    print("PASS_NATIVE_DESTRUCTURING_WITH_NEGATIVE_CONTROLS", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
