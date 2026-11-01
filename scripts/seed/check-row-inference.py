#!/usr/bin/env python3
"""Row inference for unannotated parameters; get with a default on a record (JUN-733 slice 3).

Owner decision 2026-11-01 (Linear JUN-733): native Amu follows the amu ladder's
row floors (docs/language-ladder.edn :row-records, :row-get-and-match,
:options-map-argument). In seed/21-check:

* an unannotated parameter used as a record -- (:k p), get, an assoc / dissoc /
  merge / select-keys operand, a :keys destructuring, or a record passed by a
  caller -- asks the R6C refinement for a ROW (the pseudo type TY-REC-BASE,
  ck-refine-note / ck-row-note); the re-run makes its function a ROW GENERIC
  (FN2-FLAGS bits 0 and 5): never checked or lowered itself, it exists only as
  its specializations, one per tuple of record types a call passes (ck-row-call
  / ck-row-spec: a clone of the defn form typed at them, FN2-FLAGS bit 6);
* (get m :k d) and (:k m d) on a record read a field it has as (:k m) (d of the
  field's type), an [:option T] field as (option-or (:k m) d), and a key the
  record does not have as d (ck-rget-d).

Refused by name: a non-record argument to a row parameter (E2104), a field the
record lacks read without a default (E2127), an explicitly exported row
function (E2183), a row function as a value (E2134), a self-recursive row
function without a declared result (E2126), a computed key on a row (E2104).

This gate, on Apple Silicon:

* builds seed/tests/native-row-inference.kotoba with --compiler (the Mac fixed
  point of this tree) and the descriptor's packager and runs it: exit 0;
* checks that each refusal below is refused at check time with its named code;
* definition-cids: the hand-annotated twin is refused unbridged-source (the
  definition bridge carries no records) and the row module whole-module
  DSB:BRIDGE (exit 66), as for any template with specializations
  (docs/definition-cids-native.md), so no CID is observable for these forms;
* negative controls: one mutant full compiler per change, built from this
  tree's FULL-MANIFEST with that change removed, must refuse the corpus with
  the old code;
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
CORPUS = ROOT / "seed/tests/native-row-inference.kotoba"
CHECK = "seed/21-check.kotoba"
LOWER = "seed/30-lower.kotoba"
NS = "(ns d (:export [main]))\n(defrecord P [x :i64 y :i64])\n"
# (label, file, [(old, new)], expected: a refusal code string, or "run" (the built corpus must not exit 0))
MUTANTS = [
    ("no-row-refinement", CHECK, [
        ("        (= t TY-REC-BASE) true   ; JUN-733: a row (ck-row-gen?)\n", ""),
        ("                        (= t TY-REC-BASE) (ck-f2-set (ck-hint-set M f k t tn) f FN2-FLAGS (bit-or (ck-f2 M f FN2-FLAGS) 33))   ; JUN-733\n", "")],
     "E2104"),
    ("no-row-specialization", CHECK, [
        ("          (and (= (ck-callable M fi) 1) (ck-row-gen? M (ck-pick M fi (dec (nm-count M n))))) (ck-row-call M n (ck-pick M fi (dec (nm-count M n))) fx)   ; JUN-733\n", "")],
     "E2126"),
    ("no-caller-row", CHECK, [
        ("(ck-r6m-refine (ck-row-note M1 fi k ty) fi k (ck-r6m-fnsig-np M1 ty))", "(ck-r6m-refine M1 fi k (ck-r6m-fnsig-np M1 ty))")],
     "E2104"),
    ("no-get-default-on-record", CHECK, [
        ("          (and (ck-rec-ty? M1 (ck-ty M1)) (= (nm-kind M1 (nm-nth M1 n 2)) ND-KW))   ; JUN-733: a default on a record\n"
         "          (ck-rget-d M1 n (nm-nth M1 n 1) (nm-nth M1 n 2) (nm-nth M1 n 3) fx)\n", "")],
     "E2104"),
    ("no-keyword-default-on-record", CHECK, [
        ("          (ck-rec-ty? M1 (ck-ty M1)) (ck-rget-d M1 n r kw d fx)   ; JUN-733: a default on a record\n", "")],
     "E2103"),
]
REFUSALS = [
    ("non-record-argument", "(defn- f [m] (:a m))\n(defn main [] :i64 (f 5))", "E2104"),
    ("absent-field-without-default", "(defn- f [m] (:z m))\n(defn main [] :i64 (f {:a 1}))", "E2127"),
    ("exported-row-function", "(ns d (:export [main f]))\n(defn f [m] (:a m))\n(defn main [] :i64 (f {:a 1}))", "E2183"),
    ("row-function-as-a-value", "(defn- f [m] (:a m))\n(defn main [] :i64 (let [g f] 0))", "E2134"),
    ("computed-key-on-a-row", "(defn- f [m] (get m (if true :a :b) 0))\n(defn main [] :i64 (f {:a 1}))", "E2104"),
    ("recursive-row-without-result",
     "(defn- len [m] (if (> (:n m) 0) (+ 1 (len (assoc m :n (- (:n m) 1)))) 0))\n(defn main [] :i64 (len {:n 3}))", "E2126"),
    ("default-of-another-type", "(defn main [] :i64 (get {:a 1} :a \"s\"))", "E2104"),
    ("row-read-as-a-number", "(defn- f [m] (+ (:a m) m))\n(defn main [] :i64 (f {:a 1}))", "E2104"),
]
CIDS = {
    "row": "(ns a (:export [main]))\n(defrecord P [x :i64 y :i64])\n(defn- f [p] (:x p))\n"
           "(defn main [] :i64 (f (->P 1 2)))\n",
    "annotated": "(ns a (:export [main]))\n(defrecord P [x :i64 y :i64])\n(defn- f [p [:ref :a/P]] :i64 (:x p))\n"
                 "(defn main [] :i64 (f (->P 1 2)))\n",
}


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
        status, out, err = native(compiler, refusals, "check", name,
                                  (source if source.startswith("(ns") else NS + source) + "\n")
        if status == 0 or code not in out + err:
            raise ValueError(f"{name}: expected a check-time {code}, got exit {status}: {(out + err)[-300:]!r}")
        print(f"refused {name}: {code}", flush=True)

    ids = output / "cids"; ids.mkdir(mode=0o700)
    status, out, err = native(compiler, ids, "definition-cids", "annotated", CIDS["annotated"])
    if status != 0 or "SCANNED\t0/2" not in out or out.count("REFUSED:unbridged-source") != 2:
        raise ValueError(f"definition-cids annotated: expected both definitions REFUSED:unbridged-source, got exit "
                         f"{status}: {(out + err)[-300:]!r}")
    # a row generic is a template with specializations: whole-module DSB:BRIDGE (docs/definition-cids-native.md)
    status, out, err = native(compiler, ids, "definition-cids", "row", CIDS["row"])
    if status != 66 or out or not err.startswith("DSB:BRIDGE:"):
        raise ValueError(f"definition-cids row: expected exit 66 with DSB:BRIDGE, got exit {status}: {(out + err)[-300:]!r}")
    print("definition-cids: annotated twin unbridged-source; the row module is DSB:BRIDGE (templates/specializations)",
          flush=True)

    names = [line for line in (ROOT / "seed/FULL-MANIFEST").read_text().splitlines()
             if line and not line.startswith("#")]
    for label, path, edits, expected in MUTANTS:
        if path not in names:
            raise ValueError("FULL-MANIFEST no longer lists " + path)
        text = (ROOT / path).read_text()
        for old, new in edits:
            if text.count(old) != 1:
                raise ValueError(f"cannot construct the {label} negative control")
            text = text.replace(old, new)
        mutant = output / label; mutant.mkdir(mode=0o700)
        with (mutant / "full-unity.kotoba").open("w") as stream:
            for name in names:
                stream.write((text if name == path else (ROOT / name).read_text()) + "\n")
        mutant_compiler = scope.build(gate, compiler, packager, mutant, "full-unity",
                                      (mutant / "full-unity.kotoba").read_text())
        if gate.pin(mutant_compiler) == gate.pin(compiler):
            raise ValueError("mutant compiler is identical to the compiler under test: " + label)
        status, out, err = native(mutant_compiler, mutant, "check", "corpus", CORPUS.read_text())
        if expected == "run":
            if status != 0:
                raise ValueError(f"{label} mutant: expected the corpus admitted, got exit {status}: {(out + err)[-300:]!r}")
            built = scope.build(gate, mutant_compiler, packager, mutant, "corpus-run", CORPUS)
            run = subprocess.run([str(built)], cwd=mutant, capture_output=True, timeout=60,
                                 env={"PATH": "/usr/bin:/bin", "LANG": "C"})
            if run.returncode == 0:
                raise ValueError(f"{label} mutant: the corpus still exits 0")
            print(f"{label} (mutant compiler): corpus admitted, built and exits {run.returncode}", flush=True)
        else:
            if status == 0 or expected not in out + err:
                raise ValueError(f"{label} mutant: expected the corpus refused with {expected}, got exit {status}: "
                                 f"{(out + err)[-300:]!r}")
            print(f"{label} (mutant compiler): corpus refused with {expected}", flush=True)

    public = output / "public"; public.mkdir(mode=0o700)
    (public / "corpus.kotoba").write_bytes(CORPUS.read_bytes())
    result = subprocess.run([str(ROOT / "bin/amu"), "run", "corpus.kotoba"], cwd=public,
                            env={"PATH": "/usr/bin:/bin", "LANG": "C"},
                            capture_output=True, timeout=600)
    if result.returncode != 0 or result.stdout != b"0\n" or result.stderr:
        raise ValueError(f"bin/amu run: exit {result.returncode}, stdout {result.stdout!r}, "
                         f"stderr {result.stderr[-400:]!r}")
    print("bin/amu run corpus: 0", flush=True)
    print("PASS_NATIVE_ROW_INFERENCE_WITH_NEGATIVE_CONTROLS", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
