#!/usr/bin/env python3
"""Observe native flock/vector coexistence and an executed slot-alias mutant.

The Kotoba fixture decides its lock, zeroing and outer-value result. Python
only stages source/paths and records native process exits and hashes.
"""
import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def pin(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main(compiler, out):
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "x86_64")
    target = "aarch64-linux" if platform.machine() == "aarch64" else "x86_64-linux"
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    scope = out / "scope"
    scope.mkdir(mode=0o700)
    (out / "outside-target").write_text("outside\n")
    (scope / "link.lock").symlink_to(out / "outside-target")
    fixture = ROOT / "seed/tests/native-flock-vector.kotoba"
    src = out / "fixture.kotoba"
    src.write_bytes(fixture.read_bytes())
    paths = [p for p in (ROOT / "seed/FULL-MANIFEST").read_text().splitlines()
             if p and not p.startswith("#")]
    env = dict(PATH="/nonexistent", KEXE_STACK_BYTES="8388608",
               KEXE_CAP_RESOURCES_35=str(out), KEXE_ALLOW="35,37,38,39",
               KEXE_FUEL="10000000000", KEXE_COMMAND="1")
    report = dict(schema="amu.native-flock-vector.v1", host=[platform.system(), platform.machine()],
                  producer=pin(compiler), fixture=pin(fixture),
                  sourceBindings={p: pin(ROOT / p) for p in paths}, calls=[])

    def run(name, argv, expected=0):
        operation_env = env if name.startswith("build-") else {
            **env, "KEXE_CAP_RESOURCES_35": str(scope), "KEXE_ALLOW": "35,38"}
        r = subprocess.run(list(map(str, argv)), cwd=out, env=operation_env,
                           capture_output=True, timeout=900)
        for stream, raw in (("stdout", r.stdout), ("stderr", r.stderr)):
            (out / (name + "." + stream)).write_bytes(raw)
        report["calls"].append(dict(name=name, exit=r.returncode))
        assert r.returncode == expected and not r.stderr, (name, r.returncode, r.stderr[-800:])
        if not name.startswith("build-"):
            assert not r.stdout, (name, "unexpected fixture output")

    def build(name, producer, source):
        dst = out / (name + ".elf")
        run("build-" + name, [producer, "compile", source, "--target", target,
                              "--output", dst, "--format", "static"])
        dst.chmod(0o700)
        return dst

    good = build("fixture", compiler, src)
    def fixture_args(name):
        return [scope / name, str(scope) + "//" + name, scope / "link.lock", out / "outside.lock"]

    run("lock-vector-rollback-and-unlock", [good, *fixture_args("good.lock")])
    parts = []
    changed = 0
    for p in paths:
        text = (ROOT / p).read_text()
        if p in ("seed/76-x86_64-static-rt.kotoba", "seed/77-aarch64-static-rt.kotoba"):
            start = text.index("(defn- kxrt-fs-lock ")
            end = text.index(";; ---- wire 42", start)
            body = text[start:end]
            assert body.count("kxrt-gl 792") == 1 and body.count("kxrt-gs 792") == 2
            body = body.replace("kxrt-gl 792", "kxrt-gl 760").replace("kxrt-gs 792", "kxrt-gs 760")
            text = text[:start] + body + text[end:]
            changed += 1
        parts.append(text + "\n")
    assert changed == 2
    mutant_source = out / "slot-alias.kotoba"
    mutant_source.write_text("".join(parts))
    mutant_compiler = build("slot-alias-compiler", compiler, mutant_source)
    bad = build("slot-alias-fixture", mutant_compiler, src)
    run("detect-slot-alias", [bad, *fixture_args("bad.lock")], 1)
    assert pin(fixture) == report["fixture"] and pin(compiler) == report["producer"]
    assert all(pin(ROOT / p) == expected for p, expected in report["sourceBindings"].items())
    report.update(status="PASS_NATIVE_FLOCK_VECTOR", image=pin(good),
                  mutant=dict(source=pin(mutant_source), compiler=pin(mutant_compiler),
                              image=pin(bad), builtSuccessfully=True, executed=True, exit=1),
                  qualificationReplacement=False)
    (out / "observations.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--compiler", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    main(a.compiler.resolve(), a.output.resolve())
