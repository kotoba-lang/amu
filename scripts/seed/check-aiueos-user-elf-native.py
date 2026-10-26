#!/usr/bin/env python3
"""Observe the selfhost AIUEOS user ELF v1 scalar ABI and refusals.

The compiler emits the artifact. Python stages fixed source, checks bytes and
records exits; this is not a CPL3, signature or Itonami runtime qualification.
"""

import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path


SOURCE = "(ns aiueos-user-scalar (:export [main]))\n(defn main [] :i64 42)\n"
EFFECT = ("(ns aiueos-user-effect (:export [main]))\n"
          "(defn main [] :i64 (let [x (typed-cap-call :io/write :string :string \"denied\")] 42))\n")
PARAMETER = ("(ns aiueos-user-parameter (:export [main]))\n"
             "(defn main [goal :i64] :i64 goal)\n")
TARGET = "x86_64-aiueos-user-v1"


def pin(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def verify(blob):
    assert len(blob) == 8280, "unexpected image length"
    header = struct.unpack_from("<16sHHIQQQIHHHHHH", blob)
    assert header == (b"\x7fELF\x02\x01\x01" + bytes(9), 2, 62, 1,
                      0x220000, 64, 0, 0, 64, 56, 2, 0, 0, 0), "ELF identity"
    rx, rw = (struct.unpack_from("<IIQQQQQQ", blob, 64 + 56 * i) for i in range(2))
    assert rx[:5] == (1, 5, 4096, 0x220000, 0x220000)
    assert 64 < rx[5] == rx[6] <= 4096 and rx[7] == 4096
    assert rw == (1, 6, 8192, 0x221000, 0x221000, 88, 88, 4096)
    assert not any(blob[176:4096]) and not any(blob[4096 + rx[5]:8192])
    assert blob[4096:4103] == bytes.fromhex("4c8d0df90f0000")
    assert blob[0x1020:0x102c] == bytes.fromhex("b805000000488b7f500f05c3")
    context = bytearray(88)
    struct.pack_into("<Q", context, 8, 256)
    struct.pack_into("<Q", context, 48, 0x220020)
    assert blob[8192:] == context, "capabilities or runtime handle are nonzero"


def main(compiler, out):
    out.mkdir(parents=True, exist_ok=False)
    env = {"PATH": "/nonexistent", "KEXE_CAP_RESOURCES_35": str(out),
           "KEXE_STACK_BYTES": "8388608"}
    cases = []

    def compile_case(name, source, extra=(), expected=0):
        src, dst = out / f"{name}.kotoba", out / f"{name}.elf"
        src.write_text(source)
        argv = [str(compiler), "compile", str(src), "--target", TARGET,
                "--output", str(dst), *extra]
        result = subprocess.run(argv, cwd=out, env=env, capture_output=True, timeout=120)
        assert result.returncode == expected, (name, result.returncode, result.stderr[-300:])
        if expected:
            assert not dst.exists(), (name, "refusal left an artifact")
        else:
            assert not result.stderr, (name, result.stderr[-300:])
        cases.append({"name": name, "exit": result.returncode,
                      "stderr": result.stderr.decode().strip()})
        return dst

    image = compile_case("scalar", SOURCE)
    verify(image.read_bytes())
    mutation = bytearray(image.read_bytes())
    mutation[8208] = 1
    try:
        verify(mutation)
    except AssertionError:
        pass
    else:
        raise AssertionError("bitmap-1 mutation was accepted")
    compile_case("effect", EFFECT, expected=1)
    assert "E7101" in cases[-1]["stderr"], cases[-1]
    compile_case("parameter", PARAMETER, expected=1)
    assert "E7102" in cases[-1]["stderr"], cases[-1]
    compile_case("format", SOURCE, ("--format", "static"), expected=1)
    assert "E1 usage" in cases[-1]["stderr"], cases[-1]
    report = {"status": "PASS_AIUEOS_ZERO_CAP_USER_ELF_NATIVE",
              "compiler": pin(compiler), "source": pin(out / "scalar.kotoba"),
              "image": pin(image), "target": TARGET, "cases": cases,
              "bitmap1Rejected": True, "parameterRefused": True,
              "guestExecution": False,
              "signedAppAdmission": False, "itonamiTurn": False}
    (out / "aiueos-user-elf-native.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], report["image"]["sha256"][:16])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(), args.output.resolve())
