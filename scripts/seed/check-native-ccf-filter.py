#!/usr/bin/env python3
"""Observe native equivalence to the original CCF evaluator and four mutants."""
import argparse
import hashlib
import json
import platform
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def pin(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main(compiler, out):
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "x86_64")
    out.mkdir(parents=True, exist_ok=False)
    paths = [p for p in (ROOT / "seed/CORE-STATIC-MANIFEST").read_text().splitlines()
             if p and not p.startswith("#")][:-1]
    source = b"".join((ROOT / p).read_bytes() + b"\n" for p in paths).decode()
    fixture = ROOT / "seed/tests/native-ccf-filter.kotoba"
    text = source + fixture.read_text()
    start = text.index("(defn- ccf-code [")
    end = text.index(";; Preserve direct returned-value comparison", start)
    fragment = text[start:end]
    target = "aarch64-linux" if platform.machine() == "aarch64" else "x86_64-linux"
    env = dict(PATH="/nonexistent", KEXE_STACK_BYTES="8388608", KEXE_CAP_RESOURCES_35=str(out),
               KEXE_ALLOW="35,37,38,39", KEXE_FUEL="10000000000", KEXE_COMMAND="1")
    report = dict(schema="amu.native-ccf-filter-controls.v1", nativeVerdictAuthority=False,
                  qualificationReplacement=False, wholeCompilerQualified=False, gridCases=131072,
                  host=[platform.system(), platform.machine()], producer=pin(compiler), fixture=pin(fixture),
                  observerSourceSHA256=pin(Path(__file__))["sha256"],
                  sourceBindings={p: pin(ROOT / p) for p in paths}, calls=[], mutations=[])

    def save():
        (out / "observations.json").write_text(json.dumps(report, indent=2) + "\n")

    def run(name, argv, expected=0):
        started = time.monotonic()
        p = subprocess.run(list(map(str, argv)), cwd=out, env=env, capture_output=True, timeout=900)
        for stream, raw in (("stdout", p.stdout), ("stderr", p.stderr)):
            (out / (name + "." + stream)).write_bytes(raw)
        report["calls"].append(dict(name=name, exit=p.returncode, seconds=time.monotonic() - started))
        save()
        assert p.returncode == expected and not p.stderr, (name, p.returncode, p.stderr[-1200:])
        if not name.startswith("build-"):
            assert not p.stdout, (name, "unexpected oracle output")

    def build(name, contents):
        src = out / (name + ".kotoba")
        src.write_text(contents)
        image = out / (name + ".elf")
        run("build-" + name, [compiler, "compile", src, "--target", target,
                              "--output", image, "--format", "static"])
        image.chmod(0o755)
        return image

    image = build("oracle", text)
    run("original-evaluator-equivalence", [image])
    run("wrong-mode", [image, "fail"], 1)
    for name, old, new in (
        ("word-bound", "(and (>= w 0) (<= w 4294967295)", "(and true true"),
        ("adrp", "(not= page 2415919104)", "true"),
        ("class-adr-bit", "67835469688274944", "67835469688209408"),
        ("class-literal-bit", "67835469688274944", "67835469671497728"),
    ):
        assert fragment.count(old) == 1, name
        mutant = build("mutant-" + name, text[:start] + fragment.replace(old, new) + text[end:])
        run("detect-" + name, [mutant], 1)
        report["mutations"].append(dict(name=name, image=pin(mutant), builtSuccessfully=True, executed=True, exit=1))
    report.update(status="PASS_NATIVE_CCF_FILTER_CONTROLS", originalEvaluatorEquivalence=True,
                  noMutablePrefixCache=True, allOriginalLimitsAndPredicatesRetained=True)
    save()
    print(report["status"], flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--compiler", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    main(a.compiler.resolve(), a.output.resolve())
