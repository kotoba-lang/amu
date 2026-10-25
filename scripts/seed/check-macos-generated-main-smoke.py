#!/usr/bin/env python3
"""Observe Amu-generated scalar and loop functions in a Kotoba Mach-O.

This is a Mac host observer for pinned artifacts. The Kotoba compiler and
packager produce the bytes; Python supplies no compiler, codegen, or native
gate-controller verdict.
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
PACKAGER_SOURCE_SHA256 = "6f912435d77cd4cf696ae6fa8f965b5f971713337bb0c34f828c647633e9f4cc"
PACKAGER_IMAGE_SHA256 = "002d61803c229bf81d8e4ee4993de80b2e553c4b1354b3045f83ccc514be059d"
CASES = (
    {
        "sourceName": "macos-generated-main42.kotoba",
        "source": "b873c3421ab57a63e6e30dab20334d4cebe0cde6644c52a05df243ca8662f3a4",
        "kseed": "d9d93e2896184a1eff34a88f79cdfd9d51d96afd2af1f6d1b2020010ebc920bc",
        "raw": "5a39545c19169d735db93f1ac90d264dc566c59cadd0a7ee9dc29b07de29ce7d",
        "image": "b8a5c5bcfa50c6c4aa7f7dd4be819024dcb881ae63d5d91b6bd64cf8f82b63d3",
        "rawBytes": 12,
        "expectedExit": 42,
        "stem": "macos-generated-main",
        "imageStem": "macos-generated-main-v2",
    },
    {
        "sourceName": "macos-generated-main43.kotoba",
        "source": "13ba8bb4a2ca67f24a40ad3ae0d947f1afc1653f4afca9837c989a6bea872d44",
        "kseed": "07e88862a381098133c32ad4d9ffe604aef43fd94ccef7c4c202b59d64d9b8c6",
        "raw": "1f5a129afecc5a9970eb110ac1ce49f4ac392d4716d784c81329698c759e66aa",
        "image": "4ff646d2fd295820918e9a8b346cef613deaad5f0ab42f5a6311b7889aa93b2c",
        "rawBytes": 12,
        "expectedExit": 43,
        "stem": "macos-generated-main43",
        "imageStem": "macos-generated-main43-v2",
    },
    {
        "sourceName": "macos-loop-main.kotoba",
        "source": "f4e6a0d98725fa680d5ab5b7e555851e151b549cdbeb3a00d730ff3b4350a2ad",
        "kseed": "4c0d0ee12bc9b47fef1eb4ffbe843bea90cf4c654af1a4eb379ba4a77cefd7e5",
        "raw": "a3229332968fd6b9eb8223800aba6496d7966fb80ddc7406032ddd6f11513327",
        "image": "1d635f61d6df8bac5cee0f4727130d94425a88fbf30af35f97504f4840ca191c",
        "rawBytes": 136,
        "expectedExit": 42,
        "stem": "macos-loop-main",
        "imageStem": "macos-loop-main-v2",
    },
)
LOW_FUEL_UNSIGNED_SHA256 = "ec5dd2f94ad1b56e2924b874bde4c410ced19303cb68ec99a050287ccbc34155"


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
    assert_digest(artifacts / "macos-generated-main-smoke-v2.elf", PACKAGER_IMAGE_SHA256)
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for expected in CASES:
        expected_exit = expected["expectedExit"]
        stem = expected["stem"]
        source = ROOT / "seed" / expected["sourceName"]
        kseed = artifacts / f"{stem}.kseed"
        raw = artifacts / f"{stem}.raw"
        unsigned = artifacts / f"{expected['imageStem']}.macho"
        assert_digest(source, expected["source"])
        assert_digest(kseed, expected["kseed"])
        assert_digest(raw, expected["raw"])
        assert_digest(unsigned, expected["image"])
        data = unsigned.read_bytes()
        if (len(data) != 16384 or data[:4] != b"\xcf\xfa\xed\xfe"
                or struct.unpack_from("<II", data, 4) != (0x0100000c, 0)
                or struct.unpack_from("<I", data, 12)[0] != 2
                or struct.unpack_from("<I", data, 24)[0] != 0x00200085
                or struct.unpack_from("<8I", data, 1024) !=
                (0xd10043ff, 0x910003e7, 0xd2807d08, 0xf90004e8,
                 0x94000004, 0xd2800030, 0xf2a04010, 0xd4001001)
                or len(raw.read_bytes()) != expected["rawBytes"]
                or data[1056:1056 + expected["rawBytes"]] != raw.read_bytes()):
            raise ValueError(f"unexpected Amu-generated Mach-O structure for {stem}")
        signed = output / f"{expected['imageStem']}-signed.macho"
        shutil.copyfile(unsigned, signed)
        signed.chmod(0o755)
        sign = run(["/usr/bin/codesign", "--force", "--sign", "-", str(signed)])
        verify = run(["/usr/bin/codesign", "--verify", "--strict", str(signed)])
        if sign.returncode or verify.returncode:
            raise RuntimeError(f"diagnostic signing failed for {expected_exit}")
        launched = run([str(signed)])
        if launched.returncode != expected_exit or launched.stdout or launched.stderr:
            raise RuntimeError(f"Amu-generated code returned the wrong Mac result for {expected_exit}")
        rows.append({"source": expected["sourceName"], "sourceSha256": expected["source"],
                     "kseedSha256": expected["kseed"],
                     "rawSha256": expected["raw"], "unsignedSha256": expected["image"],
                     "signedSha256": sha256(signed), "rawBytes": expected["rawBytes"],
                     "expectedExit": expected_exit,
                     "observedExit": launched.returncode, "stdoutBytes": 0, "stderrBytes": 0})
    low_fuel = bytearray((artifacts / "macos-loop-main-v2.macho").read_bytes())
    struct.pack_into("<I", low_fuel, 1032, 0xd2800028)
    if hashlib.sha256(low_fuel).hexdigest() != LOW_FUEL_UNSIGNED_SHA256:
        raise ValueError("low-fuel control does not match the reviewed bytes")
    low_path = output / "macos-loop-main-lowfuel-signed.macho"
    low_path.write_bytes(low_fuel)
    low_path.chmod(0o755)
    if (run(["/usr/bin/codesign", "--force", "--sign", "-", str(low_path)]).returncode
            or run(["/usr/bin/codesign", "--verify", "--strict", str(low_path)]).returncode):
        raise RuntimeError("low-fuel control signing failed")
    low_run = run([str(low_path)])
    if low_run.returncode != -5 or low_run.stdout or low_run.stderr:
        raise RuntimeError("fuel exhaustion did not reach the generated trap")
    receipt = {"schema": "amu.macos-generated-main-smoke.v2", "status": "PASS_HOST_OBSERVATION",
               "compilerQualification": False, "externalSignerDiagnostic": True,
               "compilerSha256": COMPILER_SHA256, "packagerSourceSha256": PACKAGER_SOURCE_SHA256,
               "packagerImageSha256": PACKAGER_IMAGE_SHA256,
               "host": [platform.system(), platform.machine(), platform.mac_ver()[0]],
               "cases": rows, "lowFuelUnsignedSha256": LOW_FUEL_UNSIGNED_SHA256,
               "lowFuelExit": low_run.returncode}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: check-macos-generated-main-smoke.py ARTIFACT_DIR NEW_OUTPUT_DIR")
    print(json.dumps(check(Path(sys.argv[1]), Path(sys.argv[2]))))
