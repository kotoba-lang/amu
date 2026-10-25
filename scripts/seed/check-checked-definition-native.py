#!/usr/bin/env python3
"""Stage KIR fixtures and observe the native checked identity/SCC producer.

All binding normalization, canonical encoding, SCC search, hashing, type
checks, version parsing and independent payload construction execute in Amu
native images. Python only stages bytes, launches processes and compares
observations. No definition/hash grants execution or build-cache authority.
"""
import argparse
import hashlib
import json
import platform
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXTRA = ["seed/04-definition-cid.kotoba", "seed/05-checked-definition.kotoba",
         "seed/06-definition-groups.kotoba", "seed/tests/native-checked-definition-equivalence.kotoba"]
AUTH = ROOT / "seed/tests/checked-definition-authority"
ENTRY = r'''
(defn- seed-main [] :i64
 (cond (and (= (io-argc) 3) (= (io-arg 0) "versions"))
        (if (dce-authority (io-fs2-text 65 (io-arg 1) "") (io-fs2-text 65 (io-arg 2) "")) 0 1)
       (and (= (io-argc) 2) (= (io-arg 0) "equivalence"))
        (if (dce-run (io-fs2-text 65 (io-arg 1) ""))
          (let [out (io-out "PASS_NATIVE_SCC_EQUIVALENCE\n")] 0) 1)
       (= (io-argc) 1)
        (let [result (dcs-run (io-fs2-text 65 (io-arg 0) ""))]
          (if (= result 0) 0
            (let [out (io-err (string-concat "DCP:E" (string-concat (mem-u2dec result) "\n")))] 1)))
       :else 2))
'''


def pin(p):
    b = p.read_bytes()
    return dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest())


def function(name, body, params="x", types=":i64", result=":i64", effects="#{}"):
    return ("{:name " + name + " :params [" + params + "] :param-types [" + types + "] :result " +
            result + " :effects " + effects + " :body " + body + "}")


def module(functions, tail=""):
    return ("{:format :kotoba.kir/v4 :entry nil :exports [] :effects #{} :functions [" +
            " ".join(functions) + "] " + tail + "}\n")


def cycle(n):
    # Distinct bases force the canonical winner to the LAST permutation.
    return module([function(chr(97 + i), "(if (= x 0) " + str(n - i) + " (" +
                            chr(97 + (i - 1) % n) + " (- x 1)))") for i in range(n)])


def main(compiler, out):
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "x86_64")
    out.mkdir(parents=True, exist_ok=False)
    snapshot = json.loads((AUTH / "snapshot.json").read_text())
    for name, expected_pin in snapshot["files"].items():
        assert pin(AUTH / name) == {k: expected_pin[k] for k in ("bytes", "sha256")}, name
    target = "aarch64-linux" if platform.machine() == "aarch64" else "x86_64-linux"
    paths = [p for p in (ROOT / "seed/CORE-STATIC-MANIFEST").read_text().splitlines()
             if p and not p.startswith("#")]
    assert paths[-1] == "seed/99-entry.kotoba", paths[-1]
    paths = paths[:-1] + EXTRA
    source = out / "producer.kotoba"
    source.write_bytes(b"\n".join((ROOT / p).read_bytes() for p in paths) + ENTRY.encode())
    env = dict(PATH="/nonexistent", KEXE_STACK_BYTES="8388608", KEXE_FUEL="10000000000",
               KEXE_ALLOW="35,37,38,39", KEXE_CAP_RESOURCES_35=str(out))
    report = dict(schema="amu.native-checked-definition.v1", nativeVerdictAuthority=False,
                  host=[platform.system(), platform.machine()], compiler=pin(compiler), target=target,
                  modules={p: pin(ROOT / p) for p in paths}, source=pin(source),
                  authority={p.name: pin(p) for p in AUTH.iterdir() if p.is_file()},
                  scope="bounded pure KIR v3/v4, payload-v2, profile6/desugar2, SCC<=8",
                  fullSeedFrontendQualified=False, persistentBuildQualified=False,
                  productionCompilerClosureChanged=False, emulation=False, calls=[], mutations=[])

    def save():
        (out / "observations.json").write_text(json.dumps(report, indent=2) + "\n")

    def run(name, argv, code=0):
        start = time.monotonic()
        p = subprocess.run(list(map(str, argv)), cwd=out, env=env, capture_output=True, timeout=900)
        (out / (name + ".stdout")).write_bytes(p.stdout)
        (out / (name + ".stderr")).write_bytes(p.stderr)
        row = dict(name=name, exit=p.returncode, seconds=time.monotonic() - start,
                   stdoutSHA256=hashlib.sha256(p.stdout).hexdigest(),
                   stderrSHA256=hashlib.sha256(p.stderr).hexdigest())
        report["calls"].append(row)
        save()
        print(json.dumps(row), flush=True)
        assert p.returncode == code, (name, p.returncode, p.stdout[-400:], p.stderr[-800:])
        return p.stdout.decode()

    def build(name, text):
        p = out / (name + ".kotoba")
        p.write_text(text)
        image = out / (name + ".elf")
        run("build-" + name, [compiler, "compile", p, "--target", target, "--output", image, "--format", "static"])
        image.chmod(0o755)
        return image

    producer = build("checked-producer", source.read_text())
    oracle_paths = ["seed/00-ns-static.kotoba", "seed/01-mem.kotoba", "seed/02-io.kotoba",
                    "seed/03-source-sha256.kotoba", "seed/04-definition-cid.kotoba",
                    "seed/tests/native-checked-definition-oracle.kotoba"]
    oracle = build("independent-oracle", "\n".join((ROOT / p).read_text() for p in oracle_paths))
    report.update(producer=pin(producer), oracle=pin(oracle), oracleModules={p: pin(ROOT / p) for p in oracle_paths})
    grammar = out / "guest-grammar.edn"
    elaboration = out / "elaboration-pipeline.edn"
    grammar.write_bytes((AUTH / grammar.name).read_bytes())
    elaboration.write_bytes((AUTH / elaboration.name).read_bytes())
    run("current-authority", [producer, "versions", grammar, elaboration])
    for filename, old, new in [(grammar, ":kotoba.lang.guest-grammar/profile-version 6",
                                ":kotoba.lang.guest-grammar/profile-version 7"),
                               (elaboration, ":desugar-contract 2", ":desugar-contract 3")]:
        text = filename.read_text()
        assert text.count(old) == 1
        changed = out / ("changed-" + filename.name)
        changed.write_text(text.replace(old, new))
        run("refuse-" + filename.stem + "-drift", [producer, "versions",
            changed if filename == grammar else grammar, changed if filename == elaboration else elaboration], 1)

    sources = {}

    def produce(name, text, code=0, image=producer):
        p = out / (name + ".kir")
        p.write_text(text)
        sources[name] = p
        result = run(name, [image, p], code)
        if code:
            assert not result, (name, "refusal leaked a partial identity")
            return {}
        lines = result.splitlines()
        assert lines[0] == "DCP1 6 2"
        rows = [row.split() for row in lines[1:]]
        assert all(len(row) == 4 for row in rows) and len({row[0] for row in rows}) == len(rows)
        return {row[0]: row[1:] for row in rows}

    expected = {}

    def golden(name):
        if name not in expected:
            expected[name] = run("oracle-" + name, [oracle, name]).strip()
            assert len(expected[name]) == 59
        return expected[name]

    const = produce("const", module([function("main", "42", "", "")]))
    assert const["main"][0] == golden("const")
    leaf = produce("leaf", module([function("f", "(+ x 1)")]))
    assert leaf["f"][0] == golden("leaf")
    assert produce("rename", module([function("zz", "(+ another 1)", "another")]))["zz"] == leaf["f"]
    caller = produce("caller", module([function("f", "(+ x 1)"), function("main", "(f x)")]))
    assert caller["f"] == leaf["f"] and caller["main"][0] == golden("caller")
    assert produce("reordered", module([function("main", "(f y)", "y"), function("f", "(+ a 1)", "a")])) == caller
    changed = produce("dependency-edit", module([function("f", "(+ x 2)"), function("main", "(f x)")]))
    assert changed["f"][0] == golden("leaf2") and changed["main"][0] == golden("caller2")
    assert changed["main"][0] != caller["main"][0]
    for name, body in [("binders", "(+ (let [y x] y) (let [z x] z))"),
                       ("result", "(result-match-of [:result :i64 :i64] (result-ok-of [:result :i64 :i64] x) good (+ good x) bad (- bad x))"),
                       ("option", "(option-match [:option :i64] (option-some-of [:option :i64] x) 0 some (+ some x))")]:
        got = produce(name, module([function("main", body)]))
        assert got["main"][0] == golden(name)
    self_ = produce("self", module([function("f", "(if (= x 0) 1 (f (- x 1)))")]))
    assert self_["f"][0] == golden("self")
    two = produce("cycle2", cycle(2))
    assert two["b"][0] == golden("cycle2-first") and two["a"][0] == golden("cycle2-second")
    renamed = produce("cycle2-rename", module([function("z", "(if (= q 0) 1 (a (- q 1)))", "q"),
                                               function("a", "(if (= b 0) 2 (z (- b 1)))", "b")]))
    assert renamed["z"] == two["b"] and renamed["a"] == two["a"]
    eight = produce("cycle8", cycle(8))
    assert len(eight) == 8 and eight["h"][1] == golden("cycle8-group")
    for i in range(8):
        assert eight[chr(104 - i)][0] == golden("c8-" + str(i)) and eight[chr(104 - i)][2] == str(i)
    external = []
    for constant in [1, 2]:
        got = produce("external-cycle-" + str(constant), module([
            function("leaf", "(+ x " + str(constant) + ")"),
            function("a", "(if (= x 0) (+ (leaf x) 1) (b (- x 1)))"),
            function("b", "(if (= x 0) (+ (leaf x) 2) (a (- x 1)))"), function("main", "(a x)")]))
        prefix = "external" + ("2" if constant == 2 else "")
        assert got["a"][0] == golden(prefix + "-first") and got["b"][0] == golden(prefix + "-second")
        external.append(got)
    assert external[0]["a"][1] != external[1]["a"][1] and external[0]["main"][0] != external[1]["main"][0]
    for n in [1, 2, 3, 4, 8]:
        p = out / ("equivalence-" + str(n) + ".kir")
        p.write_text(cycle(n))
        assert run("equivalence-" + str(n), [producer, "equivalence", p]) == "PASS_NATIVE_SCC_EQUIVALENCE\n"
    # Multiple group-reference holes and literal digits distinguish template
    # patching from indiscriminate string replacement.
    p = out / "equivalence-multiple-holes.kir"
    p.write_text(module([function("f", '(if (= x 0) (string-length "0,1") (+ (g (- x 1)) (f (- x 1))))'),
                         function("g", '(if (= x 0) (string-length "1,0") (+ (f (- x 1)) (g (- x 1))))')]))
    assert run("equivalence-multiple-holes", [producer, "equivalence", p]) == "PASS_NATIVE_SCC_EQUIVALENCE\n"
    for n in [3, 4]:
        p = out / ("equivalence-ties-" + str(n) + ".kir")
        p.write_text(module([function(chr(97 + i), "(if (= x 0) 1 (" + chr(97 + (i - 1) % n) +
                                      " (- x 1)))") for i in range(n)]))
        assert run("equivalence-ties-" + str(n), [producer, "equivalence", p]) == "PASS_NATIVE_SCC_EQUIVALENCE\n"
    negatives = {
        "wrong-type": module([function("main", "42", "", "", ":bool")]),
        "unresolved": module([function("main", "(missing x)")]),
        "wire-effect": module([function("main", "42", "", "", effects="#{[:cap/call 35]}")]),
        "schema": module([function("main", "42", "", "")], ":schemas {:Foo [:record {:x :i64}]}"),
        "forged-checked": module([function("main", "42", "", "", ":bool")], ":checked true"),
        "unsupported-loop": module([function("main", "(loop [n 0] n)", "", "")]),
        "reserved-group-tag": module([function("main", "[:kotoba.definition/group 0]", "", "", ":vector-i64")]),
        "duplicate-field": module([function("main", "42", "", "")], ":effects #{}"),
        "cycle9-refused": cycle(9),
    }
    for name, text in negatives.items():
        produce(name, text, 1)
    original = source.read_text()
    mutations = [
        ("native-check", "(not (dcs-native-checked? S)) 8", "false 8", "wrong-type", "accept"),
        ("binder-counter", "restore (vector-assoc! A 2 scope)",
         "restore (vector-assoc! (vector-assoc! A 1 scope) 2 scope)", "binders", "different"),
        ("scc-bound", "(if (> n 8) (let [bad (dcp-fail A 6)] R)",
         "(if (> n 9) (let [bad (dcp-fail A 6)] R)", "cycle9-refused", "accept"),
        ("group-reference", "index (dec (dcp-f A f 3))]", "index original]", "cycle2-rename", "different"),
    ]
    for name, old, new, probe, detection in mutations:
        occurrences = original.count(old)
        assert occurrences == (2 if name == "binder-counter" else 1), (name, occurrences)
        image = build("mutant-" + name, original.replace(old, new))
        got = produce("detect-" + name, sources[probe].read_text(), image=image)
        if detection == "different":
            correct = golden("binders") if name == "binder-counter" else two["b"][0]
            assert got["main" if name == "binder-counter" else "z"][0] != correct
        report["mutations"].append(dict(name=name, source=pin(out / ("mutant-" + name + ".kotoba")),
                                         image=pin(image), builtSuccessfully=True, executed=True,
                                         detection=detection))
    report.update(status="PASS_NATIVE_CHECKED_DEFINITION", independentOraclePassed=True,
                  nativeTypeCheckingRequired=True, nativeAuthorityVersionsChecked=True,
                  scc8LastPermutationOracle=True, scc9Refused=True, nativeSccEquivalence=True)
    save()
    print(report["status"], flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--compiler", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    main(a.compiler.resolve(), a.output.resolve())
