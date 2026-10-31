#!/usr/bin/env python3
"""Closed static dispatch in the native frontend (JUN-730).

lang/guest-grammar.edn, against the native checker as measured at amu 05668c77
(every form below was E2003 `unsupported top-level form`, reify E2101):

* :closed-multimethod -- (defmulti NAME DISPATCH) with every (defmethod NAME
  KEY [params] body ..) of the module is reader sugar, expanded by seed/20-names
  before any name is registered, into one module-local
  (defn NAME [params] (case (DISPATCH p ..) KEY body .. [:default body]));
  DISPATCH an unqualified symbol or a keyword, KEY an integer or keyword, all
  parameter vectors identical and plain, no hierarchy / prefer / extension;
* :protocol-dispatch / :protocol-extension -- an implementation of a
  defprotocol method for a record of the module (inline in defrecord, in
  extend-type or in extend-protocol) becomes a private defn whose receiver is
  typed [:ref R]; seed/21-check binds a call's receiver to a fresh local and calls
  the implementation for its static record type (ADR 0204: no runtime type
  test). Another receiver type is E2180;
* reify stays a permanent refusal (E2181). An extend-protocol `default`
  section is refused E2006 for now: its per-record specialization did not fit
  the x86 static profile's token table (MM-TOK-CAP 786432) next to the rest of
  FULL-MANIFEST.

This gate, on Apple Silicon:

* builds seed/tests/native-closed-dispatch.kotoba with --compiler (the Mac fixed
  point of this tree) and the descriptor's packager and runs it: exit 0; the
  surface-equivalence corpus pair (inline defrecord implementation vs
  extend-type) builds and answers 7 on both sides;
* checks every refusal below at check time with its named code;
* Definition CIDs (definition-cids, profile 6): the multimethod sugar prints the
  same CIDs as the hand-written case defn and the control differs; the protocol
  corpus pair is refused identically on both sides (REFUSED:unbridged-source:
  the definition bridge carries no records), so its CID equality is not
  observable;
* negative controls: one mutant full compiler per load-bearing change, built
  from this tree's FULL-MANIFEST with that change removed; each must refuse the
  corpus with the old code at the old place, or (`run`) build a corpus that
  does not exit 0, or (`reify`) not refuse reify with E2181;
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
CORPUS = ROOT / "seed/tests/native-closed-dispatch.kotoba"
NAMES = "seed/20-names.kotoba"
CHECK = "seed/21-check.kotoba"
NS = "(ns d (:export [main]))\n"
PROTO = ("(defprotocol Area (area [this]) (scale [this k]))\n(defrecord Sq [w :i64])\n"
         "(defrecord Rect [w :i64 h :i64])\n")
IMPL = "(extend-type Sq Area (area [this] (* (:w this) (:w this))) (scale [this k] (->Sq (* k (:w this)))))\n"
REIFY = NS + PROTO + IMPL + "(defn main [] :i64 (area (reify Area (area [this] 1) (scale [this k] this))))\n"
# lang/surface-equivalence-corpus.edn :protocol-dispatch (sugar, pure, control)
PAIR = {
    "protocol-sugar": "(ns d (:export [main]))\n(defprotocol Value (value [this]))\n"
                      "(defrecord Box [x] Value (value [this] (get this :x)))\n(defn main [] (value (->Box 7)))\n",
    "protocol-pure": "(ns d (:export [main]))\n(defprotocol Value (value [this]))\n(defrecord Box [x])\n"
                     "(extend-type Box Value (value [this] (get this :x)))\n(defn main [] (value (->Box 7)))\n",
    "protocol-control": "(ns d (:export [main]))\n(defprotocol Value (value [this]))\n"
                        "(defrecord Box [x] Value (value [this] (+ (get this :x) 1)))\n(defn main [] (value (->Box 7)))\n",
}
MM = NS + "(defn kind [x :i64] :i64 x)\n"
MM_MAIN = "(defn main [] :i64 (+ (render 2) (render 7)))\n"
CIDS = {
    "multimethod-sugar": MM + "(defmulti render kind)\n(defmethod render 1 [x :i64] (+ x 10))\n"
                         "(defmethod render 2 [x :i64] (+ x 20))\n(defmethod render :default [x :i64] 99)\n" + MM_MAIN,
    "multimethod-pure": MM + "(defn render [x :i64] (case (kind x) 1 (+ x 10) 2 (+ x 20) 99))\n" + MM_MAIN,
    "multimethod-control": MM + "(defn render [x :i64] (case (kind x) 1 (+ x 11) 2 (+ x 20) 99))\n" + MM_MAIN,
}
# (label, file, [(old, new)], expected: a refusal string, "run" (built corpus must not exit 0) or "reify")
MUTANTS = [
    ("no-dispatch-expansion", NAMES, [
        ("  (nm-run-defs (nm-dp-norm (nm-r6b-norm (nm-intern-nodes M S 1)))))",
         "  (nm-run-defs (nm-r6b-norm (nm-intern-nodes M S 1))))")],
     "E2003 unsupported top-level form 'defmethod'"),
    ("no-protocol-call", CHECK, [
        ("          (ck-pr-head? M n) (ck-pr-call M n fx ctx)   ; JUN-730: a protocol method\n", "")],
     "E2101 unknown or unsupported form 'area'"),
    ("no-receiver-local", CHECK, [
        ("          (ck-pr-wrap? M n) (ck-ds-walk (ck-pr-wrap M n) S n)   ; JUN-730: a protocol call's receiver is a fresh local\n",
         "")],
     "E2180 no static implementation of protocol method 'area'"),
    ("dispatch-ignores-record", CHECK, [
        ("                   (or (zero? blk) (= (nm-sf M (nm-sym-of M (nm-nth M (nm-nth M (nm-nth M d 2) 1) 1)) SF-REC) blk)))",
         "                   true)")],
     "E2104 type mismatch"),
    ("multimethod-drops-default", NAMES, [
        ("    (let [M1 (if (zero? prev) M (nm-set-nf M prev NF-NEXT dflt))",
         "    (let [M1 (if (zero? prev) M (nm-set-nf M prev NF-NEXT 0))")],
     "run"),
    ("no-reify-refusal", CHECK, [
        ("          (= (nm-sf M s SF-HASH) -3568532113232994950) (ck-err M E-CHECK-REIFY h 0)   ; JUN-730: reify (FNV-1a)\n",
         "")],
     "reify"),
]
P = PROTO
REFUSALS = [
    # closed multimethods
    ("defmethod-without-defmulti", "(defmethod f 1 [x] x)\n(defn main [] :i64 0)", "E2007 closed dispatch: 'f'"),
    ("string-key", "(defmulti f identity)\n(defmethod f \"x\" [x] x)\n(defn main [] :i64 0)", "E2006"),
    ("different-parameters",
     "(defn k [x] x)\n(defmulti f k)\n(defmethod f 1 [x] x)\n(defmethod f 2 [y] y)\n(defn main [] :i64 (f 1))", "E2006"),
    ("pattern-parameter", "(defn k [x] x)\n(defmulti f k)\n(defmethod f 1 [[a b]] a)\n(defn main [] :i64 0)", "E2006"),
    ("two-defaults",
     "(defn k [x] x)\n(defmulti f k)\n(defmethod f :default [x] x)\n(defmethod f :default [x] 1)\n(defn main [] :i64 0)",
     "E2006 malformed closed dispatch form ':default'"),
    ("duplicate-key",
     "(defn k [x] x)\n(defmulti f k)\n(defmethod f 1 [x] x)\n(defmethod f 1 [x] 2)\n(defn main [] :i64 (f 1))", "E2125"),
    ("fn-literal-dispatch", "(defmulti f (fn [x] x))\n(defmethod f 1 [x] x)\n(defn main [] :i64 0)", "E2006"),
    ("no-defmethod", "(defmulti f :k)\n(defn main [] :i64 0)", "E2006"),
    ("dispatch-options", "(defmulti f :k :default :other)\n(defmethod f 1 [x] x)\n(defn main [] :i64 0)", "E2006"),
    ("duplicate-defmulti", "(defmulti f :k)\n(defmulti f :k)\n(defmethod f 1 [x] x)\n(defn main [] :i64 0)", "E2001"),
    ("defmulti-and-defn", "(defn f [x] x)\n(defmulti f :k)\n(defmethod f 1 [x] x)\n(defn main [] :i64 0)", "E2001"),
    ("empty-method-body", "(defn k [x] x)\n(defmulti f k)\n(defmethod f 1 [x])\n(defn main [] :i64 0)", "E2006"),
    # protocols
    ("extend-undeclared-protocol", P + "(extend-type Sq Perimeter (area [this] 1))\n(defn main [] :i64 0)",
     "E2007 closed dispatch: 'Perimeter'"),
    ("extend-foreign-type", P + "(extend-type String Area (area [this] 1) (scale [this k] this))\n(defn main [] :i64 0)",
     "E2007 closed dispatch: 'String'"),
    ("extend-protocol-foreign-type",
     P + "(extend-protocol Area String (area [this] 1) (scale [this k] this))\n(defn main [] :i64 0)",
     "E2007 closed dispatch: 'String'"),
    ("extend-protocol-undeclared", P + "(extend-protocol Perimeter Sq (area [this] 1))\n(defn main [] :i64 0)",
     "E2007 closed dispatch: 'Perimeter'"),
    ("defrecord-undeclared-protocol", "(defrecord Sq [w] Area (area [this] 1))\n(defn main [] :i64 0)",
     "E2007 closed dispatch: 'Area'"),
    ("defrecord-object", "(defprotocol Area (area [this]))\n(defrecord Sq [w] Object (toString [this] 1))\n"
                         "(defn main [] :i64 0)", "E2007 closed dispatch: 'Object'"),
    ("missing-method", P + "(extend-type Sq Area (area [this] 1))\n(defn main [] :i64 0)",
     "E2006 malformed closed dispatch form 'Area'"),
    ("unknown-method", P + "(extend-type Sq Area (area [this] 1) (scale [this k] this) (perim [this] 2))\n"
                           "(defn main [] :i64 0)", "E2006 malformed closed dispatch form 'perim'"),
    ("wrong-arity", P + "(extend-type Sq Area (area [this x] 1) (scale [this k] this))\n(defn main [] :i64 0)",
     "E2006 malformed closed dispatch form 'area'"),
    ("implemented-twice", P + IMPL + "(extend-type Sq Area (area [this] 1) (scale [this k] this))\n(defn main [] :i64 0)",
     "E2006 malformed closed dispatch form 'area'"),
    ("method-twice-in-section", P + "(extend-type Sq Area (area [this] 1) (area [this] 2) (scale [this k] this))\n"
                                    "(defn main [] :i64 0)", "E2006 malformed closed dispatch form 'area'"),
    ("typed-receiver", P + "(extend-type Sq Area (area [this [:ref :d/Sq]] 1) (scale [this k] this))\n"
                           "(defn main [] :i64 0)", "E2006 malformed closed dispatch form 'area'"),
    ("method-also-defined", P + "(defn area [x] x)\n(defn main [] :i64 0)", "E2001 duplicate definition 'area'"),
    ("method-named-like-a-head", "(defprotocol C (count [this]))\n(defn main [] :i64 0)",
     "E2006 malformed closed dispatch form 'count'"),
    ("multi-arity-signature", "(defprotocol C (m [this] [this x]))\n(defn main [] :i64 0)", "E2006"),
    ("signature-docstring", "(defprotocol C (m [this] \"doc\"))\n(defn main [] :i64 0)",
     "E2006 malformed closed dispatch form 'm'"),
    ("extend-protocol-default", P + "(extend-protocol Area default (area [this] 1) (scale [this k] this))\n"
                                    "(defn main [] :i64 0)", "E2006 malformed closed dispatch form 'default'"),
    ("receiver-not-a-record", P + IMPL + "(defn main [] :i64 (area 5))",
     "E2180 no static implementation of protocol method 'area'"),
    ("record-without-implementation", P + IMPL + "(defn main [] :i64 (area (->Rect 1 2)))",
     "E2180 no static implementation of protocol method 'area'"),
    ("no-receiver", P + IMPL + "(defn main [] :i64 (area))", "E2180"),
    ("reify", PROTO + IMPL + "(defn main [] :i64 (area (reify Area (area [this] 1) (scale [this k] this))))",
     "E2181 reify is not admitted"),
    ("reify-empty", "(defn main [] :i64 (let [o (reify)] 0))", "E2181"),
    ("definterface", "(definterface I (m []))\n(defn main [] :i64 0)", "E2003 unsupported top-level form 'definterface'"),
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


def build_run(scope, gate, compiler, packager, directory, name, source):
    path = directory / f"{name}.kotoba"
    path.write_text(source)
    image = scope.build(gate, compiler, packager, directory, name, path)
    run = subprocess.run([str(image)], cwd=directory, capture_output=True, timeout=60,
                         env={"PATH": "/usr/bin:/bin", "LANG": "C"})
    return run.returncode


def cids(compiler, directory, name, source):
    status, out, err = native(compiler, directory, "definition-cids", name, source)
    if status != 0:
        raise ValueError(f"definition-cids {name}: exit {status}: {(out + err)[-300:]!r}")
    return out


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
    for name in ("protocol-sugar", "protocol-pure"):
        status = build_run(scope, gate, compiler, packager, fixed, name, PAIR[name])
        if status != 7:
            raise ValueError(f"{name}: expected exit 7, got {status}")
        print(f"fixed compiler: {name} exit 7", flush=True)

    refusals = output / "refusals"; refusals.mkdir(mode=0o700)
    for name, source, code in REFUSALS:
        status, out, err = native(compiler, refusals, "check", name, NS + source + "\n")
        if status == 0 or code not in out + err:
            raise ValueError(f"{name}: expected a check-time {code}, got exit {status}: {(out + err)[-300:]!r}")
        print(f"refused {name}: {code}", flush=True)

    ids = output / "cids"; ids.mkdir(mode=0o700)
    sugar, pure, control = (cids(compiler, ids, k, CIDS[k])
                            for k in ("multimethod-sugar", "multimethod-pure", "multimethod-control"))
    if sugar != pure or "REFUSED" in sugar or "SCANNED\t3/3" not in sugar:
        raise ValueError(f"multimethod sugar and pure CIDs differ:\n{sugar}\n{pure}")
    if control == sugar:
        raise ValueError("multimethod control has the sugar's CIDs")
    print("definition-cids: multimethod sugar = hand-written case defn; control differs", flush=True)
    reports = {k: cids(compiler, ids, k, v) for k, v in PAIR.items()}
    for report in reports.values():
        if "SCANNED\t0/2" not in report or report.count("REFUSED:unbridged-source") != 2:
            raise ValueError(f"protocol pair: expected both definitions REFUSED:unbridged-source:\n{report}")
    if reports["protocol-sugar"] != reports["protocol-pure"]:
        raise ValueError("protocol pair: the refusal reports differ")
    print("definition-cids: protocol pair refused identically (unbridged-source; records have no bridge)", flush=True)

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
        if expected == "reify":
            status, out, err = native(mutant_compiler, mutant, "check", "reify", REIFY)
            if status == 0 or "E2181" in out + err:
                raise ValueError(f"{label} mutant: reify is still refused E2181 (or admitted): {(out + err)[-300:]!r}")
            print(f"{label} (mutant compiler): reify is not refused E2181 ({(out + err).strip()[-120:]})", flush=True)
        elif expected == "run":
            status, out, err = native(mutant_compiler, mutant, "check", "corpus", CORPUS.read_text())
            if status != 0:
                raise ValueError(f"{label} mutant: expected the corpus admitted, got exit {status}: {(out + err)[-300:]!r}")
            status = build_run(scope, gate, mutant_compiler, packager, mutant, "corpus-run", CORPUS.read_text())
            if status == 0:
                raise ValueError(f"{label} mutant: the corpus still exits 0")
            print(f"{label} (mutant compiler): corpus admitted, built and exits {status}", flush=True)
        else:
            status, out, err = native(mutant_compiler, mutant, "check", "corpus", CORPUS.read_text())
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
    print("PASS_NATIVE_CLOSED_DISPATCH_WITH_NEGATIVE_CONTROLS", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
