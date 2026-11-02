#!/usr/bin/env python3
"""Fresh native complete24 verdict before the expensive ARM/x86 derivation.

Python transports pinned inputs and observes exits. The existing native gate
decides source/image/result/exit/fuel agreement. Full controller qualification
and every later gate remain required.
"""
import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def pin(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(compiler, out):
    assert platform.system() == "Linux" and platform.machine() == "x86_64"
    assert pin(compiler) == json.loads((ROOT / "native-product.json").read_text())["image"]["sha256"]
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    policy = json.loads((ROOT / "seed/cdci/policy.json").read_text())
    cases = json.loads((ROOT / "seed/static-cases.json").read_text())["cases"]
    assert len(cases) == 24
    report = dict(schema="amu.early-native-kotoba24.v1", nativeControllerQualified=False,
                  qualificationReplacement=False, producerSHA256=pin(compiler),
                  observerSourceSHA256=pin(Path(__file__)), fixtureSHA256=pin(ROOT / "seed/static-cases.json"),
                  caseArtifacts=[], calls=[])
    env = dict(PATH="/nonexistent", KEXE_CAP_RESOURCES_35=str(out), KEXE_STACK_BYTES="8388608")

    def run(name, argv, expected=0, native_gate=False):
        started = time.monotonic()
        p = subprocess.run(list(map(str, argv)), cwd=out, env={"PATH": "/nonexistent"} if native_gate else env,
                           capture_output=True, timeout=180)
        for stream, data in (("stdout", p.stdout), ("stderr", p.stderr)):
            (out / (name + "." + stream)).write_bytes(data)
        report["calls"].append(dict(name=name, exit=p.returncode, seconds=time.monotonic() - started))
        (out / "observations.json").write_text(json.dumps(report, indent=2) + "\n")
        assert p.returncode == expected, (name, p.returncode, p.stderr[-800:])
        if expected == 0:
            assert not p.stderr, (name, p.stderr)
        else:
            assert b"CDCI:E4002\n" == p.stderr, (name, p.stderr)

    for name in ("entry.kotoba", "runtime.kotoba", "kotoba-gate.kotoba"):
        shutil.copy2(ROOT / "seed/cdci" / name, out / name)
    assert hashlib.sha256(b"".join((out / n).read_bytes() for n in
                                  ("entry.kotoba", "runtime.kotoba", "kotoba-gate.kotoba"))).hexdigest() == policy["kotobaGateSourceSHA256"]
    gate = out / "kotoba-native.elf"
    run("build-gate", [compiler, "cdci-build", "kotoba-native", out / "entry.kotoba",
                       out / "runtime.kotoba", out / "kotoba-gate.kotoba", gate])
    gate.chmod(0o755)
    report["gateImageSHA256"] = pin(gate)
    (out / "observations.json").write_text(json.dumps(report, indent=2) + "\n")
    assert pin(gate) == policy["kotobaNativeGateSHA256"]
    lines = ["KCGATE1", str(out), pin(gate), "24"]
    for i, case in enumerate(cases):
        source = out / f"case-{i}.kotoba"
        image = out / f"case-{i}.elf"
        source.write_text(case["source"])
        run(f"compile-case-{i}", [compiler, "compile", source, "--target", "x86_64-linux",
                                   "--output", image, "--format", "static"])
        image.chmod(0o755)
        report["caseArtifacts"].append(dict(index=i, name=case["name"], sourceSHA256=pin(source),
                                            imageSHA256=pin(image), imageBytes=image.stat().st_size))
        (out / "observations.json").write_text(json.dumps(report, indent=2) + "\n")
        lines += [pin(source), pin(image), source.name, image.name,
                  str(0 if case["reference"]["exit"] else case["result"]),
                  str(case["reference"]["exit"]), str(case["reference"]["remainingFuel"])]
    ledger = out / "cases.kcg"
    ledger.write_text("\n".join(lines) + "\n")
    run("native-complete24", [gate, ledger, pin(ledger)], native_gate=True)
    report["nativeReceiptSHA256"] = pin(out / "kotoba-gate.receipt")
    # These reach the native canonical ledger check before any new case output.
    for name, field, value in (("wrong-case-image", 5, "0" * 64),
                               ("wrong-case-fuel", 10, str(int(lines[10]) + 1))):
        changed = lines.copy()
        changed[field] = value
        probe = out / (name + ".kcg")
        probe.write_text("\n".join(changed) + "\n")
        run(name, [gate, probe, pin(probe)], 2, native_gate=True)
    report.update(status="PASS_EARLY_NATIVE_KOTOBA24_GATE", caseCount=24, namedRefusals=2,
                  nativeGateDecides=True, allLaterControllerAndRuntimeGatesRequired=True)
    (out / "observations.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--compiler", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    main(a.compiler.resolve(), a.output.resolve())
