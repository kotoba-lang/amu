#!/usr/bin/env python3
"""Observe Kotoba-emitted Mac capability runtime images on an arm64 Mac.

Python checks and signs copies; it does not emit the guest, runtime payload,
or Mach-O image and is not a native gate-controller verdict.
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
PINS = {
    "root": (ROOT / "seed/bootstrap/aarch64-linux-static-root.elf",
             "285c54f826d5f7f77db6827bc21c622c2c777cea252a1ba4816d8b01351807e1"),
    "guestSource": (ROOT / "seed/macos-io-main.kotoba",
                    "e8c575e4e4e47980e82b250d13e43230c4a0996554e61f57df5b0696617e011a"),
    "payloadSource": (ROOT / "seed/macos-io-runtime-payload.kotoba",
                      "3ce09602a432ef2dcc1eab4ee6e77271a5756ac9bce1ac576b333d7641d2e67d"),
    "packagerSource": (ROOT / "seed/macos-generated-main-smoke.kotoba",
                       "eefcf0f2470f7168693990d72853a8b1d51245f17acf269fe31616f7665982bc"),
}
ARTIFACT_PINS = {
    "guestKseed": ("macos-io-main-v2.kseed", "3cc65f8ed2b4439ed8733be692076e9aa2d511cc876b3a0fbaa9b4a274715ab9"),
    "guestRaw": ("macos-io-main-v2.raw", "b8999afcfe0ab0a2198471475dfa55109e6bf2a0749e32de138e0f244b560e9c"),
    "payloadEmitter": ("macos-io-runtime-payload.elf", "619282503f834452567c9e839f796ed2ccb442852f8a7e9e36c898e0e01af44d"),
    "packager": ("macos-generated-main-smoke-v3.elf", "693dbbe7ae5873b9f8880531fd575502318785fb34f54d856fc2db96392e3c46"),
    "allowPayload": ("macos-io-runtime-allow.raw", "fdeb5c62af6c9f838415f08c646b9abd3cf07e444041ad44c71367d4e1f238eb"),
    "denyPayload": ("macos-io-runtime-deny.raw", "e45bbcf0784c78be3f3fd3ab5d3796ea026fb2986407a04440d880f3e48da77e"),
    "allowImage": ("macos-io-kotoba-allow.macho", "893198862e039cf2fcf10c7e1397c75b095eaf33b3562b35f5f9cafa18cb078f"),
    "denyImage": ("macos-io-kotoba-deny.macho", "cbca5a9009a19551be0d3548436dc93418a64525bda1d3d455325018bd08eda9"),
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pin(path, expected):
    observed = sha256(path)
    if observed != expected:
        raise ValueError(f"unexpected digest for {path}: {observed}")


def run(argv):
    return subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=10, check=False)


def observe(artifacts, output):
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise RuntimeError("execution requires macOS arm64")
    for path, expected in PINS.values():
        pin(path, expected)
    paths = {}
    for key, (name, expected) in ARTIFACT_PINS.items():
        paths[key] = artifacts / name
        pin(paths[key], expected)
    invalid = json.loads((artifacts / "macos-io-payload-invalid-admission.json").read_text())
    if (invalid.get("schema") != "amu.native-build-admission.v1"
            or invalid.get("exit") != 2
            or (artifacts / "macos-io-runtime-invalid.raw").exists()):
        raise ValueError("undeclared payload mode was not refused")

    guest = paths["guestRaw"].read_bytes()
    allow = paths["allowPayload"].read_bytes()
    deny = paths["denyPayload"].read_bytes()
    if (len(guest) != 135 or len(allow) != len(deny) or len(allow) != 448
            or allow[80:80 + len(guest)] != guest
            or struct.unpack_from("<I", allow, 20)[0] != 0xd2c00408
            or struct.unpack_from("<I", deny, 20)[0] != 0xd2800008
            or allow[:20] != deny[:20] or allow[24:] != deny[24:]):
        raise ValueError("Kotoba payload does not bind the Amu guest and grant edge")

    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for mode, payload, expected_exit, expected_stdout in (
            ("allow", allow, 42, b"native\n"),
            ("deny", deny, -5, b"")):
        image = paths[f"{mode}Image"].read_bytes()
        offset = 32
        commands = []
        for _ in range(6):
            command, size = struct.unpack_from("<II", image, offset)
            commands.append((command, size))
            offset += size
        if (len(image) != 16384 or image[:4] != b"\xcf\xfa\xed\xfe"
                or struct.unpack_from("<3I", image, 16) != (6, 296, 0x00200005)
                or commands != [(25, 72), (25, 72), (25, 72),
                                (14, 32), (0x80000028, 24), (50, 24)]
                or offset != 328 or image[1056:1504] != payload
                or image[1504:] != bytes(16384 - 1504)):
            raise ValueError(f"unexpected Kotoba Mach-O structure: {mode}")
        signed = output / f"macos-io-kotoba-{mode}-signed.macho"
        shutil.copyfile(paths[f"{mode}Image"], signed)
        signed.chmod(0o755)
        if (run(["/usr/bin/codesign", "--force", "--sign", "-", str(signed)]).returncode
                or run(["/usr/bin/codesign", "--verify", "--strict", str(signed)]).returncode):
            raise RuntimeError(f"macOS code signing failed: {mode}")
        launched = run([str(signed)])
        if (launched.returncode != expected_exit or launched.stdout != expected_stdout
                or launched.stderr):
            raise RuntimeError(f"Mac runtime result mismatch: {mode}")
        rows.append({"mode": mode, "unsignedSha256": sha256(paths[f"{mode}Image"]),
                     "signedSha256": sha256(signed), "exit": launched.returncode,
                     "stdoutHex": launched.stdout.hex(), "stderrBytes": len(launched.stderr)})

    allowed = paths["allowImage"].read_bytes()
    denied = paths["denyImage"].read_bytes()
    if allowed[:1076] != denied[:1076] or allowed[1080:] != denied[1080:]:
        raise ValueError("grant-only images differ outside the allow instruction")
    receipt = {"schema": "amu.macos-io-runtime-kotoba-smoke.v1",
               "status": "PASS_HOST_OBSERVATION", "compilerQualification": False,
               "trustedUserConsent": False, "payloadBytes": 448,
               "guestRawBytes": 135, "imageGrantWordOffset": 1076,
               "undeclaredModeExit": 2,
               "host": [platform.system(), platform.machine(), platform.mac_ver()[0]],
               "sourceSha256": {key: digest for key, (_, digest) in PINS.items()},
               "artifactSha256": {key: digest for key, (_, digest) in ARTIFACT_PINS.items()},
               "cases": rows}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: check-macos-io-runtime-payload.py ARTIFACT_DIR OUTPUT_DIR")
    print(json.dumps(observe(Path(sys.argv[1]), Path(sys.argv[2]))))
