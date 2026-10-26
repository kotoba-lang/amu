#!/usr/bin/env python3
"""Observe a Kotoba-packed full-size Amu main without launching it.

Python checks pinned bytes and Darwin's signature acceptance. It is not a
compiler, Mach-O producer, runtime, or evidence that the full compiler runs.
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
PACKAGER_COMPILER_SHA256 = "285c54f826d5f7f77db6827bc21c622c2c777cea252a1ba4816d8b01351807e1"
PACKAGER_SOURCE_SHA256 = "112da64149a141659a4c1857e63fdea8904382188e03c99816df36858527fb42"
PACKAGER_IMAGE_SHA256 = "ad09cdae55a174c4560e70c1f1a50065243dbab0cca2cc4e596e860d09cfcb25"
FULL_KSEED_SHA256 = "dec8649a9d095b1f144ecf86dd176a32703a637c4999aa634537978369bc4c18"
FULL_EXTRACTOR_SHA256 = "1610a3461bed66a17b6c6de7a2bf9f05a37ed60eb012291f0e1e61a7bbf02753"
FULL_RAW_SHA256 = "164482b3310774e488e0cf84882ed05922fcaeec1f2a812e6440e1679e9fd09e"
FULL_IMAGE_SHA256 = "520be6af651d71c459fe48a95c99598aba51833a1b9585c66a19d5f21d75a0dc"
SMALL_IMAGE_SHA256 = "de3c61bf00d32ec5ad82b155292437aba0cbd83636c23e5f08bd7d3e5b2e35ef"
COMMANDS = [(25, 72), (25, 72), (25, 72), (14, 32), (0x80000028, 24), (50, 24)]
WRAPPER = (0xd10043ff, 0x910003e7, 0xd2807d08, 0xf90004e8,
           0x94000004, 0xd2800030, 0xf2a04010, 0xd4001001)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pin(path, expected):
    actual = digest(path)
    if actual != expected:
        raise ValueError(f"unexpected SHA-256 for {path.name}: {actual}")
    return actual


def admission(artifacts, stem, code):
    row = json.loads((artifacts / f"{stem}-admission.json").read_text())
    if row.get("schema") != "amu.native-build-admission.v1" or row.get("exit") != code:
        raise ValueError(f"unexpected native admission result for {stem}")
    return row


def check_macho(data, raw):
    image_bytes = ((1056 + len(raw) + 16383) // 16384) * 16384
    if (len(data) != image_bytes or data[:4] != b"\xcf\xfa\xed\xfe"
            or struct.unpack_from("<II", data, 4) != (0x0100000c, 0)
            or struct.unpack_from("<4I", data, 12) != (2, 6, 296, 0x00200005)):
        raise ValueError("unexpected Mach-O header or image extent")
    commands = []
    at = 32
    for _ in range(6):
        command = struct.unpack_from("<II", data, at)
        commands.append(command)
        at += command[1]
    if (commands != COMMANDS or at != 328
            or data[260:275] != b"/usr/lib/dyld\0\0"
            or struct.unpack_from("<QQ", data, 128) != (0x100000000, image_bytes)
            or struct.unpack_from("<Q", data, 152)[0] != image_bytes
            or struct.unpack_from("<QQQQ", data, 200)
            != (0x100000000 + image_bytes, 16384, image_bytes, 0)
            or struct.unpack_from("<Q", data, 288)[0] != 1024
            or struct.unpack_from("<8I", data, 1024) != WRAPPER
            or any(data[328:1024])
            or data[1056:1056 + len(raw)] != raw
            or any(data[1056 + len(raw):])):
        raise ValueError("Mach-O commands, wrapper, payload, or padding mismatch")
    return image_bytes


def run(argv):
    result = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=60, check=False)
    if result.returncode:
        raise RuntimeError(f"{argv[0]} failed: {result.stderr.decode(errors='replace')}")
    return result


def check(artifacts, kseed, extractor, output):
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise RuntimeError("Apple Silicon macOS required for signature readback")
    pin(ROOT / "seed/bootstrap/aarch64-linux-static-root.elf", PACKAGER_COMPILER_SHA256)
    pin(ROOT / "seed/macos-large-main-packager.kotoba", PACKAGER_SOURCE_SHA256)
    pin(artifacts / "macos-large-main-packager.elf", PACKAGER_IMAGE_SHA256)
    pin(kseed, FULL_KSEED_SHA256)
    pin(extractor, FULL_EXTRACTOR_SHA256)
    raw_path = artifacts / "full-compiler-main.raw"
    raw_hash = pin(raw_path, FULL_RAW_SHA256)
    pin(artifacts / "full-compiler-main-reextract.raw", FULL_RAW_SHA256)
    image_path = artifacts / "full-compiler-main.macho"
    image_hash = pin(image_path, FULL_IMAGE_SHA256)
    pin(artifacts / "macos-loop-main-large.macho", SMALL_IMAGE_SHA256)
    admission(artifacts, "compile", 0)
    admission(artifacts, "small", 0)
    admission(artifacts, "full", 0)
    admission(artifacts, "full-repeat", 0)
    admission(artifacts, "reextract", 0)
    admission(artifacts, "short", 2)
    admission(artifacts, "oversize", 2)
    if ((artifacts / "short-main.macho").exists()
            or (artifacts / "oversize-main.macho").exists()):
        raise ValueError("rejected raw input produced an image")
    if image_path.read_bytes() != (artifacts / "full-compiler-main-repeat.macho").read_bytes():
        raise ValueError("full-size Kotoba packaging was not byte-identical")
    if raw_path.read_bytes() != (artifacts / "full-compiler-main-reextract.raw").read_bytes():
        raise ValueError("F1 re-extraction differs from package input")
    raw = raw_path.read_bytes()
    image_bytes = check_macho(image_path.read_bytes(), raw)
    otool = run(["/usr/bin/otool", "-L", str(image_path)]).stdout.decode()
    if "libSystem" in otool:
        raise ValueError("diagnostic image unexpectedly links libSystem")
    output.mkdir(parents=True, exist_ok=False)
    signed = output / "full-compiler-main-signed.macho"
    shutil.copyfile(image_path, signed)
    signed.chmod(0o755)
    run(["/usr/bin/codesign", "--force", "--sign", "-", str(signed)])
    run(["/usr/bin/codesign", "--verify", "--strict", str(signed)])
    receipt = {
        "schema": "amu.macos-large-main-packager.v1",
        "status": "PASS_PACKAGING_AND_SIGNABILITY_ONLY",
        "fullCompilerExecuted": False,
        "darwinCapabilityRuntime": False,
        "linuxFreeBuildClosure": False,
        "host": [platform.system(), platform.machine(), platform.mac_ver()[0]],
        "packagerCompilerSha256": PACKAGER_COMPILER_SHA256,
        "packagerSourceSha256": PACKAGER_SOURCE_SHA256,
        "packagerImageSha256": PACKAGER_IMAGE_SHA256,
        "fullKseedSha256": FULL_KSEED_SHA256,
        "fullExtractorSha256": FULL_EXTRACTOR_SHA256,
        "reextractedRawByteIdentical": True,
        "rawSha256": raw_hash,
        "rawBytes": len(raw),
        "unsignedSha256": image_hash,
        "unsignedBytes": image_bytes,
        "signedSha256": digest(signed),
        "smallImageMatchesV3": True,
        "repeatImageByteIdentical": True,
        "shortRawExit": 2,
        "oversizeRawExit": 2,
        "rejectedImagesExist": False,
        "codeSignatureStrictVerified": True,
        "libSystemLoadCommands": 0,
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit("usage: check-macos-large-main-packager.py ARTIFACT_DIR F1_KSEED F1_ELF NEW_OUTPUT_DIR")
    print(json.dumps(check(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))))
