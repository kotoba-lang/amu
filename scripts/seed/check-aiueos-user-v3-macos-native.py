#!/usr/bin/env python3
"""Check the bounded Amu user-v3 syscall ELF with a pinned Mac selfhost image.

This checks compiler isolation and ELF bytes. Guest behavior has a separate
AIUEOS QEMU gate; this script does not claim an Itonami turn.
"""

import argparse
import importlib.util
import json
from pathlib import Path
import struct


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1] / "seed/tests/aiueos-user-v3-local-model.kotoba"
TRAMPOLINE = bytes.fromhex("b8050000004883ec080f054883c408c3")
ELF_SHA256 = "331a3ed64c5859bc546a36ce9666e1a1e17e31195caca96407def6f63f5cc7b1"


def load_mac():
    spec = importlib.util.spec_from_file_location(
        "mac_user_gate", HERE / "check-aiueos-user-macos-native.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify(data):
    if len(data) != 8280 or data[:4] != b"\x7fELF":
        raise ValueError("wrong user-v3 ELF size or header")
    if struct.unpack_from("<Q", data, 24)[0] != 0x220000:
        raise ValueError("wrong user-v3 entry")
    if struct.unpack_from("<Q", data, 64 + 32)[0] != 462:
        raise ValueError("wrong user-v3 executable extent")
    if struct.unpack_from("<Q", data, 120 + 40)[0] != 320:
        raise ValueError("wrong user-v3 writable extent")
    if data[4096 + 48:4096 + 64] != TRAMPOLINE:
        raise ValueError("syscall trampoline did not align the stack")
    if (struct.unpack_from("<Q", data, 8192 + 8)[0] != 256
            or struct.unpack_from("<Q", data, 8192 + 48)[0] != 0x220030
            or any(data[8192:8192 + 8])
            or any(data[8192 + 16:8192 + 48])
            or any(data[8192 + 56:8280])):
        raise ValueError("user-v3 ELF has unexpected initial context")


def main(args):
    mac = load_mac()
    compiler = args.compiler_image.resolve(strict=True)
    compiler_pin = mac.require_regular(compiler, args.compiler_sha256)
    mac.verify_macho(compiler)
    source_pin = mac.require_regular(SOURCE)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    source = output / "user.kotoba"
    source.write_bytes(SOURCE.read_bytes())
    results = []
    for name in ("user.elf", "user.reproduced.elf"):
        mac.native_run(compiler, output, "compile", source.name,
                       "--target", "x86_64-aiueos-user-v3", "--output", name)
        result = output / name
        verify(result.read_bytes())
        identity = mac.pin(result)
        if identity["sha256"] != ELF_SHA256:
            raise ValueError("user-v3 ELF changed from the pinned guest image")
        results.append(identity)
    if results[0] != results[1]:
        raise ValueError("user-v3 native build was not reproducible")
    refused = mac.native_run(compiler, output, "compile", source.name,
                             "--target", "x86_64-aiueos-user-v2",
                             "--output", "forbidden-v2.elf", expected=1)
    if (output / "forbidden-v2.elf").exists() or not refused.stderr:
        raise ValueError("v2 target accepted the v3-only operation")
    if mac.pin(source) != source_pin or mac.pin(compiler) != compiler_pin:
        raise ValueError("qualification inputs changed")
    report = {"schema": "amu.mac-aiueos-user-v3-local-call.v1",
              "status": "PASS_MAC_NATIVE_USER_V3_LOCAL_CALL_ELF",
              "compiler": compiler_pin, "source": source_pin,
              "elf": results[0], "reproducedElf": results[1],
              "v2Refusal": True, "observer": mac.pin(Path(__file__)),
              "guestExecution": False, "externalOperation": False,
              "agentLoop": False, "linuxProcessInThisGate": False}
    (output / "mac-aiueos-user-v3-local-call.json").write_text(
        json.dumps(report, indent=2) + "\n")
    print(report["status"], ELF_SHA256, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler-image", type=Path, required=True)
    parser.add_argument("--compiler-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args())
