#!/usr/bin/env python3
"""Small native admissions in seed/21-check and seed/30-lower (JUN-734).

lang/guest-grammar.edn, against the native checker as measured at amu c2186d76:

* D5 :def :value :literal -- a def of a vector / map literal with f64 or boolean
  values, or of map-literal items, was E2124. It now takes R6F's computed-def
  route (a private nullary defn whose body is the literal, typed as in a body);
  R0's integer vectors and R6B's opaque constant maps are unchanged;
* D6 -- the variadic (assoc r k1 v1 k2 v2 ..) was E2103. It is now reader sugar
  for (assoc (assoc r k1 v1) k2 v2 ..) on records, typed maps and documents; an
  odd key/value count stays E2103;
* D10 -- (get m k) on a typed map was E2104; it is now [:option V] (:def :value
  :quoted-not-widened: lookup is get on the typed map, [:option V], or V with a
  default), lowered as typed-map-get. (:k m d) on a typed map was E2103; it is
  now (get m :k d). On a record a default is refused E2103 (a field is never
  absent). A defrecord's bare name as a parameter type ([s S]) silently read S
  as a second parameter; it is now refused E2105 (a type is a keyword or a type
  vector; the record type is [:ref :<ns>/S]).

This gate, on Apple Silicon:

* builds seed/tests/native-def-assoc-get.kotoba with --compiler (the Mac fixed
  point of this tree) and the descriptor's packager and runs it: exit 0;
* checks that each refusal below is refused at check time with its named code;
* negative controls: one mutant full compiler per change, built from this
  tree's FULL-MANIFEST with that change removed: the four checker mutants must
  refuse the corpus with the old code at the old place, the lowering mutant
  (21-check admits (get m k) but 30-lower reads it as a record field) must build
  a corpus that does not exit 0, and the mutant without the bare-record-name
  refusal must not refuse [s S] with E2105;
* runs the corpus through the public CLI (bin/amu run), which must print 0.

Definition CIDs are not observable for these forms: the definition bridge
refuses computed defs (DSB:BRIDGE, as for (def x (+ 1 2)) before this change)
and unbridged record / typed-map sources, on both the sugar and the pure side.

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
CORPUS = ROOT / "seed/tests/native-def-assoc-get.kotoba"
CHECK = "seed/21-check.kotoba"
LOWER = "seed/30-lower.kotoba"
NS = "(ns d (:export [main]))\n(defrecord S [a :i64 b :i64])\n"
BARE = NS + "(defn f [s S] :i64 (:a s))\n(defn main [] :i64 (f (->S 1 2)))\n"
# (label, file, [(old, new)], expected: a refusal code string, "run" (built corpus must not exit 0) or "bare")
MUTANTS = [
    ("no-def-literal", CHECK, [
        ("             (and (= k ND-VEC) (zero? (ck-def-vec M v)))\n"
         "             (and (= k ND-MAP) (not (ck-r6b-const? M v)))))))",
         "             false))))")],
     "E2124 def value must be an integer, string, keyword or vector literal: 'cfg'"),
    ("no-variadic-assoc", CHECK, [
        ("          (ck-vassoc? M n) (ck-ds-walk (ck-vassoc M n) S n)   ; JUN-734: variadic assoc\n", "")],
     "E2103 wrong number of arguments to 'assoc'"),
    ("no-get-option", CHECK, [
        ("          (= (ck-tcon M1 (ck-ty M1)) TC-MAP) (ck-gget2 M1 n fx)   ; JUN-734\n", "")],
     "E2104 type mismatch in 'get'"),
    ("no-kw-default", CHECK, [
        ("          (= (nm-count M n) 3) (ck-kwget3 M n fx)   ; JUN-734\n", "")],
     "E2103 wrong number of arguments to ':q'"),
    ("no-get-option-lowering", LOWER, [
        ("                   (= (lw-ct M (lw-nf M a NF-TYPE) CT-CTOR) TC-MAP)   ; JUN-734: (get m k) on a map -> [:option V]\n"
         "                   (lw-mget M a (lw-nf M h NF-TYPE) (lw-md M (lw-nf M a NF-TYPE)) t)\n", "")],
     "run"),
    ("no-bare-record-refusal", CHECK, [
        ("          (pos? (nm-sf M (nm-sym-of M c) SF-REC)) (ck-err M E-CHECK-TYPENAME c 0)\n", "")],
     "bare"),
]
REFUSALS = [
    ("def-loop", "(def x [(loop [i 0] (if (> i 3) i (recur (+ i 1))))])\n(defn main [] :i64 0)", "E2124"),
    ("def-fn-literal", "(def x {:a (fn [y] y)})\n(defn main [] :i64 0)", "E2124"),
    ("def-mixed-vector", "(def x [1 :a])\n(defn main [] :i64 0)", "E2116"),
    ("def-unknown-symbol", "(def x {:a 0.5 :b nope})\n(defn main [] :i64 0)", "E2102"),
    ("assoc-odd", "(defn main [] :i64 (let [s (->S 1 2)] (:a (assoc s :a 1 :b))))", "E2103"),
    ("assoc-absent-field", "(defn main [] :i64 (let [s (->S 1 2)] (:a (assoc s :a 1 :z 2))))", "E2127"),
    ("assoc-field-type", "(defn main [] :i64 (let [s (->S 1 2)] (:a (assoc s :a 1 :b \"x\"))))", "E2104"),
    ("assoc-map-value-type",
     "(defn main [] :i64 (let [m (typed-map-new [:map :keyword :i64] :a 1)] (get (assoc m :a 1 :b true) :a 0)))", "E2104"),
    ("get-key-type",
     "(defn main [] :i64 (let [m (typed-map-new [:map :keyword :i64] :a 1)] (option-or (get m \"a\") 0)))", "E2104"),
    ("get-is-option", "(defn main [] :i64 (let [m (typed-map-new [:map :keyword :i64] :a 1)] (get m :a)))", "E2121"),
    ("kw-default-type", "(defn main [] :i64 (let [m (typed-map-new [:map :keyword :i64] :a 1)] (:a m \"d\")))", "E2104"),
    ("kw-default-record", "(defn main [] :i64 (let [s (->S 1 2)] (:a s 0)))", "E2103"),
    ("kw-default-map-literal-record", "(defn main [] :i64 (let [s {:a 1 :b true}] (:a s 0)))", "E2103"),
    ("kw-default-vector", "(defn main [] :i64 (let [v [1 2]] (:a v 0)))", "E2103"),
    ("bare-record-type", "(defn f [s S] :i64 (:a s))\n(defn main [] :i64 (f (->S 1 2)))", "E2105 unsupported type 'S'"),
    ("bare-record-param", "(defn f [S] :i64 0)\n(defn main [] :i64 (f 1))", "E2105 unsupported type 'S'"),
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
        if expected == "bare":
            status, out, err = native(mutant_compiler, mutant, "check", "bare", BARE)
            if status != 0 and "E2105" in out + err:
                raise ValueError(f"{label} mutant: [s S] is still refused with E2105: {(out + err)[-300:]!r}")
            print(f"{label} (mutant compiler): [s S] is not refused E2105 (exit {status}: "
                  f"{(out + err).strip()[-120:]})", flush=True)
        elif expected == "run":
            status, out, err = native(mutant_compiler, mutant, "check", "corpus", CORPUS.read_text())
            if status != 0:
                raise ValueError(f"{label} mutant: expected the corpus admitted, got exit {status}: {(out + err)[-300:]!r}")
            built = scope.build(gate, mutant_compiler, packager, mutant, "corpus-run", CORPUS)
            run = subprocess.run([str(built)], cwd=mutant, capture_output=True, timeout=60,
                                 env={"PATH": "/usr/bin:/bin", "LANG": "C"})
            if run.returncode == 0:
                raise ValueError(f"{label} mutant: the corpus still exits 0")
            print(f"{label} (mutant compiler): corpus admitted, built and exits {run.returncode}", flush=True)
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
    print("PASS_NATIVE_DEF_ASSOC_GET_WITH_NEGATIVE_CONTROLS", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
