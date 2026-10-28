#!/usr/bin/env python3
"""Stage source/KIR fixtures; checking, normalization and CIDs run natively.

This observer is not a semantic compiler, cache admission or whole-compiler
qualification. Original KIR identity/SCC/object gates remain independent.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import platform
import struct
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = "seed/05-checked-source.kotoba"
EXTRA = ["seed/04-definition-cid.kotoba", "seed/05-definition-graph.kotoba",
         "seed/05-checked-definition.kotoba", "seed/06-definition-groups.kotoba", BRIDGE,
         "seed/05-source-loops.kotoba"]
ENTRY = '''
(defn- seed-main [] :i64
 (cond (and (= (io-argc) 2) (= (io-arg 0) "kir")) (dsb-source (io-fs2-text 65 (io-arg 1) "") true)
       (and (= (io-argc) 2) (= (io-arg 0) "reference")) (dcs-run (io-fs2-text 65 (io-arg 1) ""))
       (= (io-argc) 1) (dsb-source (io-fs2-text 65 (io-arg 0) "") false)
       :else 2))
'''


def pin(path):
    data = Path(path).read_bytes()
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def function(name, body, params="x", types=":i64", result=":i64"):
    return ("{:name " + name + " :params [" + params + "] :param-types [" + types +
            "] :result " + result + " :effects #{} :body " + body + "}")


def module(functions):
    return "{:format :kotoba.kir/v4 :entry nil :exports [] :effects #{} :functions [" + " ".join(functions) + "]}\n"



def execution_cases():
    return {
        "loop": ("(defn work [x :i64] :i64 (loop [i x] (if (= i 0) 7 (recur (dec i)))))", "(work 4)", 7),
        "captures": ("(defn work [z :i64 a :i64] :i64 (loop [i z] (if (= i 0) (+ z a) (recur (dec i)))))", "(work 4 9)", 13),
        "shadow": ("(defn work [x :i64] :i64 (loop [i 0] (if (< i 1) (let [x i] (recur (inc x))) x)))", "(work 9)", 9),
        "nested": ("(defn work [x :i64] :i64 (loop [i x] (if (= i 0) (loop [j 2] (if (= j 0) 11 (recur (dec j)))) (recur (dec i)))))", "(work 3)", 11),
        "string-capture": ("(defn work [s :string x :i64] :i64 (loop [i x] (if (= i 0) (string-length s) (recur (dec i)))))", '(work "hello" 3)', 5),
        "string-result": ("(defn work [s :string x :i64] :string (loop [i x] (if (= i 0) s (recur (dec i)))))", '(string-length (work "hello" 3))', 5),
    }


def loop_boundary(captures):
    ps = [f"p{i}" for i in range(captures)]
    variables = [f"i{i}" for i in range(20)]
    call_args = "(- i0 1) " + " ".join(variables[1:])
    tail = " ".join(ps) + " p2"
    source_body = f"(if (= i0 0) (do {tail}) (recur {call_args}))"
    bindings = " ".join(v + (" 1" if i == 0 else " 0") for i, v in enumerate(variables))
    outer = " ".join(p + " " + str(i) for i, p in enumerate(ps))
    source = f"(defn work [] :i64 (let [{outer}] (loop [{bindings}] {source_body})))"
    # Reference capture order is lexical, not numeric (p10 precedes p2).
    ordered = sorted(ps)
    helper_params = variables + ordered
    helper_body = f"(if (= i0 0) (do {tail}) (__kotoba_loop_1 {call_args} " + " ".join(ordered) + "))"
    reference = [function("work", f"(let [{outer}] (__kotoba_loop_1 1 " + "0 " * 19 + " ".join(ordered) + "))", "", ""),
                 function("__kotoba_loop_1", helper_body, " ".join(helper_params), " ".join([":i64"] * len(helper_params)))]
    return source, reference


def main(compiler, out):
    machine = platform.machine()
    assert platform.system() == "Linux" and machine in ("aarch64", "x86_64")
    target = "aarch64-linux" if machine == "aarch64" else "x86_64-linux"
    product = json.loads((ROOT / "native-product.json").read_text())
    assert pin(compiler) == product["rootImage" if machine == "aarch64" else "image"]
    out.mkdir(parents=True, exist_ok=False)
    (out / "observer.py").write_bytes(Path(__file__).read_bytes())
    paths = [p for p in (ROOT / "seed/CORE-STATIC-MANIFEST").read_text().splitlines() if p and not p.startswith("#")]
    assert paths[-1] == "seed/99-entry.kotoba"
    paths = paths[:-1] + EXTRA
    text = "\n".join((ROOT / p).read_text() for p in paths) + ENTRY
    env = dict(PATH="/nonexistent", KEXE_STACK_BYTES="8388608", KEXE_FUEL="10000000000",
               KEXE_ALLOW="35,37,38,39", KEXE_CAP_RESOURCES_35=str(out))
    report = dict(schema="amu.native-checked-source.v1", status="RUNNING", host=[platform.system(), machine],
                  compiler=pin(compiler), observer=pin(Path(__file__)),
                  modules={p: pin(ROOT / p) for p in paths}, calls=[],
                  mutations=[], nativeVerdictAuthority=False, wholeCompilerBridgeQualified=False,
                  persistentBuildQualified=False, sourceResourceProofQualified=False, emulation=False)

    def save():
        (out / "observations.json").write_text(json.dumps(report, indent=2) + "\n")

    def run(name, argv, code=0):
        started = time.monotonic()
        p = subprocess.run(list(map(str, argv)), cwd=out, env=env, capture_output=True, timeout=300)
        (out / (name + ".stdout")).write_bytes(p.stdout)
        (out / (name + ".stderr")).write_bytes(p.stderr)
        report["calls"].append(dict(name=name, exit=p.returncode, seconds=time.monotonic() - started,
                                    stdout=pin(out / (name + ".stdout")), stderr=pin(out / (name + ".stderr"))))
        save()
        assert p.returncode == code, (name, p.returncode, p.stdout[-300:], p.stderr[-500:])
        return p.stdout.decode(), p.stderr.decode()

    def build(name, source):
        src, img = out / (name + ".kotoba"), out / (name + ".elf")
        src.write_text(source)
        run("build-" + name, [compiler, "compile", src, "--target", target, "--output", img, "--format", "static"])
        img.chmod(0o755)
        assert struct.unpack_from('<H', img.read_bytes(), 18)[0] == (183 if machine == "aarch64" else 62)
        return img

    producer = build("source-producer", text)
    oracle_paths = ["seed/00-ns-static.kotoba", "seed/01-mem.kotoba", "seed/02-io.kotoba",
                    "seed/03-source-sha256.kotoba", "seed/04-definition-cid.kotoba",
                    "seed/tests/native-checked-definition-oracle.kotoba"]
    oracle = build("independent-oracle", "\n".join((ROOT / p).read_text() for p in oracle_paths))
    report.update(producer=pin(producer), oracle=pin(oracle), oracleModules={p: pin(ROOT / p) for p in oracle_paths})
    type_oracle_paths = oracle_paths[:-1] + ["seed/tests/native-source-type-oracle.kotoba"]
    type_oracle = build("independent-type-oracle", "\n".join((ROOT / p).read_text() for p in type_oracle_paths))
    report.update(typeOracle=pin(type_oracle), typeOracleModules={p: pin(ROOT / p) for p in type_oracle_paths})

    def rows(stdout):
        lines = stdout.splitlines()
        assert lines[0] == "DCP1 6 2"
        values = [line.split() for line in lines[1:]]
        assert all(len(v) == 4 for v in values) and len({v[0] for v in values}) == len(values)
        return {v[0]: v[1:] for v in values}

    ns = "(ns source (:export [])) "
    cases = {
        "const": ("(defn main [] :i64 42)", [function("main", "42", "", "")]),
        "negative": ("(defn main [] :i64 -7)", [function("main", "-7", "", "")]),
        "minimum": ("(defn main [] :i64 -9223372036854775808)",
                    [function("main", "-9223372036854775808", "", "")]),
        "leaf": ("(defn f [x :i64] :i64 (+ x 1))", [function("f", "(+ x 1)")]),
        "sugar": ("(defn f [x :i64] :i64 (inc x))", [function("f", "(+ x 1)")]),
        "inferred": ("(defn f [x] (+ x 1))", [function("f", "(+ x 1)")]),
        "caller": ("(defn f [x :i64] :i64 (+ x 1)) (defn main [x :i64] :i64 (f x))",
                   [function("f", "(+ x 1)"), function("main", "(f x)")]),
        "constant-reference": ("(def delta 1) (defn f [x :i64] :i64 (+ x delta))", [function("f", "(+ x 1)")]),
        "constant-edit": ("(def delta 2) (defn f [x :i64] :i64 (+ x delta))", [function("f", "(+ x 2)")]),
        "binders": ("(defn main [x :i64] :i64 (+ (let [a x] a) (let [b x] b)))",
                    [function("main", "(+ (let [a x] a) (let [b x] b))")]),
        "sequential-let": ("(defn main [x :i64] :i64 (let [a (+ x 1) b (* a 2)] (+ b x)))",
                           [function("main", "(let [a (+ x 1) b (* a 2)] (+ b x))")]),
        "shadow": ("(defn main [x :i64] :i64 (let [x 1] x))",
                   [function("main", "(let [x 1] x)")]),
        "constant-false": ("(def flag false) (defn main [] :bool flag)",
                           [function("main", "false", "", "", ":bool")]),
        "constant-true": ("(def flag true) (defn main [] :bool flag)",
                          [function("main", "true", "", "", ":bool")]),
        "two-params": ("(defn main [a :i64 b :i64] :i64 (+ a b))", [function("main", "(+ a b)", "a b", ":i64 :i64")]),
        "hygienic-call": ("(defn __dsb0_v1 [x :i64] :i64 (+ x 1)) (defn main [x :i64] :i64 (__dsb0_v1 x))",
                          [function("__dsb0_v1", "(+ x 1)"), function("main", "(__dsb0_v1 x)")]),
        "bool": ("(defn main [x :bool] :bool x)", [function("main", "x", "x", ":bool", ":bool")]),
        "keyword": ("(defn main [] :keyword :hello)", [function("main", ":hello", "", "", ":keyword")]),
        "do": ("(defn main [x :i64] :i64 (+ x 1) (* x 2))", [function("main", "(do (+ x 1) (* x 2))")]),
        "self": ("(defn f [x :i64] :i64 (if (= x 0) 1 (f (- x 1))))", [function("f", "(if (= x 0) 1 (f (- x 1)))")]),
        "recur": ("(defn f [x :i64] :i64 (if (= x 0) 1 (recur (- x 1))))", [function("f", "(if (= x 0) 1 (f (- x 1)))")]),
        "cond-one": ("(defn f [x :i64] :i64 (cond (< x 0) 11 :else 22))",
                     [function("f", "(if (< x 0) 11 22)")]),
        "cond-many": ("(defn f [x :i64] :i64 (cond (< x 0) 11 (= x 0) 22 (> x 9) 33 :else 44))",
                      [function("f", "(if (< x 0) 11 (if (= x 0) 22 (if (> x 9) 33 44)))")]),
        "cond-else": ("(defn f [x :i64] :i64 (cond :else x))", [function("f", "x")]),
        "cond-keyword-value": ("(defn f [x :bool] :keyword (cond x :else :else :done))",
                               [function("f", "(if x :else :done)", "x", ":bool", ":keyword")]),
        "cond-string-value": ('(defn f [x :bool] :string (cond x "yes" :else "no"))',
                              [function("f", '(if x "yes" "no")', "x", ":bool", ":string")]),
        "cond-recur": ("(defn f [x :i64] :i64 (cond (= x 0) 1 :else (recur (dec x))))",
                       [function("f", "(if (= x 0) 1 (f (- x 1)))")]),
        "cond-binding": ("(defn f [x :i64] :i64 (cond (< x 0) (let [x 1] x) :else (let [a x] (inc a))))",
                         [function("f", "(if (< x 0) (let [x 1] x) (let [a x] (+ a 1)))")]),
        "string-equality": ("(defn f [a :string b :string] :bool (= a b))",
                            [function("f", "(string=? a b)", "a b", ":string :string", ":bool")]),
    }
    for ty in [":string", ":bytes", ":vector-i64"]:
        cases["type-" + ty[1:]] = (f"(defn f [x {ty}] {ty} x)", [function("f", "x", "x", ty, ty)])
    cases["escaped-string"] = ('(defn main [] :string "a\\n\\u0000\\\"\\\\z")',
                               [function("main", '"a\\n\\u0000\\\"\\\\z"', "", "", ":string")])
    composite_types = {
        "list-i64": "[:list :i64]", "list-string": "[:list :string]",
        "option-bool": "[:option :bool]", "result-string-bytes": "[:result :string :bytes]",
        "map-keyword-string": "[:map :keyword :string]", "set-keyword": "[:set :keyword]",
        "nested": "[:list [:result [:option :string] [:map :keyword [:list :bytes]]]]",
    }
    for name, ty in composite_types.items():
        cases[name] = (f"(defn f [x {ty}] {ty} x)", [function("f", "x", "x", ty, ty)])
    # Populate the native CT table in a different order. Portable identity
    # cannot contain checker allocation indices or even the names of helpers.
    cases["type-table-reordered"] = (
        "(defn unused [s [:option :string]] [:option :string] s) "
        "(defn f [x [:list :i64]] [:list :i64] x)",
        [function("unused", "s", "s", "[:option :string]", "[:option :string]"),
         function("f", "x", "x", "[:list :i64]", "[:list :i64]")])
    helper = "__kotoba_loop_1"
    self_body = f"(if (= i 0) 1 ({helper} (- i 1)))"
    cases["loop-simple"] = (
        "(defn main [x :i64] :i64 (loop [i x] (if (= i 0) 1 (recur (dec i)))))",
        [function("main", f"({helper} x)"), function(helper, self_body, "i")])
    cases["loop-init-only"] = (
        "(defn main [x :i64] :i64 (loop [i (+ x 1)] (if (= i 0) 1 (recur (dec i)))))",
        [function("main", f"({helper} (+ x 1))"), function(helper, self_body, "i")])
    cases["loop-capture-order"] = (
        "(defn main [z :i64 a :i64] :i64 (loop [i z] (if (= i 0) (+ z a) (recur (dec i)))))",
        [function("main", f"({helper} z a z)", "z a", ":i64 :i64"),
         function(helper, f"(if (= i 0) (+ z a) ({helper} (- i 1) a z))", "i a z", ":i64 :i64 :i64")])
    cases["loop-string-capture"] = (
        "(defn main [s :string x :i64] :i64 (loop [i x] (if (= i 0) (string-length s) (recur (dec i)))))",
        [function("main", f"({helper} x s)", "s x", ":string :i64"),
         function(helper, f"(if (= i 0) (string-length s) ({helper} (- i 1) s))", "i s", ":i64 :string")])
    cases["loop-capture-shadow"] = (
        "(defn main [x :i64] :i64 (loop [i 0] (if (< i 1) (let [x i] (recur (inc x))) x)))",
        [function("main", f"({helper} 0 x)"),
         function(helper, f"(if (< i 1) (let [x i] ({helper} (+ x 1) outer)) outer)", "i outer", ":i64 :i64")])
    cases["loop-local-scopes"] = (
        "(defn main [x :i64] :i64 (loop [i x] (let [a (let [b i] b) c (let [b 1] b)] (if (= a 0) c (recur (dec a))))))",
        [function("main", f"({helper} x)"),
         function(helper, f"(let [a (let [b i] b) c (let [b 1] b)] (if (= a 0) c ({helper} (- a 1))))", "i")])
    cases["loop-nested"] = (
        "(defn main [x :i64] :i64 (loop [i x] (if (= i 0) (loop [j 2] (if (= j 0) 1 (recur (dec j)))) (recur (dec i)))))",
        [function("main", "(__kotoba_loop_2 x)"), function(helper, "(if (= j 0) 1 (__kotoba_loop_1 (- j 1)))", "j"),
         function("__kotoba_loop_2", "(if (= i 0) (__kotoba_loop_1 2) (__kotoba_loop_2 (- i 1)))", "i")])
    cases["loop-owner"] = (
        "(defn first [] :i64 42) (defn main [x :i64] :i64 (loop [i x] (if (= i 0) 1 (recur (dec i)))))",
        [function("first", "42", "", ""), function("main", f"({helper} x)"), function(helper, self_body, "i")])
    cases["unused-loop"] = (
        "(defn main [] :i64 42) (defn unused [] :i64 (loop [x 0] x))",
        [function("main", "42", "", ""), function("unused", f"({helper} 0)", "", ""), function(helper, "x")])
    cases["loop-literal-name"] = (
        "(def __kotoba_loop_1 9) (defn main [x :i64] :i64 (loop [i x] (if (= i 0) __kotoba_loop_1 (recur (dec i)))))",
        [function("main", f"({helper} x)"), function(helper, f"(if (= i 0) 9 ({helper} (- i 1)))", "i")])
    cases["loop-boolean-name"] = (
        "(def __kotoba_loop_1 true) (defn main [x :i64] :i64 (loop [i x] (if __kotoba_loop_1 i (recur (dec i)))))",
        [function("main", f"({helper} x)"), function(helper, f"(if true i ({helper} (- i 1)))", "i")])
    cases["loop-arity63"] = loop_boundary(43)
    observed, inputs = {}, {}
    for name, (source, functions) in cases.items():
        src, ref = out / (name + ".input"), out / (name + ".kir")
        src.write_text(ns + source + "\n")
        ref.write_text(module(functions))
        inputs[name] = src
        expected = rows(run("reference-" + name, [producer, "reference", ref])[0])
        got = rows(run("source-" + name, [producer, src])[0])
        assert got == expected, (name, got, expected)
        observed[name] = got
    for name, fn, gold in [("const", "main", "const"), ("leaf", "f", "leaf"),
                           ("caller", "main", "caller"), ("binders", "main", "binders"), ("self", "f", "self")]:
        expected = run("independent-" + name, [oracle, gold])[0].strip()
        assert observed[name][fn][0] == expected
    assert observed["constant-reference"]["f"] == observed["leaf"]["f"] != observed["constant-edit"]["f"]
    assert observed["recur"] == observed["self"] and observed["sugar"] == observed["inferred"] == observed["leaf"]
    assert observed["cond-recur"] == observed["self"]
    assert observed["loop-simple"][helper] == observed["loop-init-only"][helper] == observed["self"]["f"]
    for name in composite_types:
        assert observed[name]["f"][0] == run("independent-type-" + name, [type_oracle, name])[0].strip()
    assert observed["type-table-reordered"]["f"] == observed["list-i64"]["f"]
    assert observed["list-i64"]["f"] != observed["list-string"]["f"]
    negatives = {
        "ill-typed": "(defn main [] :i64 true)",
        "unknown": "(defn main [] :i64 (unknown 1))",
        "loop-closure": "(defn main [] :i64 (loop [x 0] (let [f (fn [y] (+ y x))] (f 1))))",
        "closure": "(defn main [] :i64 (let [f (fn [x] (+ x 1))] (f 2)))",
        "option-refinement": "(defn main [x :option-i64] :option-i64 x)",
        "tuple-refinement": "(defn main [x [:vector [:i64 :i64]]] [:vector [:i64 :i64]] x)",
        "nested-refinement": "(defn main [x [:list :option-i64]] [:list :option-i64] x)",
        "function-type": "(defn main [f [:fn [[:i64] :i64]]] [:fn [[:i64] :i64]] f)",
        "unused-unsupported": "(defn main [] :i64 42) (defn unused [] :i64 (let [f (fn [x] (+ x 1))] (f 2)))",
        "computed-def": "(def value (+ 1 2)) (defn main [] :i64 value)",
        "constant-alias": "(def a 1) (def b a) (defn main [] :i64 b)",
        "claimed-checked": "{:checked true :functions []}",
        "cond-missing-else": "(defn f [x :bool] :i64 (cond x 1))",
        "cond-misplaced-else": "(defn f [x :bool] :i64 (cond :else 1 x 2))",
        "cond-odd": "(defn f [x :bool] :i64 (cond x 1 :else))",
        "cond-unreachable-unknown": "(defn f [] :i64 (cond :else 1 false (unknown 2)))",
        # The existing KIR reader reserves this sugar spelling. Do not bypass
        # its fresh check to admit a Seed-only shadowed function name.
        "cond-shadowed": "(defn cond [x :i64 y :i64] :i64 (+ x y)) (defn main [] :i64 (cond 1 2))",
        "loop-name-collision": "(defn __kotoba_loop_1 [x :i64] :i64 x) (defn main [] :i64 (loop [i 0] i))",
        "loop-arity65": loop_boundary(45)[0],
        # Existing kr-drop uses an i64 parameter mask; preserve its observed
        # refusal until the adopted reader's arity64 boundary is repaired.
        "loop-arity64-kir-gap": loop_boundary(44)[0],
    }
    for name, source in negatives.items():
        src = out / (name + ".input")
        src.write_text(ns + source + "\n")
        inputs[name] = src
        stdout, stderr = run("refuse-" + name, [producer, src], 1)
        assert not stdout and stderr.startswith("DSB:")
        if name in ("computed-def", "constant-alias", "option-refinement", "tuple-refinement", "nested-refinement", "function-type"):
            assert stderr.startswith("DSB:BRIDGE:")
    mutations = [
        ("operator", 'HD-ADD "+"', 'HD-ADD "-"', "leaf", False),
        ("literal", '(mem-u2dec (nm-nf M n NF-AUX))', '"0"', "const", False),
        ("type", 'TY-BOOL ":bool"', 'TY-BOOL ":i64"', "bool", False),
        ("slot", '(mem-u2dec slot)', '"1"', "two-params", True),
        ("hygiene", '(dsb-salt M S)', '0', "hygienic-call", True),
        ("constant-origin", '(ck-r6f-cdef-fn? M f)', 'false', "constant-false", False),
        ("constant-inline", '(and (= (quot r RES-SCALE) RES-FN) (ck-r6f-cdef-fn? M fi))',
         'false', "constant-false", True),
        ("composite-constructor", 'TC-LIST ":list"', 'TC-LIST ":option"', "list-string", False),
        ("composite-child", '(dsb-type M C a (inc depth))', '":i64"', "list-string", False),
        ("composite-right", '(dsb-type M C b (inc depth))', '":i64"', "map-keyword-string", False),
        ("cond-test", '(dsb-expr M S C p depth)', '"true"', "cond-many", False),
        ("string-equality", 'HD-STRING-EQ "string=?"', 'HD-STRING-EQ "="', "string-equality", False),
        ("loop-recur-capture", '(dsl-capture-text M C (vector-at C 4) false)', '""', "loop-capture-order", True),
    ]
    bridge = (ROOT / BRIDGE).read_text()
    assert text.count(bridge) == 1
    for name, old, new, probe, refuses in mutations:
        assert bridge.count(old) == 1, (name, bridge.count(old))
        image = build("mutant-" + name, text.replace(bridge, bridge.replace(old, new)))
        stdout, stderr = run("detect-" + name, [image, inputs[probe]], 1 if refuses else 0)
        if refuses:
            assert not stdout and stderr.startswith("DSB:")
        else:
            assert rows(stdout) != observed[probe]
        report["mutations"].append(dict(name=name, built=True, executed=True, image=pin(image),
                                         detectedBy="fresh native KIR refusal" if refuses else "independent native identity mismatch"))
        save()
    # A mutant that drops CT-B would falsely turn fixed tuples / option-i64
    # into admitted unrefined types, including under nested constructors.
    old = '(and unary (not= b 0))'
    assert bridge.count(old) == 1
    image = build("mutant-refinement-erasure", text.replace(bridge, bridge.replace(old, 'false')))
    for probe in ("option-refinement", "tuple-refinement", "nested-refinement"):
        stdout, stderr = run("detect-refinement-erasure-" + probe, [image, inputs[probe]])
        assert rows(stdout) and not stderr
    report["mutations"].append(dict(name="refinement-erasure", built=True, executed=True, image=pin(image),
                                     detectedBy="three native atomic-refusal violations"))
    save()
    loop_path = "seed/05-source-loops.kotoba"
    loop_source = (ROOT / loop_path).read_text()
    assert text.count(loop_source) == 1
    for name, old, new, probe, refuses in [
        ("loop-capture-order", '(> (string-compare', '(< (string-compare', "loop-capture-order", False),
        ("loop-capture-loss", '(dsl-capture M S C B record n)', '0', "loop-string-capture", True),
        ("loop-owner", '(vector-assoc! (+ record 1) owner)', '(vector-assoc! (+ record 1) 1)', "loop-owner", True),
    ]:
        assert loop_source.count(old) == 1, (name, loop_source.count(old))
        image = build("mutant-" + name, text.replace(loop_source, loop_source.replace(old, new)))
        stdout, stderr = run("detect-" + name, [image, inputs[probe]], 1 if refuses else 0)
        if refuses:
            assert not stdout and stderr.startswith("DSB:")
        else:
            assert rows(stdout) != observed[probe]
        report["mutations"].append(dict(name=name, built=True, executed=True, image=pin(image),
                                         detectedBy="fresh native KIR refusal" if refuses else "native canonical identity mismatch"))
        save()
    # Execute source via the public static compiler and generated KIR via a
    # native qualification driver using that same adopted reader/backend.
    # Direct public compile-kir -> static is not implemented. No hosted
    # translator or serialized-AST substitute fills that gap. Only entry /
    # export metadata is selected; function bodies are transported unchanged.
    full_paths = [p for p in (ROOT / "seed/FULL-MANIFEST").read_text().splitlines() if p and not p.startswith("#")]
    execution_path = "seed/tests/native-source-loop-execution.kotoba"
    full_parts = []
    for p in full_paths:
        data = (ROOT / p).read_text()
        if p == "seed/78-full-entry.kotoba":
            assert data.count('(defn- seed-main [] :i64') == 1
            data = data.replace('(defn- seed-main [] :i64', '(defn- dsx-original-main [] :i64')
        full_parts.append(data)
    execution_compiler = build("kir-execution-compiler", "\n".join(full_parts) + "\n" + (ROOT / execution_path).read_text())
    report.update(executionCompiler=pin(execution_compiler), publicKirStaticQualified=False,
                  executionCompilerModules={p:pin(ROOT / p) for p in [*full_paths, execution_path]})
    executions = execution_cases()
    executed = []
    for name, (body, call, expected) in executions.items():
        source = '(ns execution (:export [main]))\n' + body + f'\n(defn main [] :i64 {call})\n'
        src = out / ("execute-" + name + ".input")
        src.write_text(source)
        kir = run("emit-execution-" + name, [producer, "kir", src])[0]
        assert kir.count(':entry nil :exports []') == 1
        selected = kir.replace(':entry nil :exports []', ':entry main :exports [main]')
        (out / ("execute-" + name + ".kir")).write_text(selected)
        receipts = {}
        resources = {}
        for lane, text_input in [("source", source), ("kir", selected)]:
            if lane == "source":
                image = build("execute-" + name + "-" + lane, text_input)
                checked_image = out / ("execute-" + name + "-source-driver.elf")
                _, trace = run("build-execute-" + name + "-source-driver",
                               [execution_compiler, "source", src, checked_image, target])
                assert pin(checked_image) == pin(image)
            else:
                image = out / ("execute-" + name + "-kir.elf")
                _, trace = run("build-execute-" + name + "-kir", [execution_compiler, "kir", out / ("execute-" + name + ".kir"), image, target])
                image.chmod(0o755)
                assert struct.unpack_from('<H', image.read_bytes(), 18)[0] == (183 if machine == "aarch64" else 62)
            receipts[lane] = [line for line in trace.splitlines() if line.startswith("DSX-RTL ")]
            resources[lane] = [line.replace(" " + lane + " ", " ", 1) for line in trace.splitlines()
                               if line.startswith(("DSX-FN ", "DSX-FUEL "))]
            stdout, stderr = run("execute-" + name + "-" + lane, [image], expected)
            assert not stdout and not stderr
            executed.append(dict(name=name, lane=lane, image=pin(image), expectedI64=expected))
        assert receipts['source'] == receipts['kir']
        report.setdefault('executionResourceObservations', []).append(dict(
            name=name, sourceDriverMatchesPinnedCompiler=True, runtimeLiteralReceiptsMatch=True,
            runtimeLiterals=len(receipts['source']), resourceContractsEqual=resources['source'] == resources['kir'],
            sourceResourceProofQualified=False))
    report.update(nativeSourceKirExecutions=executed)
    save()
    driver_negatives = {
        "ill-typed": module([function("main", "true", "", "")]),
        "extra-form": module([function("main", "42", "", "")]) + "(defn extra [] :i64 0)\n",
        "runtime-intrinsic": module([function("main", "(kxrt-ctx)", "", "")]),
        "claimed-checked": module([function("main", "42", "", "")]).rstrip()[:-1] + " :checked true}\n",
    }
    for name, data in driver_negatives.items():
        src = out / ("execution-refuse-" + name + ".kir")
        src.write_text(data)
        image = out / ("execution-refuse-" + name + ".elf")
        stdout, stderr = run("execution-refuse-" + name, [execution_compiler, "kir", src, image, target], 1)
        assert not stdout and stderr and not image.exists()
    probe = out / "execution-literal-probe.kir"
    probe.write_text(module([function("main", "42", "", "")]))
    no_image = out / "execution-literal-probe-not-an-image"
    stdout, stderr = run("execution-literal-probe", [execution_compiler, "probe", probe, no_image, target])
    expected_hash = hashlib.sha256(b"runtime-literal-probe").hexdigest()
    literal_rows = [line.split() for line in stderr.splitlines() if line.startswith("DSX-RTL ")]
    assert not stdout and not no_image.exists() and len(literal_rows) == 1
    assert literal_rows[0][2:] == ["21", expected_hash]
    driver_source = (ROOT / execution_path).read_text()
    old = '(dsx-restore-literals lowered saved runtime old-end)'
    assert driver_source.count(old) == 1
    mutant = build("mutant-execution-literal-origin", "\n".join(full_parts) + "\n" + driver_source.replace(old, 'lowered'))
    stdout, stderr = run("detect-execution-literal-origin", [mutant, "probe", probe, no_image, target], 1)
    assert not stdout and stderr and not no_image.exists()
    report.update(executionDriverRefusals=len(driver_negatives), executionLiteralProbe=True,
                  executionMutations=[dict(name="literal-origin", image=pin(mutant), built=True, executed=True,
                                           detectedBy="native runtime literal origin refusal")])
    save()
    whole = out / "whole-compiler.input"
    whole.write_bytes(b"".join((ROOT / p).read_bytes() + b"\n" for p in full_paths))
    assert pin(whole) == product["sourceUnity"]
    stdout, stderr = run("whole-compiler-unbridged-refusal", [producer, whole], 1)
    assert not stdout and stderr.startswith("DSB:")
    report.update(status="PASS_NATIVE_CHECKED_SOURCE_BRIDGE", matchedSourceKirCases=len(cases),
                  independentPayloadOracles=5, atomicRefusals=len(negatives), wholeInput=pin(whole),
                  wholeCompilerRefusal=stderr.strip())
    report.update(independentTypePayloadOracles=len(composite_types))
    assert all(pin(ROOT / p) == v for p, v in {**report["modules"], **report["oracleModules"], **report["typeOracleModules"], **report["executionCompilerModules"]}.items())
    namespace_observer = ROOT / 'scripts/seed/check-source-namespace-native.py'
    spec = importlib.util.spec_from_file_location('native_source_namespace', namespace_observer)
    namespace = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(namespace)
    report['status'] = 'RUNNING_NATIVE_SOURCE_NAMESPACE'
    report['namespaceObserver'] = pin(namespace_observer)
    save()
    report['namespaceQualification'] = namespace.qualify(
        compiler, out/'namespace', paths,
        sorted(p for p in out.glob('*.input') if p != whole), whole,
        len(cases)+len(execution_cases()), len(negatives))
    assert pin(namespace_observer) == report['namespaceObserver']
    report['status'] = 'PASS_NATIVE_CHECKED_SOURCE_BRIDGE'
    save()
    print(report["status"], len(cases), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(), args.output.resolve())
