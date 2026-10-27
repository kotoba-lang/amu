#!/usr/bin/env python3
"""Check the proposed user-v5 ELF and slot-v4 layout with signed Mac Amu.

This checks artifact shape and old target isolation. The guest still rejects
slot-v4, and this is not a typed kit call or AIUEOS release qualification.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct


HERE = Path(__file__).resolve().parent
V5_SOURCE = ("(ns aiueos-user-v5-layout (:export [main]))\n"
             "(defn main [request :i64 request-bytes :i64] :i64 "
             "(kernel-load-u32 request request-bytes 0))\n")
DECLARED_LLM = ("(ns aiueos-user-v5-llm (:export [main]) "
                "(:capabilities #{:llm/generate}))\n"
                "(defn main [request :i64 request-bytes :i64] :i64 "
                "(llm/generate request))\n")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reject(native, compiler, output, source, name, diagnostic, *options):
    result = native.native_run(compiler, output, "package-aiueos-user-payload",
                               source, "--output", name, *options, expected=1)
    if diagnostic not in result.stderr or (output / name).exists():
        raise ValueError("slot admission failed open: " + name)


def main(args):
    native = load("mac_user_gate", HERE / "check-aiueos-user-macos-native.py")
    v2 = load("user_v2", HERE / "check-aiueos-user-v2-native.py")
    v3 = load("user_v3", HERE / "check-aiueos-user-v3-macos-native.py")
    compiler = args.compiler_image.resolve(strict=True)
    original = native.require_regular(compiler, args.compiler_sha256)
    native.verify_macho(compiler)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)

    (output / "user-v5.kotoba").write_text(V5_SOURCE)
    native.native_run(compiler, output, "compile", "user-v5.kotoba", "--target",
                      "x86_64-aiueos-user-v5", "--output", "user-v5.elf")
    elf = (output / "user-v5.elf").read_bytes()
    if (len(elf) != 8280 or struct.unpack_from("<Q", elf, 24)[0] != 0x420000
            or elf[:4] != b"\x7fELF"):
        raise ValueError("user-v5 ELF identity changed")
    rx, rw = (struct.unpack_from("<IIQQQQQQ", elf, 64 + 56 * i)
              for i in range(2))
    if (rx[:5] != (1, 5, 4096, 0x420000, 0x420000)
            or not 80 < rx[5] == rx[6] <= 4096 or rx[7] != 4096
            or rw != (1, 6, 8192, 0x421000, 0x421000, 88, 262144, 4096)
            or struct.unpack_from("<Q", elf, 8192 + 48)[0] != 0x420030
            or any(elf[176:4096]) or any(elf[4096 + rx[5]:8192])):
        raise ValueError("user-v5 ELF layout changed")
    native.native_run(compiler, output, "package-aiueos-user-payload",
                      "user-v5.elf", "--output", "user-v5.slot", "--version", "v4")
    slot = (output / "user-v5.slot").read_bytes()
    if (len(slot) != 524288
            or struct.unpack_from("<QQQ", slot) != (0x0031444c50554941, 4, len(elf))
            or slot[64:64 + len(elf)] != elf or any(slot[64 + len(elf):])):
        raise ValueError("slot-v4 content or zero padding changed")

    negative = []
    for name, offset, value in (("entry", 24, 0x220000),
                                ("rw-address", 136, 0x321000),
                                ("rw-extent", 160, 320)):
        candidate = bytearray(elf)
        struct.pack_into("<Q", candidate, offset, value)
        source = name + ".elf"
        (output / source).write_bytes(candidate)
        reject(native, compiler, output, source, name + ".slot", b"E7111",
               "--version", "v4")
        negative.append(name)
    for version in ("v2", "v3"):
        reject(native, compiler, output, "user-v5.elf", "wrong-" + version + ".slot",
               b"E7111", "--version", version)
        negative.append("v5-as-" + version)
    (output / "declared-llm.kotoba").write_text(DECLARED_LLM)
    refused = native.native_run(compiler, output, "compile", "declared-llm.kotoba",
                                "--target", "x86_64-aiueos-user-v5", "--output",
                                "declared-llm.elf", expected=1)
    if b"E2004" not in refused.stderr or (output / "declared-llm.elf").exists():
        raise ValueError("v5 accepted an unimplemented typed LLM kit")
    negative.append("typed-llm-kit")

    legacy = []
    for name, target, source, version in (
            ("v2", "x86_64-aiueos-user-v2", v2.SOURCE, "v2"),
            ("v3", "x86_64-aiueos-user-v3",
             (HERE.parents[1] / "seed/tests/aiueos-user-v3-local-model.kotoba").read_text(), "v2"),
            ("v4", "x86_64-aiueos-user-v4",
             (HERE.parents[1] / "seed/tests/aiueos-user-v3-local-model.kotoba").read_text(), "v3")):
        (output / (name + ".kotoba")).write_text(source)
        native.native_run(compiler, output, "compile", name + ".kotoba", "--target",
                          target, "--output", name + ".elf")
        artifact = (output / (name + ".elf")).read_bytes()
        if name == "v2":
            v2.verify(artifact)
        elif name == "v3":
            v3.verify(artifact)
            if hashlib.sha256(artifact).hexdigest() != v3.ELF_SHA256:
                raise ValueError("pinned v3 ELF changed")
        elif (struct.unpack_from("<Q", artifact, 24)[0] != 0x320000
              or struct.unpack_from("<Q", artifact, 136)[0] != 0x321000
              or struct.unpack_from("<Q", artifact, 160)[0] != 320):
            raise ValueError("legacy v4 ELF layout changed")
        native.native_run(compiler, output, "package-aiueos-user-payload",
                          name + ".elf", "--output", name + ".slot",
                          "--version", version)
        legacy.append({"target": target, "elf": native.pin(output / (name + ".elf")),
                       "slot": native.pin(output / (name + ".slot"))})

    if native.pin(compiler) != original:
        raise ValueError("compiler changed during observation")
    report = {"schema": "amu.mac-aiueos-user-v5-layout-candidate.v1",
              "status": "PASS_MAC_NATIVE_V5_LAYOUT_CANDIDATE",
              "compiler": original, "source": native.pin(output / "user-v5.kotoba"),
              "elf": native.pin(output / "user-v5.elf"),
              "slot": native.pin(output / "user-v5.slot"),
              "legacy": legacy, "negativeControls": negative,
              "observer": native.pin(Path(__file__)), "guestAdmission": False,
              "typedKitCall": False, "agentLoop": False, "releaseQualified": False,
              "linuxProcessInThisGate": False}
    (output / "mac-aiueos-user-v5-layout.json").write_text(
        json.dumps(report, indent=2) + "\n")
    print(report["status"], report["elf"]["sha256"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler-image", type=Path, required=True)
    parser.add_argument("--compiler-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args())
