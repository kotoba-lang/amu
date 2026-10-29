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

    def cids(name, source, image=cli, code=0):
        p = out / (name + ".kotoba")
        p.write_text("\n".join(source) + "\n")
        stdout, stderr = run("cids-" + name, [image, "definition-cids", p], code)
        if code:
            assert stdout == "" and stderr.startswith("DSB:"), (name, stdout, stderr)
            return {}
        lines = stdout.splitlines()
        assert lines[0] == "DCP1 6 2", lines[0]
        rows = [r.split() for r in lines[1:]]
        assert all(len(r) == 4 for r in rows) and len({r[0] for r in rows}) == len(rows)
        return {r[0]: r[1:] for r in rows}

    def golden(name):
        stdout, _ = run("oracle-" + name, [oracle, name])
        assert len(stdout.strip()) == 59
        return stdout.strip()

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
    two = cids("cycle2", cycle(2))
    assert two["b"][0] == golden("cycle2-first") and two["a"][0] == golden("cycle2-second")
    eight = cids("cycle8", cycle(8))
    for i in range(8):
        assert eight[chr(104 - i)][0] == golden("c8-" + str(i))
    # Negative controls: the gate must refuse / detect, not merely pass.
    cids("refuse-unbound", [fn("f", ["x"], "(missing x)")], code=1)
    cids("refuse-syntax", ["(defn f [x :i64] :i64 (+ x 1)"], code=1)
    # A producer with a changed payload field is refused by its own canonical validator (04) -- no CID leaks.
    cids("mutant-encoder", [fn("f", ["x"], "(+ x 1)")], image=mutant, code=1)
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
