#!/usr/bin/env python3
"""Build the native `definition-cids` candidate image and observe it (JUN-583/JUN-584).

Every parse, check, alpha normalization, SCC search, DAG-CBOR encoding and hash runs in
Amu native images. Python only stages bytes, launches processes and compares observations.
The expected CIDs come from an independently hand-authored oracle image
(seed/tests/native-checked-definition-oracle.kotoba, through seed/04's codec), never from
the producer. A mutant that changes a seed/05 canonical payload field must be refused. This
gate qualifies the candidate closure only; it changes no manifest and grants nothing.
"""
import argparse
import hashlib
import json
import os
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "seed/DEFINITION-CIDS-MANIFEST"
ORACLE = ["seed/00-ns-static.kotoba", "seed/01-mem.kotoba", "seed/02-io.kotoba",
          "seed/03-source-sha256.kotoba", "seed/04-definition-cid.kotoba",
          "seed/tests/native-checked-definition-oracle.kotoba"]


def pin(p):
    b = Path(p).read_bytes()
    return dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest())


def fn(name, params, body):
    ps = " ".join(f"{p} :i64" for p in params)
    return f"(defn {name} [{ps}] :i64 {body})"


def cycle(n):
    return [fn(chr(97 + i), ["x"], f"(if (= x 0) {n - i} ({chr(97 + (i - 1) % n)} (- x 1)))") for i in range(n)]


def main(compiler, out):
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "x86_64")
    target = "aarch64-linux" if platform.machine() == "aarch64" else "x86_64-linux"
    out.mkdir(parents=True, exist_ok=False)
    paths = [p for p in MANIFEST.read_text().splitlines() if p and not p.startswith("#")]
    assert paths[-1] == "seed/99-definition-cids-entry.kotoba"
    assert not set(paths) & {"seed/99-entry.kotoba"}
    env = dict(PATH="/nonexistent", KEXE_STACK_BYTES="8388608", KEXE_FUEL="10000000000",
               KEXE_ALLOW="35,37,38,39", KEXE_CAP_RESOURCES_35=str(out))
    report = dict(schema="amu.native-definition-cids.v1", nativeVerdictAuthority=False,
                  host=[platform.system(), platform.machine()], compiler=pin(compiler), target=target,
                  modules={p: pin(ROOT / p) for p in paths}, calls=[],
                  scope="pure checked-source bridge, payload-v2 profile6/desugar2, SCC<=8; no admission",
                  macosQualified=False, x86CliAlreadyHasCommand="unknown", productionCompilerClosureChanged=False)

    def save():
        (out / "observations.json").write_text(json.dumps(report, indent=2) + "\n")

    def run(name, argv, code=0):
        p = subprocess.run(list(map(str, argv)), cwd=out, env=env, capture_output=True, timeout=900)
        report["calls"].append(dict(name=name, exit=p.returncode, stdoutSHA256=hashlib.sha256(p.stdout).hexdigest(),
                                    stderrSHA256=hashlib.sha256(p.stderr).hexdigest()))
        save()
        print(name, p.returncode, flush=True)
        assert p.returncode == code, (name, p.returncode, p.stdout[-300:], p.stderr[-600:])
        return p.stdout.decode(), p.stderr.decode()

    def build(name, text):
        src = out / (name + ".kotoba")
        src.write_text(text)
        image = out / (name + ".elf")
        run("build-" + name, [compiler, "compile", src, "--target", target, "--output", image, "--format", "static"])
        image.chmod(0o755)
        return image

    text = "\n".join((ROOT / p).read_text() for p in paths)
    cli = build("definition-cids", text)
    oracle = build("oracle", "\n".join((ROOT / p).read_text() for p in ORACLE))
    mutant_text = text.replace('(dc-entry "effect-row" (dcp-effect-row effects))',
                               '(dc-entry "effect-rowx" (dcp-effect-row effects))', 1)
    assert mutant_text != text
    mutant = build("mutant-encoder", mutant_text)
    # B1 mutants (JUN-588): the sealed closure head, and a closure encoder that does not bind its parameters.
    head_text = text.replace('(dcp-list (typed-list-new [:list :string] (dcp-sym "fn") (dcp-vec names) value))',
                             '(dcp-list (typed-list-new [:list :string] (dcp-sym "fnx") (dcp-vec names) value))', 1)
    assert head_text != text
    mutant_head = build("mutant-fn-head", head_text)
    keep_text = text.replace(':string (dcp-bind M A n))\n(defn- dcp-fn [', ':string (dcp-sym "k0"))\n(defn- dcp-fn [', 1)
    assert keep_text != text
    mutant_keep = build("mutant-fn-unbound", keep_text)

    def cids(name, source, image=cli, code=0, groups=False):
        p = out / (name + ".kotoba")
        p.write_text("\n".join(source) + "\n")
        argv = [image, "definition-cids", p] + (["--groups"] if groups else [])
        stdout, stderr = run("cids-" + name + ("-groups" if groups else ""), argv, code)
        if code:
            assert stdout == "" and stderr.startswith("DSB:"), (name, stdout, stderr)
            return {}
        lines = stdout.splitlines()
        # ADR 0300: `name<TAB>CID` per definition in declaration order, then SCANNED<TAB>n/n.
        assert lines[-1] == f"SCANNED\t{len(lines) - 1}/{len(lines) - 1}", lines[-1]
        rows = [r.split("\t") for r in lines[:-1]]
        assert all(len(r) == (4 if groups else 2) for r in rows) and len({r[0] for r in rows}) == len(rows)
        assert all(r[0] != "DCP1" for r in rows)
        return {r[0]: r[1:] for r in rows}

    def golden(name):
        stdout, _ = run("oracle-" + name, [oracle, name])
        assert len(stdout.strip()) == 59
        return stdout.strip()

    order = out / "order.kotoba"
    order.write_text(fn("zeta", ["x"], "(+ x 1)") + "\n" + fn("alpha", ["x"], "(+ x 2)") + "\n")
    stdout, _ = run("order", [cli, "definition-cids", order])
    assert [l.split("\t")[0] for l in stdout.splitlines()] == ["zeta", "alpha", "SCANNED"], stdout
    const = cids("const", [fn("main", [], "42")])
    assert const["main"][0] == golden("const")
    leaf = cids("leaf", [fn("f", ["x"], "(+ x 1)")])
    assert leaf["f"][0] == golden("leaf")
    assert cids("rename", [fn("zz", ["another"], "(+ another 1)")])["zz"] == leaf["f"]
    caller = cids("caller", [fn("f", ["x"], "(+ x 1)"), fn("main", ["x"], "(f x)")])
    assert caller["f"] == leaf["f"] and caller["main"][0] == golden("caller")
    assert cids("reordered", [fn("main", ["y"], "(f y)"), fn("f", ["a"], "(+ a 1)")]) == caller
    edit = cids("dependency-edit", [fn("f", ["x"], "(+ x 2)"), fn("main", ["x"], "(f x)")])
    assert edit["f"][0] == golden("leaf2") and edit["main"][0] == golden("caller2")
    assert edit["main"][0] != caller["main"][0]
    assert cids("self", [fn("f", ["x"], "(if (= x 0) 1 (f (- x 1)))")])["f"][0] == golden("self")
    # --groups keeps group/SCC information: same CIDs, plus group CID and member index.
    flat, grouped = cids("cycle2-flat", cycle(2)), cids("cycle2", cycle(2), groups=True)
    assert {k: v[0] for k, v in grouped.items()} == {k: v[0] for k, v in flat.items()}
    assert {v[2] for v in grouped.values()} == {"0", "1"} and grouped["a"][1] == grouped["b"][1] != "-"
    two = grouped
    assert two["b"][0] == golden("cycle2-first") and two["a"][0] == golden("cycle2-second")
    eight = cids("cycle8", cycle(8), groups=True)
    for i in range(8):
        assert eight[chr(104 - i)][0] == golden("c8-" + str(i))
    # B1 local closures (JUN-588). Expected CIDs are hand-authored payloads in the oracle image, never the producer.
    clo = cids("closure", [fn("f", ["n"], "(let [g (fn [x] (+ x 1))] (g n))")])
    assert clo["f"][0] == golden("closure")
    # Renaming the lambda parameter, the let name and the definition leaves the CID alone; the body does not.
    assert cids("closure-renamed", [fn("zz", ["m"], "(let [h (fn [y] (+ y 1))] (h m))")])["zz"] == clo["f"]
    assert cids("closure-body", [fn("f", ["n"], "(let [g (fn [x] (+ x 2))] (g n))")])["f"][0] != clo["f"][0]
    # Observation (pinned, not a claim of equivalence): a closure keeps its own identity; the hand-inlined body is the leaf.
    inlined = cids("closure-inlined", [fn("f", ["n"], "(+ n 1)")])
    assert inlined["f"][0] == golden("leaf") and inlined["f"][0] != clo["f"][0]
    report["observations"] = dict(closureLetFn=clo["f"][0], handInlined=inlined["f"][0], equal=False)
    # A captured outer local is a binder reference: its name does not matter, which binder it is does.
    cap = cids("closure-capture", [fn("f", ["n"], "(let [k 5 g (fn [x] (+ x k))] (g n))")])
    assert cap["f"][0] == golden("closure-capture")
    assert cids("closure-capture-renamed", [fn("f", ["n"], "(let [m 5 q (fn [z] (+ z m))] (q n))")]) == cap
    pick_k = cids("closure-capture-k", [fn("f", ["n"], "(let [k 5 j 6 g (fn [x] (+ x k))] (g n))")])
    pick_j = cids("closure-capture-j", [fn("f", ["n"], "(let [k 5 j 6 g (fn [x] (+ x j))] (g n))")])
    assert pick_k["f"][0] != pick_j["f"][0]
    assert cids("closure-param-vs-capture-a", [fn("f", ["n"], "(let [g (fn [x] (+ x n))] (g n))")])["f"][0] != \
        cids("closure-param-vs-capture-b", [fn("f", ["n"], "(let [g (fn [x] (+ x x))] (g n))")])["f"][0]
    # A top-level definition referenced inside the body is a direct dependency (by CID).
    dep = cids("closure-dep", [fn("h", ["x"], "(+ x 1)"), fn("f", ["n"], "(let [g (fn [y] (h y))] (g n))")])
    assert dep["h"][0] == golden("leaf") and dep["f"][0] == golden("closure-dep")
    dep2 = cids("closure-dep-edit", [fn("h", ["x"], "(+ x 2)"), fn("f", ["n"], "(let [g (fn [y] (h y))] (g n))")])
    assert dep2["f"][0] != dep["f"][0]
    assert cids("closure-nested", [fn("f", ["n"], "(let [g (fn [x] (let [h (fn [y] (+ y x))] (h n)))] (g 1))")])["f"][0] \
        == golden("closure-nested")
    assert cids("closure-two", [fn("f", ["n"], "(let [a 1 b 2 g (fn [x] (+ x (+ a b)))] (g n))")])["f"][0] \
        == golden("closure-two")
    # Negative controls: the gate must refuse / detect, not merely pass.
    cids("refuse-unbound", [fn("f", ["x"], "(missing x)")], code=66)
    cids("refuse-syntax", ["(defn f [x :i64] :i64 (+ x 1)"], code=66)
    # Closure refusals stay fail-closed (exit 66, empty stdout, a named DSB: diagnostic), never a wrong CID.
    cids("refuse-closure-unbound", [fn("f", ["n"], "(let [g (fn [x] (+ x missing))] (g n))")], code=66)
    cids("refuse-closure-in-loop", [fn("f", ["n"], "(loop [i 0] (if (< i n) (let [g (fn [x] (+ x i))] (recur (+ i (g 1)))) i))")], code=66)
    cids("refuse-loop-in-closure", [fn("f", ["n"], "(let [g (fn [x] (loop [i 0] (if (< i x) (recur (+ i 1)) i)))] (g n))")], code=66)
    cids("refuse-closure-operator", [fn("f", ["n"], "((fn [x] (+ x 1)) n)")], code=66)
    cids("refuse-closure-callback", ["(defn ap [g [:fn [:i64] :i64] x :i64] :i64 (g x))",
                                     fn("f", ["n"], "(ap (fn [x] (+ x 1)) n)")], code=66)
    # A producer with a changed payload field is refused by its own canonical validator (04) -- no CID leaks.
    cids("mutant-encoder", [fn("f", ["x"], "(+ x 1)")], image=mutant, code=66)
    # The closure encoder mutants must not reproduce the oracle CID (head spelling), and the one that never binds
    # the parameter must not produce a CID (the body's reference is then unbound: refused).
    moved = cids("mutant-fn-head", [fn("f", ["n"], "(let [g (fn [x] (+ x 1))] (g n))")], image=mutant_head)
    assert moved["f"][0] != golden("closure")
    assert cids("mutant-fn-head-plain", [fn("f", ["x"], "(+ x 1)")], image=mutant_head)["f"][0] == golden("leaf")
    cids("mutant-fn-unbound", [fn("f", ["n"], "(let [g (fn [x] (+ x 1))] (g n))")], image=mutant_keep, code=66)
    # Usage errors are not "no identity": distinct exit code.
    run("usage-extra-arg", [cli, "definition-cids", order, "--nope"], 2)
    run("usage-missing-file-arg", [cli, "definition-cids"], 2)
    # The unchanged core driver still answers its own commands through this entry.
    ok = out / "ok.kotoba"
    ok.write_text(fn("f", ["x"], "(+ x 1)") + "\n")
    stdout, _ = run("driver-check", [cli, "check", ok])
    assert stdout.strip() == "ok", stdout
    report["status"] = "PASS_NATIVE_DEFINITION_CIDS"
    save()
    print(report["status"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--compiler", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    main(a.compiler, a.output)
