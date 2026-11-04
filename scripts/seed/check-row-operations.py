#!/usr/bin/env python3
"""Row operations on native records (JUN-733 slice 2).

Owner decision 2026-11-01 (Linear JUN-733): native Amu follows the amu ladder's
row floors (docs/language-ladder.edn :row-operations, :empty-map-literal,
:record-field-update, :merge-literal-reads-its-row). In seed/21-check every
result is a record type of the shape the operation gives, by structural
identity (ck-shape-type): the one declared record of exactly that shape, else
the anonymous record of that shape (its keys in printed-text order, ck-krank):

* (assoc r :k v) with :k not a field of r extends the row (ck-assoc-ext; the
  value is typed as in a literal: nil / some at a key the module writes nil at);
* (assoc {} :k v) and (merge {} m): {} is the empty record there (ck-empty-rec);
  anywhere else it stays E2133;
* (dissoc r :k ..) and (select-keys r [:k ..]) shrink the row (ck-shrink; a key
  the record does not have is ignored, as clojure.core does);
* (merge a b ..) is the record with a's fields and b's, b's value and type
  winning (ck-merge), folded left;
* (update m :k f x ..) is reader sugar: (let [g m] (assoc g :k (f (:k g) x ..))),
  a fn literal f applied as a let (ck-rowop-ds).

30-lower builds each result field from the source record's field of the same key
(lw-assoc / lw-rebuild / lw-merge, lw-src).

This gate, on Apple Silicon:

* builds seed/tests/native-row-operations.kotoba with --compiler (the Mac fixed
  point of this tree) and the descriptor's packager and runs it: exit 0;
* checks that each refusal below is refused at check time with its named code;
* definition-cids: the update sugar and its hand-written let/assoc form are
  refused identically (unbridged-source: the definition bridge carries no
  records), so CID equality is not observable for these forms;
* negative controls: one mutant full compiler per change, built from this
  tree's FULL-MANIFEST with that change removed; the checker mutants must refuse
  the corpus with the old code, the lowering mutants must build a corpus that
  does not exit 0;
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
CORPUS = ROOT / "seed/tests/native-row-operations.kotoba"
CHECK = "seed/21-check.kotoba"
LOWER = "seed/30-lower.kotoba"
NS = "(ns d (:export [main]))\n(defrecord P [x :i64 y :i64])\n"
# (label, file, [(old, new)], expected: a refusal code string, or "run" (the built corpus must not exit 0))
MUTANTS = [
    ("no-row-extension", CHECK, [
        ("          (ck-assoc-ext? M r kw) (ck-assoc-ext M n fx)   ; JUN-733: a key r does not have extends the row\n", "")],
     "E2127"),
    ("no-empty-record", CHECK, [
        ("  (if (and (= (nm-kind M r) ND-MAP) (zero? (nm-count M r))) (ck-kwrec M r fx) M))", "  M)")],
     "E2133"),
    ("no-record-dissoc", CHECK, [
        ("        (= hd HD-DISSOC) (ck-dissoc M n fx ctx)   ; JUN-733: a record's dissoc shrinks the row\n", "")],
     "E2104"),
    ("no-select-keys", CHECK, [
        ("          (= (nm-sf M s SF-HASH) 5227267513227667492) (ck-selkeys M n fx)   ; JUN-733: select-keys (FNV-1a)\n", "")],
     "E2101 unknown or unsupported form 'select-keys'"),
    ("no-merge", CHECK, [
        ("          (= (nm-sf M s SF-HASH) 5641795132494944871) (ck-merge M n fx)   ; JUN-733: merge (FNV-1a)\n", "")],
     "E2101 unknown or unsupported form 'merge'"),
    ("no-variadic-merge", CHECK, [
        ("(>= (nm-count M n) 4)) 1   ; merge", "(>= (nm-count M n) 4)) 0   ; merge")],
     "E2103 wrong number of arguments to 'merge'"),
    ("no-update-sugar", CHECK, [
        ("(ck-fn-form? M f)))) 2   ; update", "(ck-fn-form? M f)))) 0   ; update")],
     "E2139"),   # the first refusal is a fn literal update would have applied as a let
    ("assoc-copies-by-position", LOWER, [
        ("(lw-seconds (+ t i) (lw-src M (:a q) (:b q) i))", "(lw-seconds (+ t i) i)")],
     "run"),
    ("rebuild-copies-by-position", LOWER, [
        ("(recur (-> M3 (lw-emit OP-LGET (+ t j) s) (lw-seconds (+ t j) (lw-src M3 a b j))) (inc j))",
         "(recur (-> M3 (lw-emit OP-LGET (+ t j) s) (lw-seconds (+ t j) j)) (inc j))")],
     "run"),
    ("merge-ignores-b", LOWER, [
        ("                 (recur (if (neg? ic)\n", "                 (recur (if true\n")],
     "run"),
]
REFUSALS = [
    ("empty-literal-alone", "(defn main [] :i64 (let [m {}] 0))", "E2133"),
    ("dissoc-then-read", "(defn main [] :i64 (:a (dissoc {:a 1 :b 2} :a)))", "E2127"),
    ("dissoc-computed-key", "(defn main [] :i64 (let [k :a m (dissoc {:a 1} k)] 0))", "E2127"),
    ("select-keys-not-a-vector", "(defn main [] :i64 (let [m (select-keys {:a 1} :a)] 0))", "E2103"),
    ("select-keys-of-a-number", "(defn main [] :i64 (let [m (select-keys 5 [:a])] 0))", "E2104"),
    ("merge-a-number", "(defn main [] :i64 (let [m (merge 1 {:a 1})] 0))", "E2104"),
    ("merge-a-typed-map", "(defn main [] :i64 (let [m (merge {:a 1} (typed-map-new [:map :keyword :i64] :b 2))] 0))", "E2104"),
    ("update-answers-another-type", "(defn main [] :i64 (:a (update {:a 1} :a (fn [x] \"s\"))))", "E2104"),
    ("update-absent-key", "(defn main [] :i64 (:z (update {:a 1} :z inc)))", "E2127"),
    ("update-fn-arity", "(defn main [] :i64 (let [m (update {:a 1} :a (fn [x y] x))] 0))", "E2103"),
    ("update-a-number", "(defn main [] :i64 (let [m (update 5 :a inc)] 0))", "E2104"),
    ("assoc-new-key-nil-without-type", "(defn main [] :i64 (let [m (assoc {:a 1} :b nil)] 0))", "E2182"),
    ("assoc-new-key-fn-value", "(defn main [] :i64 (let [m (assoc {:a 1} :b (fn [x] x))] 0))", "E2128"),
    ("assoc-past-32-fields",
     "(defn main [] :i64 (let [m (assoc {" + " ".join(f":k{i} {i}" for i in range(32)) + "} :z 1)] 0))", "E2128"),
]
CIDS = {
    "update-sugar": "(ns a (:export [main]))\n(defrecord P [x :i64 y :i64])\n"
                    "(defn f [p [:ref :a/P]] [:ref :a/P] (update p :x inc))\n(defn main [] :i64 (:x (f (->P 1 2))))\n",
    "update-pure": "(ns a (:export [main]))\n(defrecord P [x :i64 y :i64])\n"
                   "(defn f [p [:ref :a/P]] [:ref :a/P] (let [g p] (assoc g :x (inc (:x g)))))\n"
                   "(defn main [] :i64 (:x (f (->P 1 2))))\n",
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
        # JUN-358 (#1788/#1789): a source holding a form with no bridge (records) refuses atomically, exit 66 DSB:BRIDGE:3:<offset>,
        # instead of per-definition REFUSED:unbridged-source (docs/definition-cids-native.md; check-checked-source-native.py).
        if status != 66 or out or not err.startswith("DSB:BRIDGE:3:"):
            raise ValueError(f"definition-cids {name}: expected the atomic DSB:BRIDGE:3 refusal, got exit "
                             f"{status}: {(out + err)[-300:]!r}")
        reports[name] = err.split(":")[:3]
    if reports["update-sugar"] != reports["update-pure"]:
        raise ValueError("definition-cids: the update sugar and pure refusals differ in kind")
    print("definition-cids: update sugar and its let/assoc form both refuse atomically (DSB:BRIDGE:3; records have no bridge)",
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
    print("PASS_NATIVE_ROW_OPERATIONS_WITH_NEGATIVE_CONTROLS", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
