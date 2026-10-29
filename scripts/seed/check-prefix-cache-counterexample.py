#!/usr/bin/env python3
"""Execute a native counterexample to a proposed count-only prefix cache key."""
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
    paths = [p for p in (ROOT / "seed/CORE-STATIC-MANIFEST").read_text().splitlines() if p and not p.startswith("#")]
    assert paths[-1] == "seed/99-entry.kotoba"
    fixture = ROOT / "seed/tests/native-prefix-cache-counterexample.kotoba"
    source = out / "counterexample.kotoba"
    source.write_bytes(b"".join((ROOT / p).read_bytes() + b"\n" for p in paths[:-1]) + fixture.read_bytes())
    target = "aarch64-linux" if platform.machine() == "aarch64" else "x86_64-linux"
    image = out / "counterexample.elf"
    env = dict(PATH="/nonexistent", KEXE_COMMAND="1", KEXE_FUEL="1000000000", KEXE_STACK_BYTES="8388608")
    report = dict(schema="amu.native-prefix-cache-counterexample.v1", nativeVerdictAuthority=False,
                  qualificationReplacement=False, producer=pin(compiler), source=pin(source), fixture=pin(fixture),
                  sourceBindings={p: pin(ROOT / p) for p in paths[:-1]}, calls=[])

    def run(name, argv, process_env, expected):
        start = time.monotonic()
        p = subprocess.run(list(map(str, argv)), cwd=out, env=process_env, capture_output=True, timeout=600)
        for stream, raw in (("stdout", p.stdout), ("stderr", p.stderr)):
            (out / (name + "." + stream)).write_bytes(raw)
        report["calls"].append(dict(name=name, exit=p.returncode, seconds=time.monotonic() - start))
        (out / "observations.json").write_text(json.dumps(report, indent=2) + "\n")
        assert p.returncode == expected and not p.stderr, (name, p.returncode, p.stderr[-1000:])

    run("build", [compiler, "compile", source, "--target", target, "--output", image, "--format", "static"],
        dict(env, KEXE_ALLOW="35,37,38,39", KEXE_CAP_RESOURCES_35=str(out)), 0)
    image.chmod(0o755)
    run("counterexample", [image], dict(env, KEXE_ALLOW="38"), 0)
    run("wrong-mode-control", [image, "fail-control"], dict(env, KEXE_ALLOW="38"), 1)
    report.update(status="REFUTED_COUNT_ONLY_PREFIX_CACHE_KEY", host=[platform.system(), platform.machine()],
                  image=pin(image), rejectedKey=["j", "at", "MM-CODE-N", "MM-FIX-N"],
                  unchangedFills=True, originalAndRestoredAccepted=True,
                  sameExtentRewritesRefused=["ADRP", "forward branch", "negative word", "wide word"])
    (out / "observations.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--compiler", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    main(a.compiler.resolve(), a.output.resolve())
