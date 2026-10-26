#!/usr/bin/env python3
"""Observe a Kotoba-emitted arm64 Mach-O in the macOS loader.

The external codesign step signs diagnostic copies only. This does not build
or qualify an Amu macOS compiler, a self-rebuild, or a release artifact.
"""

import hashlib
import json
import os
import platform
import shutil
import struct
import subprocess
import sys
from pathlib import Path

EXPECTED_UNSIGNED_SHA256 = "b4f151d148cdb76b9c22b94f1278c57a14ddde0a7c6174ab68facc5bd50b93a7"
EXPECTED_CODE = (
    0xd10043ff, 0xd2800000, 0x910003e1, 0xd2800202,
    0xd2800070, 0xf2a04010, 0xd4001001, 0x54000202,
    0xf100001f, 0x5400018d, 0xaa0003e2, 0xd2800020,
    0x910003e1, 0xd2800090, 0xf2a04010, 0xd4001001,
    0x540000e2, 0xeb02001f, 0x540000a1, 0xd2800540,
    0x14000004, 0xd2800560, 0x14000002, 0xd2800580,
    0xd2800030, 0xf2a04010, 0xd4001001, 0xd65f03c0,
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv, *, input_bytes=None, timeout=10, close_fd=None):
    source = {"stdin": subprocess.DEVNULL} if input_bytes is None else {"input": input_bytes}
    if close_fd is not None:
        source["preexec_fn"] = lambda: os.close(close_fd)
    return subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=timeout, check=False, **source)


def check(unsigned, output):
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise RuntimeError("this loader smoke requires an Apple Silicon Mac")
    data = unsigned.read_bytes()
    if (len(data) != 16384 or data[:4] != b"\xcf\xfa\xed\xfe"
            or struct.unpack_from("<II", data, 4) != (0x0100000c, 0)
            or struct.unpack_from("<I", data, 12)[0] != 2
            or struct.unpack_from("<II", data, 16) != (8, 400)
            or struct.unpack_from("<I", data, 24)[0] != 0x00200085
            or struct.unpack_from("<28I", data, 1024) != EXPECTED_CODE):
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
    launched = run([str(signed)], input_bytes=b"abc\n")
    eof = run([str(signed)], input_bytes=b"")
    bounded = run([str(signed)], input_bytes=b"0123456789abcdefZ")
    read_error = run([str(signed)], close_fd=0)
    write_error = run([str(signed)], input_bytes=b"abc\n", close_fd=1)
    if (launched.returncode != 42 or launched.stdout != b"abc\n" or launched.stderr
            or eof.returncode != 43 or eof.stdout or eof.stderr
            or bounded.returncode != 42 or bounded.stdout != b"0123456789abcdef"
            or bounded.stderr):
        raise RuntimeError("Kotoba-emitted Mach-O failed bounded Darwin read/write/exit")
    if any(r.returncode != 44 or r.stdout or r.stderr for r in (read_error, write_error)):
        raise RuntimeError("Darwin read/write errors were not refused without output")

    broken = bytearray(data)
    struct.pack_into("<I", broken, 24, 0x00200000)
    refused.write_bytes(broken)
    refused.chmod(0o755)
    negative_sign = run(["/usr/bin/codesign", "--force", "--sign", "-", str(refused)])
    negative_verify = run(["/usr/bin/codesign", "--verify", "--strict", str(refused)])
    if negative_sign.returncode or negative_verify.returncode:
        raise RuntimeError("negative image did not pass independent signing")
    negative = run([str(refused)], input_bytes=b"abc\n")
    if negative.returncode != -9 or negative.stdout or negative.stderr:
        raise RuntimeError("missing dynamic-link flags did not give the observed pre-entry kill")
    if sha256(unsigned) != source_digest:
        raise RuntimeError("unsigned Kotoba image changed during observation")
    receipt = {
        "schema": "amu.macos-exec-smoke.v3",
        "compilerQualification": False,
        "externalSignerDiagnostic": True,
        "unsignedSha256": source_digest,
        "signedSha256": sha256(signed),
        "host": [platform.system(), platform.machine()],
        "positiveExit": launched.returncode,
        "positiveStdout": launched.stdout.decode("ascii"),
        "eofExit": eof.returncode,
        "boundedExit": bounded.returncode,
        "boundedStdout": bounded.stdout.decode("ascii"),
        "closedStdinExit": read_error.returncode,
        "closedStdoutExit": write_error.returncode,
        "missingDyldFlagsExit": negative.returncode,
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: check-macos-exec-smoke.py UNSIGNED_MACHO NEW_OUTPUT_DIR")
    print(json.dumps(check(Path(sys.argv[1]), Path(sys.argv[2]))))
