#!/usr/bin/env python3
"""Verify an Amu-generated string main calling a native Darwin pair_new slot.

Python observes the Kotoba-built image and creates signed negative controls;
it does not produce the positive Mach-O or supply its runtime.
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
ROOT_SHA = "285c54f826d5f7f77db6827bc21c622c2c777cea252a1ba4816d8b01351807e1"
SOURCE_SHA = "0a558e151a6f66d4b5b8b60d88adbc116f954321f93b0625ed9d7f2f229f6ae2"
PACKAGER_SOURCE_SHA = "d78483b4fdc7b77bf1436c4a2649ac972fdedc632f987ed6bad45be203134013"
PACKAGER_SHA = "ad8f817148d97ec2507085698c680d1aabc76d1b80220204e5503e0d92601f6a"
RAW_SHA = "787c0617b95ea96ef390432cb69dae4632ab98af9b1516d19f06b82ef12e246f"
IMAGE_SHA = "9584e6e3d79e1e46ec1d89819eb6133cd5f4528d0114709a08c4aeb0daec7f5a"
DATA_BYTES = 65536
RAW_START = 1536
HELPER_START = 1280


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pin(path, wanted):
    actual = sha(path)
    if actual != wanted:
        raise ValueError(f"{path.name} SHA-256: {actual}, wanted {wanted}")


def word(blob, offset):
    return struct.unpack_from("<I", blob, offset)[0]


def admission(path, code):
    row = json.loads(path.read_text())
    if row.get("schema") != "amu.native-build-admission.v1" or row.get("exit") != code:
        raise ValueError(f"unexpected native admission: {path.name}")


def verify_image(image, raw):
    if len(raw) != 67 or raw[-3:] != b"abc" or len(image) != 81920:
        raise ValueError("unexpected payload or image extent")
    if image[:4] != b"\xcf\xfa\xed\xfe" or struct.unpack_from("<4I", image, 12) != (2, 7, 368, 0x00200005):
        raise ValueError("Mach-O header")
    commands = []
    at = 32
    for _ in range(7):
        command, size = struct.unpack_from("<II", image, at)
        commands.append((command, size))
        at += size
    if commands != [(25, 72)] * 4 + [(14, 32), (0x80000028, 24), (50, 24)] or at != 400:
        raise ValueError("Mach-O commands")
    if (struct.unpack_from("<4Q", image, 128) != (0x100000000, 16384, 0, 16384)
            or struct.unpack_from("<4Q", image, 200) != (0x100004000, DATA_BYTES, 16384, DATA_BYTES)
            or struct.unpack_from("<Q", image, 360)[0] != 1024):
        raise ValueError("Mach-O segment or entry")
    if image[RAW_START:RAW_START + len(raw)] != raw or any(image[16384:]):
        raise ValueError("generated code or initially zeroed data")
    if (word(raw, 32) != 0xf9401c10 or word(raw, 36) != 0xd63f0200
            or word(image, 1040) != 0xf9001ce8
            or word(image, HELPER_START + 8) != 0xf110013f
            or word(image, HELPER_START + 52) != 0xf9000109):
        raise ValueError("pair slot call, installation or count guard")
    if any(image[400:1024]) or any(image[1200:HELPER_START]) or any(image[HELPER_START + 64:RAW_START]):
        raise ValueError("unexpected executable padding")


def run(path):
    return subprocess.run([str(path)], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=15, check=False)


def signed(image, out):
    shutil.copyfile(image, out)
    out.chmod(0o755)
    for args in (("--force", "--sign", "-"), ("--verify", "--strict")):
        result = subprocess.run(["/usr/bin/codesign", *args, str(out)], capture_output=True, timeout=15)
        if result.returncode:
            raise RuntimeError(f"codesign {out.name}: {result.stderr!r}")
    return sha(out)


def control(original, folder, name, offset, replacement, expected):
    changed = bytearray(original)
    struct.pack_into("<I", changed, offset, replacement)
    unsigned = folder / (name + ".macho")
    unsigned.write_bytes(changed)
    executable = folder / (name + "-signed.macho")
    signature_sha = signed(unsigned, executable)
    result = run(executable)
    if result.returncode != expected or result.stdout or result.stderr:
        raise RuntimeError(f"{name}: exit={result.returncode}, stdout={result.stdout!r}, stderr={result.stderr!r}")
    return {"name": name, "exit": result.returncode, "unsignedSha256": sha(unsigned),
            "signedSha256": signature_sha}


def check(artifacts, output):
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise RuntimeError("Apple Silicon macOS required")
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    pin(ROOT / "seed/bootstrap/aarch64-linux-static-root.elf", ROOT_SHA)
    pin(ROOT / "seed/macos-pair-main.kotoba", SOURCE_SHA)
    pin(ROOT / "seed/macos-pair-runtime-packager.kotoba", PACKAGER_SOURCE_SHA)
    pin(artifacts / "packager.elf", PACKAGER_SHA)
    pin(artifacts / "pair.raw", RAW_SHA)
    pin(artifacts / "pair.macho", IMAGE_SHA)
    for name in ("compile", "extract", "packager-compile", "package"):
        admission(artifacts / f"{name}-admission.json", 0)
    admission(artifacts / "repeat-admission.json", 0)
    admission(artifacts / "short-admission.json", 2)
    if (artifacts / "short.macho").exists():
        raise ValueError("refused short input created an image")
    if (artifacts / "pair.macho").read_bytes() != (artifacts / "pair-repeat.macho").read_bytes():
        raise ValueError("repeat image differs")
    raw = (artifacts / "pair.raw").read_bytes()
    image = (artifacts / "pair.macho").read_bytes()
    verify_image(image, raw)
    output.mkdir(parents=True, exist_ok=False)
    positive = output / "pair-signed.macho"
    positive_sha = signed(artifacts / "pair.macho", positive)
    good = run(positive)
    if good.returncode != 42 or good.stdout or good.stderr:
        raise RuntimeError(f"pair main did not return 42: {good.returncode}")
    controls = [
        control(image, output, "missing-pair-slot", 1040, 0xd503201f, -11),
        control(image, output, "pair-capacity-zero", HELPER_START + 8, 0xf100013f, -5),
        control(image, output, "literal-c", RAW_START + 66, 0x64, -5),
    ]
    receipt = {
        "schema": "amu.macos-pair-runtime.v1", "status": "PASS_PAIR_SLOT_ONLY",
        "host": [platform.system(), platform.machine(), platform.mac_ver()[0]],
        "rootSha256": ROOT_SHA, "sourceSha256": SOURCE_SHA,
        "packagerSourceSha256": PACKAGER_SOURCE_SHA, "packagerSha256": PACKAGER_SHA,
        "rawSha256": RAW_SHA, "imageSha256": IMAGE_SHA,
        "signedSha256": positive_sha, "exit": good.returncode,
        "controls": controls, "repeatByteIdentical": True,
        "shortInputRefusedWithoutArtifact": True, "runtimeSlotsImplemented": [56],
        "fullCompilerExecuted": False, "linuxFreeBuildClosure": False,
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: check-macos-pair-runtime.py ARTIFACT_DIR NEW_OUTPUT_DIR")
    print(json.dumps(check(Path(sys.argv[1]), Path(sys.argv[2]))))
