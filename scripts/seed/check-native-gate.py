#!/usr/bin/env python3
"""Stage a standalone complete24 native gate probe; the ELF owns the verdict.

This is not a complete-compiler fixed-point or controller qualification.
"""
import argparse
import hashlib
import json
import platform
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def pin(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(gate, cases_dir, out):
    assert platform.system() == "Linux" and platform.machine() == "x86_64"
    policy = json.loads((ROOT / "seed/cdci/policy.json").read_text())
    assert pin(gate) == policy["kotobaNativeGateSHA256"]
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    shutil.copy2(gate, out / "gate.elf")
    (out / "gate.elf").chmod(0o755)
    cases = json.loads((ROOT / "seed/static-cases.json").read_text())["cases"]
    assert len(cases) == 24
    lines = ["KCGATE1", str(out), pin(out / "gate.elf"), "24"]
    for i, case in enumerate(cases):
        source, image = out / f"case-{i}.kotoba", out / f"case-{i}.elf"
        source.write_text(case["source"])
        shutil.copy2(cases_dir / ("case-" + case["name"] + ".elf"), image)
        image.chmod(0o755)
        lines += [pin(source), pin(image), source.name, image.name,
                  str(0 if case["reference"]["exit"] else case["result"]),
                  str(case["reference"]["exit"]), str(case["reference"]["remainingFuel"])]
    ledger = out / "cases.kcg"
    ledger.write_text("\n".join(lines) + "\n")
    r = subprocess.run([str(out / "gate.elf"), str(ledger), pin(ledger)], env={"PATH": "/nonexistent"},
                       capture_output=True, timeout=150)
    (out / "gate.stdout").write_bytes(r.stdout)
    (out / "gate.stderr").write_bytes(r.stderr)
    assert r.returncode == 0 and not r.stderr, (r.returncode, r.stderr[-400:])
    raw = (out / "kotoba-gate.receipt").read_bytes()
    body, digest, end = raw.rsplit(b"\n", 2)
    assert end == b"" and raw.startswith(b"KCGATE-R1\n")
    assert hashlib.sha256(body + b"\n").hexdigest().encode() == digest
    assert raw == r.stdout
    report = dict(status="PASS_NATIVE_KOTOBA_GATE", cases=24, gateSHA256=pin(gate),
                  receiptSHA256=hashlib.sha256(raw).hexdigest(),
                  host=[platform.system(), platform.machine(), platform.release()],
                  compilerFixedPointQualified=False, controllerQualified=False)
    (out / "gate-probe.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], "24 actual result/exit/fuel cases", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gate", type=Path, required=True)
    p.add_argument("--case-images", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    main(a.gate.resolve(), a.case_images.resolve(), a.output.resolve())
