#!/usr/bin/env python3
"""Stage a candidate native fixed point; never promotes pins or qualifies CI.

Python only concatenates exact sources and observes Amu native processes.
Run through native_build_queue.py on the native x86 Linux host.
"""
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


def main(out):
    assert (platform.system(), platform.machine()) == ("Linux", "x86_64")
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    paths = [p for p in (ROOT / "seed/FULL-MANIFEST").read_text().splitlines()
             if p and not p.startswith("#")]
    source = out / "full.kotoba"
    source.write_bytes(b"".join((ROOT / p).read_bytes() + b"\n" for p in paths))
    producer = ROOT / "bin/amu-linux-x86_64"
    report = dict(schema="amu.native-runtime-profile-candidate.v1", status="running",
                  producer=pin(producer), sourceUnity=pin(source),
                  sources={p: pin(ROOT / p) for p in paths}, calls=[], generations=[],
                  wholeCompilerQualified=False, qualificationReplacement=False,
                  performanceQualified=False)
    env = dict(PATH="/nonexistent", KEXE_ALLOW="35,37,38,39",
               KEXE_CAP_RESOURCES_35=str(out), KEXE_STACK_BYTES="8388608")

    def save():
        (out / "candidate.json").write_text(json.dumps(report, indent=2) + "\n")

    save()
    for i in (1, 2, 3):
        image = out / f"F{i}.elf"
        argv = [producer, "compile", source, "--target", "x86_64-linux",
                "--output", image, "--format", "static"]
        start = time.monotonic()
        r = subprocess.run(list(map(str, argv)), env=env, cwd=out,
                           capture_output=True, timeout=1200)
        for stream, raw in (("stdout", r.stdout), ("stderr", r.stderr)):
            (out / f"F{i}.{stream}").write_bytes(raw)
        report["calls"].append(dict(argv=list(map(str, argv)), exit=r.returncode,
                                    seconds=time.monotonic() - start))
        save()
        assert r.returncode == 0 and not r.stderr and image.is_file(), (i, r.returncode, r.stderr[-1000:])
        image.chmod(0o700)
        report["generations"].append(pin(image))
        print("candidate", i, report["calls"][-1], flush=True)
        producer = image
        save()
    assert report["generations"][0] == report["generations"][1] == report["generations"][2]
    report.update(status="NATIVE_CANDIDATE_FIXED_POINT", fixedPoint=True)
    save()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    main(parser.parse_args().output.resolve())
