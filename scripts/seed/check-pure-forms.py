#!/usr/bin/env python3
"""The pure heads lam, app and ref in the native frontend (JUN-950).

kotoba-lang lang/pure-form.edn, against the native checker as measured at amu
1754ff26f, where lam, app and ref were each E2101 and (def f (lam ..)) could not
be written. seed/20-names lowers them before any name is registered:

* (def NAME (lam [x T ..] R BODY)) becomes (defn NAME [x T ..] R BODY);
* (lam [x ..] BODY) becomes (fn [x ..] BODY);
* (ref NAME) becomes NAME; (ref "bafy..") stays E2101 until a definition can be
  read by CID;
* (app NAME a ..) becomes (NAME a ..), and (app COMPUTED a ..) becomes
  (invoke COMPUTED a ..).

This gate, on Apple Silicon:

* builds seed/tests/native-pure-forms.kotoba with --compiler (the Mac fixed point
  of this tree) and runs it: exit 0;
* checks every refusal below at check time with its named code;
* checks that a module defining or binding one of the names keeps its own meaning;
* Definition CIDs (definition-cids): each pure spelling prints the CIDs of its
  surface spelling, and each control differs. (app (lam ..) a) has no CID: its
  invoke is unbridged, and that refusal is asserted so that a change is noticed;
* negative controls: one mutant full compiler per load-bearing change, built from
  this tree's FULL-MANIFEST with that change removed;
* runs the corpus through the public CLI (bin/amu run), which must print 0.

Python stages sources and observes processes; every compiler and program is a
native Amu-built Mach-O.
"""

import argparse
import importlib.util
import platform
import subprocess
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "seed/tests/native-pure-forms.kotoba"
NAMES = "seed/20-names.kotoba"
NS = "(ns d (:export [main]))\n"
MAIN = "(def main (lam [] :i64 1))\n"
SHAPE = "E2184 lam takes one body, and at the top level every parameter and its result are annotated"
REFUSALS = [
    ("unannotated-parameter", "(def f (lam [x] :i64 x))\n" + MAIN, SHAPE),
    ("unannotated-second-parameter", "(def f (lam [x :i64 y] :i64 x))\n" + MAIN, SHAPE),
    ("no-result-type", "(def f (lam [x :i64] x))\n" + MAIN, SHAPE),
    ("two-bodies", "(def f (lam [x :i64] :i64 x x))\n" + MAIN, SHAPE),
    ("no-body", "(def f (lam [x :i64] :i64))\n" + MAIN, SHAPE),
    ("variadic", "(def f (lam [x :i64 & r] :i64 x))\n" + MAIN, SHAPE),
    ("destructuring", "(def f (lam [[a b] :i64] :i64 a))\n" + MAIN, SHAPE),
    ("no-parameter-vector", "(def f (lam x :i64 x))\n" + MAIN, SHAPE),
    ("inner-two-bodies", "(def main (lam [] :i64 (let [g (lam [x] x x)] (g 1))))\n", SHAPE),
    ("inner-no-vector", "(def main (lam [] :i64 (let [g (lam x x)] 1)))\n", SHAPE),
    ("inner-annotation", "(def main (lam [] :i64 (let [g (lam [x :i64] x)] (g 1))))\n", "E2139"),
    ("ref-by-cid", "(def main (lam [] :i64 (let [g (ref \"bafyreiblk\")] 1)))\n", "E2101 unknown or unsupported form 'ref'"),
    ("ref-two-names", "(def f (lam [] :i64 1))\n(def main (lam [] :i64 (let [g (ref f f)] 1)))\n",
     "E2101 unknown or unsupported form 'ref'"),
    ("app-no-operator", "(def main (lam [] :i64 (app)))\n", "E2101 unknown or unsupported form 'app'"),
    ("def-of-fn", "(def f (fn [x :i64] :i64 x))\n" + MAIN, "E2124"),
]
# A module that defines or binds the name keeps its own meaning: (name, source, expected exit)
OWN_MEANING = [
    ("defines-app", "(defn app [x :i64] :i64 (+ x 1))\n(defn main [] :i64 (app 41))\n", 42),
    ("defines-lam", "(defn lam [x :i64] :i64 x)\n(defn main [] :i64 (lam 42))\n", 42),
    ("defines-ref", "(defn ref [x :i64] :i64 x)\n(defn main [] :i64 (ref 42))\n", 42),
    ("parameter-app", "(defn f [app :i64] :i64 app)\n(defn main [] :i64 (f 42))\n", 42),
    ("let-app", "(defn main [] :i64 (let [app (fn [x] (+ x 1))] (app 41)))\n", 42),
]
D = "(defn inc1 [n :i64] :i64 (+ n 1))\n"
P = "(def inc1 (lam [n :i64] :i64 (+ n 1)))\n"
# Each row: spellings that must print the same CIDs, then a control that must not.
CID_GROUPS = [
    ("definition",
     [D + "(defn main [] :i64 (inc1 (inc1 40)))\n",
      P + "(def main (lam [] :i64 (inc1 (inc1 40))))\n",
      P + "(def main (lam [] :i64 (app (ref inc1) (app (ref inc1) 40))))\n",
      D + "(defn main [] :i64 (-> 40 inc1 inc1))\n"],
     P + "(def main (lam [] :i64 (inc1 (inc1 41))))\n"),
    ("cond-is-if",
     ["(defn main [] :i64 (cond (< 1 2) 1 :else 0))\n", "(def main (lam [] :i64 (if (< 1 2) 1 0)))\n"],
     "(def main (lam [] :i64 (if (< 1 3) 1 0)))\n"),
]
# loop lifts a helper, so the rows differ in order and name; the CIDs per definition must agree.
LOOP = "(defn main [] :i64 (loop [i 0] (if (= i 3) i (recur (+ i 1)))))\n"
TAIL = "(def lp (lam [i :i64] :i64 (if (= i 3) i (lp (+ i 1)))))\n(def main (lam [] :i64 (lp 0)))\n"
TAIL_CONTROL = "(def lp (lam [i :i64] :i64 (if (= i 4) i (lp (+ i 1)))))\n(def main (lam [] :i64 (lp 0)))\n"
BETA = P + "(def main (lam [] :i64 (app (ref inc1) (app (lam [x] (+ x 1)) 40))))\n"
USER_APP = NS + OWN_MEANING[0][1]
# (label, [(old, new)], source to check, expected text in the refusal, or None when it must now be admitted)
MUTANTS = [
    ("no-pure-pass",
     [("(nm-run-defs (nm-dp-norm (nm-pure-norm (nm-r6b-norm (nm-intern-nodes M S 1)))))",
       "(nm-run-defs (nm-dp-norm (nm-r6b-norm (nm-intern-nodes M S 1))))")],
     CORPUS.read_text(), "E2005 export of undefined function 'main'"),
    ("app-keeps-its-head",
     [("(= (nm-kind M op) ND-SYM) (nm-set-nf M n NF-FIRST op)", "(= (nm-kind M op) ND-SYM) (nm-touch M)")],
     CORPUS.read_text(), "E2101 unknown or unsupported form 'app'"),
    ("ref-keeps-its-head",
     [("(nm-pf-head? M n nm-pf-ref) (nm-pf-refs (nm-pf-ref1 M n) (+ n 1))", "(nm-pf-head? M n nm-pf-ref) (nm-pf-refs M (+ n 1))")],
     CORPUS.read_text(), "unknown or unsupported form 'ref'"),
    ("top-lam-unchecked",
     [("(and (= (nm-count M l) 4) (= (nm-kind M v) ND-VEC) (nm-pf-typed-params? M v) (nm-pf-type? M r))",
       "(and (= (nm-kind M v) ND-VEC) (nm-pf-type? M r))")],
     NS + REFUSALS[0][1], None),
    ("user-name-rewritten",
     [("(and (nm-pf-spelled? M hash) (not (nm-pf-user? M hash)))", "(nm-pf-spelled? M hash)")],
     USER_APP, "E2104 type mismatch in 'app'"),
]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cid_rows(helper, compiler, directory, name, source):
    """{cid: count} of a definition-cids report, ignoring names and order; refuses a report with a refusal."""
    out = helper.cids(compiler, directory, name, NS + source)
    if "REFUSED" in out:
        raise ValueError(f"{name}: definition refused: {out!r}")
    rows = [line.split("\t")[1] for line in out.splitlines() if "\t" in line and not line.startswith("SCANNED")]
    if not rows:
        raise ValueError(f"{name}: no definitions reported: {out!r}")
    return sorted(rows)


def main(compiler, output):
    if platform.system() != "Darwin" or platform.machine() not in ("arm64", "aarch64"):
        raise ValueError("Apple Silicon native host required")
    helper = load("closed_dispatch", ROOT / "scripts/seed/check-closed-dispatch.py")
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
        status, out, err = helper.native(compiler, refusals, "check", name, NS + source)
        if status == 0 or code not in out + err:
            raise ValueError(f"{name}: expected a check-time {code}, got exit {status}: {(out + err)[-300:]!r}")
        print(f"refused {name}: {code}", flush=True)

    own = output / "own-meaning"; own.mkdir(mode=0o700)
    for name, source, expected in OWN_MEANING:
        status = helper.build_run(scope, gate, compiler, packager, own, name, NS + source)
        if status != expected:
            raise ValueError(f"{name}: expected exit {expected}, got {status}")
        print(f"own meaning kept: {name} exit {expected}", flush=True)

    ids = output / "cids"; ids.mkdir(mode=0o700)
    for label, spellings, control in CID_GROUPS:
        rows = [cid_rows(helper, compiler, ids, f"{label}-{i}", s) for i, s in enumerate(spellings)]
        if any(row != rows[0] for row in rows):
            raise ValueError(f"{label}: spellings print different CIDs: {rows}")
        if cid_rows(helper, compiler, ids, f"{label}-control", control) == rows[0]:
            raise ValueError(f"{label}: the control has the spellings' CIDs")
        print(f"definition-cids: {label}: {len(spellings)} spellings agree; control differs", flush=True)
    loop, tail = (cid_rows(helper, compiler, ids, n, s) for n, s in (("loop", LOOP), ("tail", TAIL)))
    if loop != tail:
        raise ValueError(f"loop and the tail-recursive def print different CIDs: {loop} {tail}")
    if cid_rows(helper, compiler, ids, "tail-control", TAIL_CONTROL) == tail:
        raise ValueError("the tail-recursion control has the same CIDs")
    print("definition-cids: loop = tail-recursive def; control differs", flush=True)
    status, out, err = helper.native(compiler, ids, "definition-cids", "beta", NS + BETA)
    if "REFUSED:unbridged-source" not in out + err:
        raise ValueError(f"(app (lam ..) a): expected the unbridged refusal, got exit {status}: {(out + err)[-300:]!r}")
    print("definition-cids: (app (lam ..) a) refused as unbridged, the recorded boundary", flush=True)

    names = [line for line in (ROOT / "seed/FULL-MANIFEST").read_text().splitlines()
             if line and not line.startswith("#")]
    for label, edits, source, expected in MUTANTS:
        text = (ROOT / NAMES).read_text()
        for old, new in edits:
            if text.count(old) != 1:
                raise ValueError(f"cannot construct the {label} negative control")
            text = text.replace(old, new)
        mutant = output / label; mutant.mkdir(mode=0o700)
        with (mutant / "full-unity.kotoba").open("w") as stream:
            for name in names:
                stream.write((text if name == NAMES else (ROOT / name).read_text()) + "\n")
        mutant_compiler = scope.build(gate, compiler, packager, mutant, "full-unity",
                                      (mutant / "full-unity.kotoba").read_text())
        if gate.pin(mutant_compiler) == gate.pin(compiler):
            raise ValueError("mutant compiler is identical to the compiler under test: " + label)
        status, out, err = helper.native(mutant_compiler, mutant, "check", "probe", source)
        if expected is None:
            if status != 0:
                raise ValueError(f"{label} mutant: expected the refused source admitted, got exit {status}: "
                                 f"{(out + err)[-300:]!r}")
            print(f"{label} (mutant compiler): the refused source is admitted", flush=True)
        else:
            if status == 0 or expected not in out + err:
                raise ValueError(f"{label} mutant: expected a refusal with {expected}, got exit {status}: "
                                 f"{(out + err)[-300:]!r}")
            print(f"{label} (mutant compiler): refused with {expected}", flush=True)

    public = output / "public"; public.mkdir(mode=0o700)
    (public / "corpus.kotoba").write_bytes(CORPUS.read_bytes())
    result = subprocess.run([str(ROOT / "bin/amu"), "run", "corpus.kotoba"], cwd=public,
                            env={"PATH": "/usr/bin:/bin", "LANG": "C"},
                            capture_output=True, timeout=600)
    if result.returncode != 0 or result.stdout != b"0\n" or result.stderr:
        raise ValueError(f"bin/amu run: exit {result.returncode}, stdout {result.stdout!r}, "
                         f"stderr {result.stderr[-400:]!r}")
    print("bin/amu run corpus: 0", flush=True)
    print("PASS_NATIVE_PURE_FORMS_WITH_NEGATIVE_CONTROLS", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
