#!/usr/bin/env python3
"""Observe the Kotoba-built Darwin mmap-backed pair arena on Apple Silicon."""

import importlib.util
import json
import platform
import resource
import struct
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("pair_observer", HERE / "check-macos-pair-runtime.py")
COMMON = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COMMON)

ROOT = HERE.parents[1]
SOURCE_SHA = "e1a9e364c7d4ca36e1b19c22512b8c935275e4caec6b9a1b8a7a97a851a09242"
PACKAGER_SHA = "1e7a2cfc30ce604362edf65705985db8f0abdb40867df7e463fa0fe2ceb17e45"
IMAGE_SHA = "956510d4df6ef5209bb81b3715c3362ca1e12d18cb25b53c5c5d1a4c1f99dafa"


def verify_image(image, raw):
    if len(image) != 32768 or len(raw) != 67 or raw[-3:] != b"abc":
        raise ValueError("unexpected image or generated payload extent")
    if image[:4] != b"\xcf\xfa\xed\xfe" or struct.unpack_from("<4I", image, 12) != (2, 7, 368, 0x00200005):
        raise ValueError("Mach-O header")
    at, commands = 32, []
    for _ in range(7):
        kind, length = struct.unpack_from("<II", image, at)
        commands.append((kind, length))
        at += length
    if commands != [(25, 72)] * 4 + [(14, 32), (0x80000028, 24), (50, 24)] or at != 400:
        raise ValueError("Mach-O commands")
    if (struct.unpack_from("<4Q", image, 128) != (0x100000000, 16384, 0, 16384)
            or struct.unpack_from("<4Q", image, 200) != (0x100004000, 16384, 16384, 16384)
            or struct.unpack_from("<Q", image, 360)[0] != 1024):
        raise ValueError("Mach-O segment or entry")
    if image[1536:1603] != raw or any(image[16384:]) or any(image[400:1024]):
        raise ValueError("guest code or zero-initialized data")
    w = COMMON.word
    if (w(raw, 32) != 0xf9401c10 or w(raw, 36) != 0xd63f0200
            or w(image, 1044) != 0xf9001e68
            or w(image, 1052) != 0xf9009268
            or w(image, 1060) != 0xd2a20001
            or w(image, 1068) != 0xd2820043
            or w(image, 1080) != 0xd28018b0
            or w(image, 1088) != 0xd4001001
            or w(image, 1092) != 0x54000602
            or w(image, 1096) != 0xf9009660
            or w(image, 1104) != 0xd2a02001
            or w(image, 1112) != 0xd2820043
            or w(image, 1124) != 0xd28018b0
            or w(image, 1132) != 0xd4001001
            or w(image, 1136) != 0x54000482
            or w(image, 1140) != 0xf9009a60
            or w(image, 1148) != 0xd503201f
            or w(image, 1416) != 0xd2a0200a
            or w(image, 1420) != 0xeb0a013f):
        raise ValueError("mmap ABI, fail-closed branch or pair count bound")
    if any(image[1288:1408]) or any(image[1476:1536]) or any(image[1603:16384]):
        raise ValueError("unexpected executable padding")


def check(artifacts, output):
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise RuntimeError("Apple Silicon macOS required")
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    COMMON.pin(ROOT / "seed/bootstrap/aarch64-linux-static-root.elf", COMMON.ROOT_SHA)
    COMMON.pin(ROOT / "seed/macos-pair-main.kotoba", COMMON.SOURCE_SHA)
    COMMON.pin(ROOT / "seed/macos-mapped-pair-runtime-packager.kotoba", SOURCE_SHA)
    COMMON.pin(artifacts / "packager-v2.elf", PACKAGER_SHA)
    COMMON.pin(artifacts / "pair.raw", COMMON.RAW_SHA)
    COMMON.pin(artifacts / "pair-v2.macho", IMAGE_SHA)
    for name, code in (("compile-v2", 0), ("package-v2", 0), ("repeat", 0), ("short", 2)):
        COMMON.admission(artifacts / (name + "-admission.json"), code)
    image = (artifacts / "pair-v2.macho").read_bytes()
    raw = (artifacts / "pair.raw").read_bytes()
    verify_image(image, raw)
    if image != (artifacts / "pair-repeat.macho").read_bytes() or (artifacts / "short.macho").exists():
        raise ValueError("repeat image differs or refused input created an image")
    output.mkdir(parents=True, exist_ok=False)
    signed_path = output / "pair-signed.macho"
    signed_sha = COMMON.signed(artifacts / "pair-v2.macho", signed_path)
    result = COMMON.run(signed_path)
    if result.returncode != 42 or result.stdout or result.stderr:
        raise RuntimeError(f"mmap-backed pair main did not exit 42: {result.returncode}")
    controls = [
        COMMON.control(image, output, "missing-slot", 1044, 0xd503201f, -11),
        COMMON.control(image, output, "pair-map-invalid-flags", 1068, 0xd2800003, -5),
        COMMON.control(image, output, "marks-map-invalid-flags", 1112, 0xd2800003, -5),
        COMMON.control(image, output, "pair-capacity-zero", 1416, 0xd2a0000a, -5),
        COMMON.control(image, output, "literal-c", 1602, 0x64, -5),
    ]
    receipt = {
        "schema": "amu.macos-mapped-pair-runtime.v1", "status": "PASS_MAPPED_PAIR_SLOT_ONLY",
        "host": [platform.system(), platform.machine(), platform.mac_ver()[0]],
        "rootSha256": COMMON.ROOT_SHA, "guestSourceSha256": COMMON.SOURCE_SHA,
        "packagerSourceSha256": SOURCE_SHA, "packagerSha256": PACKAGER_SHA,
        "rawSha256": COMMON.RAW_SHA, "imageSha256": IMAGE_SHA,
        "signedSha256": signed_sha, "exit": result.returncode,
        "pairArenaBytes": 268435456, "markArenaBytes": 16777216,
        "pairCapacity": 16777216, "controls": controls,
        "repeatByteIdentical": True, "shortInputRefusedWithoutArtifact": True,
        "runtimeSlotsImplemented": [56], "fullCompilerExecuted": False,
        "linuxFreeBuildClosure": False,
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: check-macos-mapped-pair-runtime.py ARTIFACT_DIR NEW_OUTPUT_DIR")
    print(json.dumps(check(Path(sys.argv[1]), Path(sys.argv[2]))))
