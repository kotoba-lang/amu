#!/usr/bin/env python3
"""Keyword map literals have structural identity; nil is an [:option T] field's none (JUN-733 slice 1).

Owner decision 2026-11-01 (Linear JUN-733): native Amu follows the amu ladder's
row floors (docs/language-ladder.edn :absence, :absent-field-from-assoc,
:row-unification, :literal-typing; kotoba-lang lang/guest-grammar.edn
:map-literal :value-types :keyword-keys). In seed/21-check:

* D1 structural identity -- a keyword map literal whose keys and value types fit
  exactly one declared record (defrecord, ns :schemas or an inline [:record ..]
  schema) is that record (ck-kwrec-decl); a literal checked where a record is
  expected -- a call argument, a record field, an assoc value, a typed slot --
  with exactly that record's keys is that record (ck-expr-to / ck-kwrec-in), so
  two declared records of one shape are each reached by their own slot. Such a
  literal builds the record in the record's field order;
* D4 nil -- nil at a keyword key of a map literal, an assoc pair or a
  record-new / constructor argument is the none of an [:option T] field; T is
  the declared field's, else the one type the module spells at that key
  (ck-kopt-scan: literals, constructors, calls of defns with a declared result,
  declared [:option T] fields of that key); a non-nil value T at such a key is
  its some (30-lower lw-some: pair(x, 0)). nil with no T is E2182, two Ts E2128.

This gate, on Apple Silicon:

* builds seed/tests/native-record-identity-option.kotoba with --compiler (the
  Mac fixed point of this tree) and the descriptor's packager and runs it:
  exit 0;
* checks that each refusal below is refused at check time with its named code;
* definition-cids: a literal and the hand-written constructor in a [:ref P]
  slot are refused identically (unbridged-source: the definition bridge carries
  no records), so CID equality is not observable for these forms;
* negative controls: one mutant full compiler per change, built from this
  tree's FULL-MANIFEST with that change removed; the checker mutants must refuse
  the corpus with the old code, the lowering mutant (no some) must build a
  corpus that does not exit 0;
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
CORPUS = ROOT / "seed/tests/native-record-identity-option.kotoba"
CHECK = "seed/21-check.kotoba"
LOWER = "seed/30-lower.kotoba"
NS = ("(ns d (:export [main]))\n(defrecord P [x :i64 y :i64])\n"
      "(defn sum-p [p [:ref :d/P]] :i64 (+ (:x p) (:y p)))\n")
# (label, file, [(old, new)], expected: a refusal code string, or "run" (the built corpus must not exit 0))
MUTANTS = [
    ("no-structural-identity", CHECK, [
        ("  (let [d (ck-kwrec-decl M n)\n", "  (let [d 0\n")],
     "E2121"),
    ("no-expected-record", CHECK, [
        ("      (ck-kwrec-in M c fx b)\n      (ck-expr M c fx 0))))", "      (ck-expr M c fx 0)\n      (ck-expr M c fx 0))))")],
     "E2104"),
    ("no-nil-option", CHECK, [
        ("(defn- ck-nil? [M :vector-i64 v :i64] :bool (and (nm-r6b-nil? M v) (neg? (nm-local-slot M (nm-sym-of M v)))))",
         "(defn- ck-nil? [M :vector-i64 v :i64] :bool false)")],
     "E2102 unknown symbol 'nil'"),
    ("no-module-option-key", CHECK, [
        ("        M3 (ck-kopt-scan (ck-hints-apply (ck-sigs M2 1)))", "        M3 (ck-hints-apply (ck-sigs M2 1))")],
     "E2182"),
    ("no-some-lowering", LOWER, [
        ("  (if (or (zero? vty) (= fty vty)) M (-> M", "  (if true M (-> M")],
     "run"),
]
REFUSALS = [
    ("nil-no-type", "(defn main [] :i64 (let [a {:zz nil}] 0))", "E2182"),
    ("nil-two-types", "(defn main [] :i64 (let [a {:zz nil} b {:zz 1} c {:zz \"s\"}] 0))", "E2128"),
    ("value-not-the-key-type", "(defn main [] :i64 (let [a {:q nil} b {:q 1} s \"x\" c {:q s}] 0))", "E2104"),
    ("nil-into-plain-field", "(defn main [] :i64 (:x (assoc (->P 1 2) :x nil)))", "E2104"),
    ("nil-into-plain-constructor-field", "(defn main [] :i64 (:x (->P nil 2)))", "E2102"),
    ("nil-as-a-value", "(defn main [] :i64 (let [x nil] 0))", "E2102"),
    ("literal-extra-key", "(defn main [] :i64 (sum-p {:x 1 :z 2}))", "E2104"),
    ("literal-field-type", "(defn main [] :i64 (sum-p {:x 1 :y \"s\"}))", "E2104"),
    ("literal-missing-key", "(defn main [] :i64 (sum-p {:x 1}))", "E2104"),
    ("two-records-one-shape-let-bound",
     "(defrecord A [x :i64 y :i64])\n(defn main [] :i64 (let [m {:x 1 :y 2}] (sum-p m)))", "E2104"),
]
CIDS = {
    "literal": "(ns a (:export [main]))\n(defrecord P [x :i64 y :i64])\n(defn f [p [:ref :a/P]] :i64 (:x p))\n"
               "(defn main [] :i64 (f {:x 1 :y 2}))\n",
    "constructor": "(ns a (:export [main]))\n(defrecord P [x :i64 y :i64])\n(defn f [p [:ref :a/P]] :i64 (:x p))\n"
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
        status, out, err = native(compiler, refusals, "check", name, NS + source + "\n")
        if status == 0 or code not in out + err:
            raise ValueError(f"{name}: expected a check-time {code}, got exit {status}: {(out + err)[-300:]!r}")
        print(f"refused {name}: {code}", flush=True)

    ids = output / "cids"; ids.mkdir(mode=0o700)
    reports = {}
    for name, source in CIDS.items():
        status, out, err = native(compiler, ids, "definition-cids", name, source)
        if status != 0 or "SCANNED\t0/2" not in out or out.count("REFUSED:unbridged-source") != 2:
            raise ValueError(f"definition-cids {name}: expected both definitions REFUSED:unbridged-source, got exit "
                             f"{status}: {(out + err)[-300:]!r}")
        reports[name] = out
    if reports["literal"] != reports["constructor"]:
        raise ValueError("definition-cids: the literal and constructor reports differ")
    print("definition-cids: literal and constructor refused identically (unbridged-source; records have no bridge)",
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
    print("PASS_NATIVE_RECORD_IDENTITY_OPTION_WITH_NEGATIVE_CONTROLS", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
