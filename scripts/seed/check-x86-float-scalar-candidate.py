#!/usr/bin/env python3
"""Observe candidate float scalar ELF results on a reported Linux x86_64 host.

This is a bounded diagnostic, not compiler adoption or full float qualification.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import re
import resource
import shutil
import signal
import struct
import subprocess


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "test/fixtures/selfhost/x86-float"


def digest(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--compiler", type=Path, required=True)
    p.add_argument("--compiler-sha256", required=True)
    p.add_argument("--cross-receipt", type=Path, required=True)
    p.add_argument("--cross-sha256", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise SystemExit("reported native Linux x86_64 host required")
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    compiler = a.compiler.resolve(strict=True)
    if not compiler.is_file() or digest(compiler)["sha256"] != a.compiler_sha256:
        raise SystemExit("compiler pin mismatch")
    cross_path = a.cross_receipt.resolve(strict=True)
    cross_pin = digest(cross_path)
    if cross_pin["sha256"] != a.cross_sha256:
        raise SystemExit("cross receipt pin mismatch")
    cross = json.loads(cross_path.read_text())
    if (cross.get("status") != "MAC_NATIVE_CROSS_CANDIDATES_UNADOPTED" or
            cross.get("x86FullCompiler") != digest(compiler)):
        raise SystemExit("unexpected candidate identity")
    spec = importlib.util.spec_from_file_location("cross_native_gate", ROOT / "scripts/seed/check-macos-cross-linux-native.py")
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    gate.source_unity(ROOT / "seed/FULL-MANIFEST", cross["fullSource"])
    output = a.output.absolute()
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    env = {"PATH": "/nonexistent", "KEXE_ALLOW": "35,37,38,39",
           "KEXE_CAP_RESOURCES_35": str(output), "KEXE_STACK_BYTES": "8388608"}
    rows = []

    def run(name, argv, *, guest=False):
        result = subprocess.run([str(x) for x in argv], cwd=output,
                                env={"PATH": "/nonexistent"} if guest else env,
                                capture_output=True, timeout=900, check=False)
        for stream in ("stdout", "stderr"):
            (output / (name + "." + stream)).write_bytes(getattr(result, stream))
        rows.append({"name": name, "exit": result.returncode,
                     "stdout": digest(output / (name + ".stdout")),
                     "stderr": digest(output / (name + ".stderr"))})
        return result

    for name, value, should_trap in (("assert-valid", 1065353216, False),
                                     ("assert-out-of-range", 2147483648, True)):
        src, image = output / (name + ".kotoba"), output / (name + ".elf")
        src.write_text("(ns native.assert-test (:export [main]))\n"
                       "(defn main [] :i64 (do (assert (and (>= " + str(value) +
                       " -2147483648) (<= " + str(value) + " 2147483647))) 42))\n")
        built = run(name + "-compile", [compiler, "compile", src, "--target", "x86_64-linux", "--output", image])
        if built.returncode != 0 or not image.is_file():
            raise SystemExit(name + ": compile failed")
        image.chmod(0o700)
        result = run(name + "-run", [image], guest=True)
        if should_trap:
            if result.returncode != -signal.SIGILL or result.stdout:
                raise SystemExit(name + ": expected SIGILL trap missing")
        elif result.returncode != 0 or result.stderr or result.stdout != (42).to_bytes(8, "little", signed=True):
            raise SystemExit(name + ": positive result mismatch")

    for name, value, should_trap in (("f32-min", -2147483648, False),
                                     ("f32-max", 2147483647, False),
                                     ("f32-below-min", -2147483649, True),
                                     ("f32-above-max", 2147483648, True)):
        src, image = output / (name + ".kotoba"), output / (name + ".elf")
        src.write_text("(ns native.f32-boundary (:export [main]))\n"
                       "(defn main [] :i64 (f32-to-bits (f32-from-bits " + str(value) + ")))\n")
        built = run(name + "-compile", [compiler, "compile", src, "--target", "x86_64-linux", "--output", image])
        if built.returncode != 0 or not image.is_file():
            raise SystemExit(name + ": compile failed")
        image.chmod(0o700)
        result = run(name + "-run", [image], guest=True)
        if should_trap:
            if result.returncode != -signal.SIGILL or result.stdout:
                raise SystemExit(name + ": expected SIGILL trap missing")
        elif result.returncode != 0 or result.stderr or result.stdout != value.to_bytes(8, "little", signed=True):
            raise SystemExit(name + ": boundary result mismatch")

    cases = json.loads((ROOT / "seed/float-cases.json").read_text())["cases"]
    examples = [(row["name"], row["source"], row["result"]) for row in cases]
    examples.append(("full-x86-float", (FIXTURES / "native/x86_float_test.kotoba").read_text(), 511))
    artifacts = []
    for name, source, expected in examples:
        if not re.fullmatch(r"[a-z0-9-]+", name):
            raise SystemExit("invalid case name")
        src, image = output / (name + ".kotoba"), output / (name + ".elf")
        src.write_text(source)
        built = run(name + "-compile", [compiler, "compile", src, "--target", "x86_64-linux", "--output", image])
        if built.returncode != 0 or not image.is_file():
            raise SystemExit(name + ": compile failed")
        data = image.read_bytes()
        if len(data) < 64 or data[:8] != b"\x7fELF\x02\x01\x01\0" or struct.unpack_from("<HH", data, 16) != (2, 62):
            raise SystemExit(name + ": unexpected ELF target")
        offset = struct.unpack_from("<Q", data, 32)[0]
        size, count = struct.unpack_from("<HH", data, 54)
        if size != 56 or not 0 < count <= 16 or offset + size * count > len(data):
            raise SystemExit(name + ": invalid ELF program headers")
        if any(struct.unpack_from("<I", data, offset + i * size)[0] in (2, 3) for i in range(count)):
            raise SystemExit(name + ": dynamic interpreter or dynamic section refused")
        image.chmod(0o700)
        result = run(name + "-run", [image], guest=True)
        if result.returncode != 0 or result.stderr or result.stdout != int(expected).to_bytes(8, "little", signed=True):
            raise SystemExit(name + ": execution mismatch")
        artifacts.append({"name": name, "source": digest(src), "image": digest(image),
                          "expectedI64": expected})

    for name, diagnostic in (("public-floating-result", b"E2104 type mismatch"),
                             ("public-floating-parameter", b"E2104 type mismatch"),
                             ("scalar-handle", b"E7102 unsupported scalar profile")):
        src = output / (name + ".kotoba")
        image = output / (name + ".elf")
        shutil.copyfile(FIXTURES / ("refusals/" + name + ".kotoba"), src)
        result = run(name + "-refusal", [compiler, "compile", src, "--target", "x86_64-linux", "--output", image])
        if result.returncode == 0 or image.exists() or diagnostic not in result.stdout + result.stderr:
            raise SystemExit(name + ": expected admission refusal missing")

    if digest(compiler)["sha256"] != a.compiler_sha256:
        raise SystemExit("compiler changed during observation")
    if digest(cross_path) != cross_pin:
        raise SystemExit("cross receipt changed during observation")
    report = {"status": "PASS_X86_FLOAT_SCALAR_CANDIDATE", "compiler": digest(compiler),
              "crossReceipt": cross_pin, "sourceUnity": cross["fullSource"]["unity"],
              "floatCorpus": digest(ROOT / "seed/float-cases.json"),
              "fixture": digest(FIXTURES / "native/x86_float_test.kotoba"),
              "observer": digest(Path(__file__)), "host": {"system": platform.system(),
              "machine": platform.machine(), "release": platform.release()},
              "cases": len(examples), "artifacts": artifacts, "calls": rows, "publicReleaseReady": False,
              "fullNativeCorpusQualified": False}
    (output / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], len(examples))


if __name__ == "__main__":
    main()
