#!/usr/bin/env python3
"""Observe two Amu-generated scalar functions in a Kotoba-packaged Mach-O.

This is a Mac host observer for pinned artifacts. The Kotoba compiler and
packager produce the bytes; Python supplies no code, verdict, or fallback.
"""

import hashlib
import json
import platform
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPILER_SHA256 = "285c54f826d5f7f77db6827bc21c622c2c777cea252a1ba4816d8b01351807e1"
PACKAGER_SOURCE_SHA256 = "2171491e581fbe02dc6803c5810b874b08e37fcb97fe2feddb32e2487e699221"
PACKAGER_IMAGE_SHA256 = "cabb2cf4b0f67191134f481e5c2b313f24fd54c610b5b524c8e43d25893fe7b3"
CASES = {
    42: {
        "source": "b873c3421ab57a63e6e30dab20334d4cebe0cde6644c52a05df243ca8662f3a4",
        "kseed": "d9d93e2896184a1eff34a88f79cdfd9d51d96afd2af1f6d1b2020010ebc920bc",
        "raw": "5a39545c19169d735db93f1ac90d264dc566c59cadd0a7ee9dc29b07de29ce7d",
        "image": "966d5aef04d99fe954bd778421386f1ad5db8ce98117120d0c8ab8f421d85bfa",
        "code": "400580d2c0035fd6200020d4",
        "stem": "macos-generated-main",
    },
    43: {
        "source": "13ba8bb4a2ca67f24a40ad3ae0d947f1afc1653f4afca9837c989a6bea872d44",
        "kseed": "07e88862a381098133c32ad4d9ffe604aef43fd94ccef7c4c202b59d64d9b8c6",
        "raw": "1f5a129afecc5a9970eb110ac1ce49f4ac392d4716d784c81329698c759e66aa",
        "image": "7dd9ed4b207e6f6328c340561a4f0fbaa553125f288ba7b4d417d3178cfec751",
        "code": "600580d2c0035fd6200020d4",
        "stem": "macos-generated-main43",
    },
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_digest(path, expected):
    actual = sha256(path)
    if actual != expected:
        raise ValueError(f"unexpected digest for {path.name}: {actual}")
    return actual


def run(argv):
    return subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=10, check=False)


def check(artifacts, output):
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise RuntimeError("this executable observation requires an Apple Silicon Mac")
    assert_digest(ROOT / "seed/bootstrap/aarch64-linux-static-root.elf", COMPILER_SHA256)
    assert_digest(ROOT / "seed/macos-generated-main-smoke.kotoba", PACKAGER_SOURCE_SHA256)
    assert_digest(artifacts / "macos-generated-main-smoke.elf", PACKAGER_IMAGE_SHA256)
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for expected_exit, expected in CASES.items():
        stem = expected["stem"]
        source = ROOT / f"seed/macos-generated-main{expected_exit}.kotoba"
        kseed = artifacts / f"{stem}.kseed"
        raw = artifacts / f"{stem}.raw"
        unsigned = artifacts / f"{stem}.macho"
        assert_digest(source, expected["source"])
        assert_digest(kseed, expected["kseed"])
        assert_digest(raw, expected["raw"])
        assert_digest(unsigned, expected["image"])
        data = unsigned.read_bytes()
        if (len(data) != 16384 or data[:4] != b"\xcf\xfa\xed\xfe"
                or struct.unpack_from("<II", data, 4) != (0x0100000c, 0)
                or struct.unpack_from("<I", data, 12)[0] != 2
                or struct.unpack_from("<I", data, 24)[0] != 0x00200085
                or struct.unpack_from("<4I", data, 1024) !=
                (0x94000004, 0xd2800030, 0xf2a04010, 0xd4001001)
                or data[1040:1052] != raw.read_bytes()
                or raw.read_bytes().hex() != expected["code"]):
            raise ValueError(f"unexpected Amu-generated Mach-O structure for {expected_exit}")
        signed = output / f"{stem}-signed.macho"
        shutil.copyfile(unsigned, signed)
        signed.chmod(0o755)
        sign = run(["/usr/bin/codesign", "--force", "--sign", "-", str(signed)])
        verify = run(["/usr/bin/codesign", "--verify", "--strict", str(signed)])
        if sign.returncode or verify.returncode:
            raise RuntimeError(f"diagnostic signing failed for {expected_exit}")
        launched = run([str(signed)])
        if launched.returncode != expected_exit or launched.stdout or launched.stderr:
            raise RuntimeError(f"Amu-generated code returned the wrong Mac result for {expected_exit}")
        rows.append({"sourceSha256": expected["source"], "kseedSha256": expected["kseed"],
                     "rawSha256": expected["raw"], "unsignedSha256": expected["image"],
                     "signedSha256": sha256(signed), "expectedExit": expected_exit,
                     "observedExit": launched.returncode, "stdoutBytes": 0, "stderrBytes": 0})
    receipt = {"schema": "amu.macos-generated-main-smoke.v1", "status": "PASS_HOST_OBSERVATION",
               "compilerQualification": False, "externalSignerDiagnostic": True,
               "compilerSha256": COMPILER_SHA256, "packagerSourceSha256": PACKAGER_SOURCE_SHA256,
               "packagerImageSha256": PACKAGER_IMAGE_SHA256,
               "host": [platform.system(), platform.machine(), platform.mac_ver()[0]],
               "cases": rows}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: check-macos-generated-main-smoke.py ARTIFACT_DIR NEW_OUTPUT_DIR")
    print(json.dumps(check(Path(sys.argv[1]), Path(sys.argv[2]))))
