#!/usr/bin/env python3
"""Observe a Kotoba-emitted arm64 Mach-O in the macOS loader.

The external codesign step signs diagnostic copies only. This does not build
or qualify an Amu macOS compiler, a self-rebuild, or a release artifact.
"""

import hashlib
import json
import platform
import shutil
import struct
import subprocess
import sys
from pathlib import Path

EXPECTED_UNSIGNED_SHA256 = "7480b497c217dc2f3249d4bc50ef2516b468559b84b16e5c231202be8d547d92"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv, *, timeout=10):
    return subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=timeout, check=False)


def check(unsigned, output):
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise RuntimeError("this loader smoke requires an Apple Silicon Mac")
    data = unsigned.read_bytes()
    if (len(data) != 16384 or data[:4] != b"\xcf\xfa\xed\xfe"
            or struct.unpack_from("<II", data, 4) != (0x0100000c, 0)
            or struct.unpack_from("<I", data, 12)[0] != 2
            or struct.unpack_from("<I", data, 24)[0] != 0x00200085
            or struct.unpack_from("<II", data, 1024) != (0xd2800540, 0xd65f03c0)):
        raise ValueError("unexpected unsigned Kotoba Mach-O smoke image")
    source_digest = sha256(unsigned)
    if source_digest != EXPECTED_UNSIGNED_SHA256:
        raise ValueError("unsigned Kotoba Mach-O does not match the reviewed fixture")
    output.mkdir(parents=True, exist_ok=False)
    signed = output / "kotoba-macos-smoke-signed.macho"
    refused = output / "kotoba-macos-smoke-no-dyld-flags.macho"
    shutil.copyfile(unsigned, signed)
    signed.chmod(0o755)
    sign = run(["/usr/bin/codesign", "--force", "--sign", "-", str(signed)])
    verify = run(["/usr/bin/codesign", "--verify", "--strict", str(signed)])
    if sign.returncode or verify.returncode:
        raise RuntimeError("diagnostic Mac code signing failed")
    launched = run([str(signed)])
    if launched.returncode != 42 or launched.stdout or launched.stderr:
        raise RuntimeError("Kotoba-emitted Mach-O did not return 42 on macOS")

    broken = bytearray(data)
    struct.pack_into("<I", broken, 24, 0x00200000)
    refused.write_bytes(broken)
    refused.chmod(0o755)
    negative_sign = run(["/usr/bin/codesign", "--force", "--sign", "-", str(refused)])
    negative_verify = run(["/usr/bin/codesign", "--verify", "--strict", str(refused)])
    if negative_sign.returncode or negative_verify.returncode:
        raise RuntimeError("negative image did not pass independent signing")
    negative = run([str(refused)])
    if negative.returncode == 42:
        raise RuntimeError("missing dynamic-link flags did not change launch")
    if sha256(unsigned) != source_digest:
        raise RuntimeError("unsigned Kotoba image changed during observation")
    receipt = {
        "schema": "amu.macos-exec-smoke.v1",
        "compilerQualification": False,
        "externalSignerDiagnostic": True,
        "unsignedSha256": source_digest,
        "signedSha256": sha256(signed),
        "host": [platform.system(), platform.machine()],
        "positiveExit": launched.returncode,
        "missingDyldFlagsExit": negative.returncode,
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: check-macos-exec-smoke.py UNSIGNED_MACHO NEW_OUTPUT_DIR")
    print(json.dumps(check(Path(sys.argv[1]), Path(sys.argv[2]))))
