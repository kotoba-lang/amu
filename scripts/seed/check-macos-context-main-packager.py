#!/usr/bin/env python3
"""Read back a Kotoba-built Mach-O context and run bounded Mac controls.

The host observer checks bytes, signs copies and runs only the known loop.
It does not produce Mach-O or execute the full compiler image.
"""

import hashlib
import json
import platform
import resource
import shutil
import struct
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPILER_SHA256 = "285c54f826d5f7f77db6827bc21c622c2c777cea252a1ba4816d8b01351807e1"
SOURCE_SHA256 = "b936417af61efe8dfe13b657766408d7bb6d0776ad99e6834a9be2c5888f2edb"
PACKAGER_SHA256 = "4e4943db070b55da2669889366c22cd5eb1d1d615c2f42a76f3175d9d1751d4a"
LOOP_RAW_SHA256 = "a3229332968fd6b9eb8223800aba6496d7966fb80ddc7406032ddd6f11513327"
FULL_RAW_SHA256 = "164482b3310774e488e0cf84882ed05922fcaeec1f2a812e6440e1679e9fd09e"
LOOP_IMAGE_SHA256 = "2770aa20e995e688caa0461f7dcd35417387834108d1fe070333577271e27426"
FULL_IMAGE_SHA256 = "91d9a4c497f4e53ced5a30c5471233be764314e4d845dbcc9ff95c54019ee1e2"
DATA_BYTES = 16384
COMMANDS = [(25, 72)] * 4 + [(14, 32), (0x80000028, 24), (50, 24)]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pin(path, expected):
    actual = digest(path)
    if actual != expected:
        raise ValueError(f"unexpected SHA-256 for {path.name}: {actual}")
    return actual


def admission(artifacts, stem, expected):
    row = json.loads((artifacts / f"{stem}-admission.json").read_text())
    if row.get("schema") != "amu.native-build-admission.v1" or row.get("exit") != expected:
        raise ValueError(f"unexpected native admission for {stem}")


def wrapper(raw_bytes, text_bytes):
    pages = text_bytes // 4096
    adrp = 0x90000007 | ((pages & 3) << 29) | ((pages // 4) << 5)
    return (
        adrp, 0xd2807d08, 0xf90004e8, 0x100003a8, 0xf900c0e8,
        0xd2800008 | ((raw_bytes & 65535) << 5),
        0xf2a00008 | ((raw_bytes >> 16) << 5),
        0xf900c4e8, 0xf940c4e9, 0xeb08013f, 0x54000121,
        0xf940c0e9, 0x10000288, 0xeb08013f, 0x540000a1,
        0x94000011, 0xd2800030, 0xf2a04010, 0xd4001001, 0xd4200000,
    )


def check_macho(image, raw):
    text_bytes = ((1152 + len(raw) + 16383) // 16384) * 16384
    total_bytes = text_bytes + DATA_BYTES
    if (len(image) != total_bytes or image[:4] != b"\xcf\xfa\xed\xfe"
            or struct.unpack_from("<II", image, 4) != (0x0100000c, 0)
            or struct.unpack_from("<4I", image, 12) != (2, 7, 368, 0x00200005)):
        raise ValueError("Mach-O header or extent mismatch")
    commands = []
    at = 32
    for _ in range(7):
        command = struct.unpack_from("<II", image, at)
        commands.append(command)
        at += command[1]
    if (commands != COMMANDS or at != 400
            or struct.unpack_from("<4Q", image, 128)
            != (0x100000000, text_bytes, 0, text_bytes)
            or struct.unpack_from("<4Q", image, 200)
            != (0x100000000 + text_bytes, DATA_BYTES, text_bytes, DATA_BYTES)
            or struct.unpack_from("<4Q", image, 272)
            != (0x100000000 + total_bytes, DATA_BYTES, total_bytes, 0)
            or struct.unpack_from("<2I", image, 160) != (5, 5)
            or struct.unpack_from("<2I", image, 232) != (3, 3)
            or struct.unpack_from("<2I", image, 304) != (1, 1)
            or image[332:347] != b"/usr/lib/dyld\0\0"
            or struct.unpack_from("<Q", image, 360)[0] != 1024
            or struct.unpack_from("<20I", image, 1024) != wrapper(len(raw), text_bytes)
            or any(image[400:1024]) or any(image[1104:1152])
            or image[1152:1152 + len(raw)] != raw
            or any(image[1152 + len(raw):])):
        raise ValueError("segment, context, wrapper, payload or padding mismatch")
    return text_bytes, total_bytes


def run(argv, *, timeout=15):
    return subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=timeout, check=False)


def sign(source, dest):
    shutil.copyfile(source, dest)
    dest.chmod(0o755)
    for args in (("--force", "--sign", "-"), ("--verify", "--strict")):
        result = run(["/usr/bin/codesign", *args, str(dest)])
        if result.returncode:
            raise RuntimeError(f"codesign failed for {dest.name}: {result.stderr!r}")
    return digest(dest)


def trap_control(image, output, name, offset, word):
    data = bytearray(image.read_bytes())
    struct.pack_into("<I", data, offset, word)
    unsigned = output / f"{name}.macho"
    unsigned.write_bytes(data)
    signed = output / f"{name}-signed.macho"
    signed_hash = sign(unsigned, signed)
    result = run([str(signed)])
    if result.returncode != -5 or result.stdout or result.stderr:
        raise RuntimeError(f"{name} did not trap without output: {result.returncode}")
    return {"name": name, "unsignedSha256": digest(unsigned),
            "signedSha256": signed_hash, "exit": result.returncode}


def check(artifacts, output):
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise RuntimeError("Apple Silicon macOS required")
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    pin(ROOT / "seed/bootstrap/aarch64-linux-static-root.elf", COMPILER_SHA256)
    pin(ROOT / "seed/macos-context-main-packager.kotoba", SOURCE_SHA256)
    pin(artifacts / "macos-context-main-packager-v2.elf", PACKAGER_SHA256)
    loop_raw = (artifacts / "macos-loop-main.raw").read_bytes()
    full_raw = (artifacts / "full-compiler-main.raw").read_bytes()
    if (hashlib.sha256(loop_raw).hexdigest() != LOOP_RAW_SHA256
            or hashlib.sha256(full_raw).hexdigest() != FULL_RAW_SHA256):
        raise ValueError("unexpected Amu-generated raw code")
    loop_path = artifacts / "macos-loop-context-v2.macho"
    full_path = artifacts / "full-compiler-context-v2.macho"
    pin(loop_path, LOOP_IMAGE_SHA256)
    pin(full_path, FULL_IMAGE_SHA256)
    loop_text, loop_total = check_macho(loop_path.read_bytes(), loop_raw)
    full_text, full_total = check_macho(full_path.read_bytes(), full_raw)
    for stem, expected in (("compile-v2", 0), ("loop-v2", 0), ("full-v2", 0),
                           ("full-v2-repeat", 0), ("short-v2", 2), ("oversize-v2", 2)):
        admission(artifacts, stem, expected)
    if ((artifacts / "short-context-v2.macho").exists()
            or (artifacts / "oversize-context-v2.macho").exists()):
        raise ValueError("rejected input created an image")
    if full_path.read_bytes() != (artifacts / "full-compiler-context-v2-repeat.macho").read_bytes():
        raise ValueError("full-size context image not byte-identical on repeat")
    output.mkdir(parents=True, exist_ok=False)
    loop_signed = output / "macos-loop-context-signed.macho"
    loop_signed_hash = sign(loop_path, loop_signed)
    positive = run([str(loop_signed)])
    if positive.returncode != 42 or positive.stdout or positive.stderr:
        raise RuntimeError(f"Amu loop returned {positive.returncode} instead of 42")
    controls = [
        trap_control(loop_path, output, "low-fuel", 1028, 0xd2800028),
        trap_control(loop_path, output, "missing-code-base-store", 1040, 0xd503201f),
        trap_control(loop_path, output, "missing-code-length-store", 1052, 0xd503201f),
    ]
    full_signed = output / "full-compiler-context-signed.macho"
    full_signed_hash = sign(full_path, full_signed)
    receipt = {
        "schema": "amu.macos-context-main-packager.v1",
        "status": "PASS_CONTEXT_LOOP_AND_PACKAGING_ONLY",
        "host": [platform.system(), platform.machine(), platform.mac_ver()[0]],
        "compilerSha256": COMPILER_SHA256,
        "sourceSha256": SOURCE_SHA256,
        "packagerSha256": PACKAGER_SHA256,
        "loopRawSha256": LOOP_RAW_SHA256,
        "loopImageSha256": LOOP_IMAGE_SHA256,
        "loopSignedSha256": loop_signed_hash,
        "loopExit": positive.returncode,
        "loopTextBytes": loop_text,
        "loopTotalBytes": loop_total,
        "controls": controls,
        "fullRawSha256": FULL_RAW_SHA256,
        "fullRawBytes": len(full_raw),
        "fullImageSha256": FULL_IMAGE_SHA256,
        "fullSignedSha256": full_signed_hash,
        "fullTextBytes": full_text,
        "fullTotalBytes": full_total,
        "fullRepeatByteIdentical": True,
        "fullCompilerExecuted": False,
        "runtimeFunctionSlotsImplemented": False,
        "linuxFreeBuildClosure": False,
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: check-macos-context-main-packager.py ARTIFACT_DIR NEW_OUTPUT_DIR")
    print(json.dumps(check(Path(sys.argv[1]), Path(sys.argv[2]))))
