#!/usr/bin/env python3
"""Observe actual native reused/fresh item zeros and two executable mutants."""
import argparse
import hashlib
import json
import platform
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MARK = "r (kxrt-store64 (+ (kxrt-gl 688) (* u 8)) 0) high (if (> (+ off n) (kxrt-gl 760)) (kxrt-gs 760 (+ off n)) 0) w (kxrt-gs 48 (inc u))"
WITHOUT = "r (kxrt-store64 (+ (kxrt-gl 688) (* u 8)) 0) w (kxrt-gs 48 (inc u))"
END_BOUND = "byte-end (+ base (* 8 count))"
SHORT_BOUND = "byte-end (+ base (* 8 (if (> count 0) (dec count) 0)))"


def pin(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main(compiler, out):
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "x86_64")
    out.mkdir(parents=True, exist_ok=False)
    paths = [p for p in (ROOT / "seed/FULL-MANIFEST").read_text().splitlines() if p and not p.startswith("#")]
    original = b"".join((ROOT / p).read_bytes() + b"\n" for p in paths).decode()
    assert original.count(MARK) == 2 and original.count(END_BOUND) == 2
    fixture = ROOT / "seed/tests/native-zero-watermark.kotoba"
    source = out / "oracle.kotoba"
    source.write_bytes(fixture.read_bytes())
    target = "aarch64-linux" if platform.machine() == "aarch64" else "x86_64-linux"
    env = dict(PATH="/nonexistent", KEXE_STACK_BYTES="8388608", KEXE_CAP_RESOURCES_35=str(out),
               KEXE_ALLOW="35,37,38,39", KEXE_FUEL="10000000000", KEXE_COMMAND="1")
    report = dict(schema="amu.native-zero-watermark-controls.v1", nativeVerdictAuthority=False,
                  qualificationReplacement=False, wholeCompilerQualified=False, officialPerformanceQualified=False,
                  observerSourceSHA256=pin(Path(__file__))["sha256"],
                  host=[platform.system(), platform.machine()], producer=pin(compiler), fixture=pin(fixture),
                  sourceBindings={p: pin(ROOT / p) for p in paths}, calls=[], mutations=[])

    def save():
        (out / "observations.json").write_text(json.dumps(report, indent=2) + "\n")

    def run(name, argv, expected=0, execution=False):
        started = time.monotonic()
        p = subprocess.run(list(map(str, argv)), cwd=out, env=env, capture_output=True, timeout=900)
        for stream, raw in (("stdout", p.stdout), ("stderr", p.stderr)):
            (out / (name + "." + stream)).write_bytes(raw)
        row = dict(name=name, exit=p.returncode, seconds=time.monotonic() - started)
        report["calls"].append(row)
        save()
        assert p.returncode == expected and not p.stderr, (name, p.returncode, p.stderr[-1200:])
        if execution:
            assert not p.stdout, (name, "unexpected runtime output")
        print(json.dumps(row), flush=True)

    def build(name, producer, src):
        image = out / (name + ".elf")
        run("build-" + name, [producer, "compile", src, "--target", target, "--output", image, "--format", "static"])
        image.chmod(0o755)
        return image

    image = build("oracle", compiler, source)
    run("fresh-reused-partial-and-nested-scopes", [image], execution=True)
    report["image"] = pin(image)
    for name, changed in (("missing-marker", original.replace(MARK, WITHOUT)),
                           ("relative-marker", original.replace("(kxrt-gs 760 (+ off n))", "(kxrt-gs 760 n)")),
                           ("last-word", original.replace(END_BOUND, SHORT_BOUND))):
        src = out / ("mutant-" + name + ".kotoba")
        src.write_text(changed)
        # The compiler's existing engine stays correct while its emitted guest
        # runtime is broken. Compilation failure cannot count as detection.
        mutant_compiler = build("mutant-compiler-" + name, compiler, src)
        mutant = build("mutant-oracle-" + name, mutant_compiler, source)
        run("detect-" + name, [mutant], 1, execution=True)
        report["mutations"].append(dict(name=name, source=pin(src), compiler=pin(mutant_compiler),
                                         image=pin(mutant), builtSuccessfully=True, executed=True, exit=1))
    report.update(status="PASS_NATIVE_ZERO_WATERMARK_CONTROLS", partialFreshSuffixAndReusedPrefix=True,
                  nestedScopesAndOuterValue=True, unchangedArenaBudgets=True)
    save()
    print(report["status"], flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--compiler", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    main(a.compiler.resolve(), a.output.resolve())
