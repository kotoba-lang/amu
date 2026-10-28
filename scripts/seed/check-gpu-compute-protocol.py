#!/usr/bin/env python3
"""The :gpu/compute (wire 42) protocol table, tested through the loaderless compiler.

Builds one unit from tools/gpu_compute_protocol_test.kotoba's ns line, then
tools/gpu_compute_protocol.kotoba without its ns line, then the rest of the
test, the way seed/MANIFEST units are built. An Amu-produced static compiler
(--compiler: S3.elf from selfhost-bootstrap.py, or the pinned root, which
reproduces it) compiles it with --format static, and the image runs as an
ordinary Linux process. No GPU, no provider, no C compiler or loader.

Checked in both directions:
* the unit: every case passes, and the CASES line equals the number of
  expect calls counted in the test source;
* the control (CONTROL 1, one expected answer made wrong): exactly one case
  fails, the ALLOC 0 case, and the image reports it.

Python only orchestrates processes and hashes. The tests are Kotoba (ADR 0371
step 1). Run on Linux, e.g. on macOS through the podman machine:
  podman run --platform linux/arm64 -v REPO:REPO -v OUT:OUT python:3.12-alpine \
    python3 REPO/scripts/seed/check-gpu-compute-protocol.py \
    --compiler REPO/seed/bootstrap/aarch64-linux-static-root.elf --output OUT
"""
import argparse
import hashlib
import json
import platform
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TABLE = "tools/gpu_compute_protocol.kotoba"
TEST = "tools/gpu_compute_protocol_test.kotoba"
FUEL = 100000000
EXPECT_CALL = re.compile(r"\((expect|expect-i64|expect-str) ")
REPORT = re.compile(rb"\{:status :(\w+) :result (-?\d+) :fuel \{:initial (\d+) :remaining (\d+)\}\}")


def pin(path):
    data = Path(path).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def split_ns(text, name):
    first, rest = text.split("\n", 1)
    assert first.startswith("(ns ") and first.endswith("))") and first.count("(") == first.count(")"), (name, first)
    return first, rest


def units():
    table, test = (ROOT / TABLE).read_text(), (ROOT / TEST).read_text()
    _, table_body = split_ns(table, TABLE)
    test_ns, test_body = split_ns(test, TEST)
    counted = len(EXPECT_CALL.findall(test_body))
    assert counted > 0 and f"(def CASES {counted})" in test_body, ("CASES must equal the expect calls", counted)
    assert test_body.count("(def CONTROL 0)") == 1
    unit = "\n".join([test_ns, table_body, test_body])
    control = unit.replace("(def CONTROL 0)", "(def CONTROL 1)")
    return counted, unit, control


def main(compiler, output, target, seccomp_if_available=False):
    assert platform.system() == "Linux", "run on Linux"
    output.mkdir(parents=True, exist_ok=False)
    art, raw = output / "artifacts", output / "raw"
    art.mkdir()
    raw.mkdir()
    counted, unit, control = units()
    # the pinned root is committed without the execute bit; run a copy
    producer = art / "compiler.elf"
    producer.write_bytes(compiler.read_bytes())
    producer.chmod(0o755)
    run_env = {"PATH": "/usr/bin:/bin", "KEXE_STRUCTURED_REPORT": "1", "KEXE_FUEL": str(FUEL)}
    if seccomp_if_available:
        run_env["KEXE_SECCOMP"] = "if-available"

    def build_and_run(name, source):
        src, elf = art / (name + ".kotoba"), art / (name + ".elf")
        src.write_text(source)
        c = subprocess.run([str(producer), "compile", str(src), "--target", target, "--output", str(elf), "--format", "static"],
                           cwd=art, env={"PATH": "/usr/bin:/bin", "KEXE_CAP_RESOURCES_35": str(art)},
                           capture_output=True, timeout=300)
        (raw / (name + ".compile.stdout")).write_bytes(c.stdout)
        (raw / (name + ".compile.stderr")).write_bytes(c.stderr)
        assert c.returncode == 0 and not c.stderr and b":ok true" in c.stdout, (name, c.returncode, c.stderr)
        elf.chmod(0o700)
        x = subprocess.run([str(elf)], cwd=art, env=run_env, capture_output=True, timeout=120)
        (raw / (name + ".run.stdout")).write_bytes(x.stdout)
        (raw / (name + ".run.stderr")).write_bytes(x.stderr)
        assert x.returncode == 0 and not x.stderr, (name, x.returncode, x.stderr)
        lines = x.stdout.decode().splitlines()
        report = REPORT.search(x.stdout)
        assert report and report.group(1) == b"ok", (name, x.stdout[-400:])
        cases = [int(l.split()[1]) for l in lines if l.startswith("CASES ")]
        failed = [int(l.split()[1]) for l in lines if l.startswith("FAILED ")]
        fails = [l for l in lines if l.startswith("FAIL ")]
        assert len(cases) == 1 and len(failed) == 1, (name, lines[-5:])
        result = int(report.group(2))
        row = dict(name=name, source=pin(src), image=pin(elf), result=result,
                   fuelUsed=int(report.group(3)) - int(report.group(4)),
                   cases=cases[0], failed=failed[0], failLines=fails)
        return row, result, cases[0], failed[0], fails

    u, result, cases, failed, fails = build_and_run("protocol-test", unit)
    assert cases == counted and failed == 0 and result == 0 and not fails, u
    k, result, cases, failed, fails = build_and_run("protocol-control", control)
    assert cases == counted and failed == 1 and result == 1, k
    assert len(fails) == 1 and fails[0].startswith("FAIL ALLOC 0 => "), fails
    report = dict(status="PASS_GPU_COMPUTE_PROTOCOL_V1", target=target, compiler=pin(compiler),
                  host=[platform.system(), platform.machine(), platform.release()],
                  executionNative=target.split("-")[0] == {"arm64": "aarch64", "AMD64": "x86_64"}.get(platform.machine(), platform.machine()),
                  imageSeccomp="if-available" if seccomp_if_available else "required",
                  sources={TABLE: pin(ROOT / TABLE), TEST: pin(ROOT / TEST)},
                  casesCounted=counted, runs=[u, k], cCompilerOrLoader=False,
                  notCovered=["refusal 3 (request-too-long): a runtime value cannot exceed one; frames are checked by the runtime and provider (ADR 0371 steps 2 and 6)",
                              "refusals 19..35 are named and formatted here and decided by the provider (ADR 0371 step 6)"])
    (output / "gpu-compute-protocol.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], target, counted, "cases", "control failed 1", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--compiler", type=Path, required=True, help="an Amu-produced static compiler (S3.elf or the pinned root)")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target", choices=["aarch64-linux", "x86_64-linux"], default="aarch64-linux")
    parser.add_argument("--seccomp-if-available", action="store_true",
                        help="run the test images with KEXE_SECCOMP=if-available (qemu-user has no seccomp); recorded")
    args = parser.parse_args()
    main(args.compiler.resolve(), args.output.resolve(), args.target, args.seccomp_if_available)
