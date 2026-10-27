#!/usr/bin/env python3
"""Check the proposed user-v5 ELF and slot-v4 layout with signed Mac Amu.

This checks artifact shape, the bounded diagnostic syscall lowering and old
target isolation. It does not execute the guest or qualify a typed kit call.
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
CALL_ELF_SHA256 = "e19f3be978e23b66c7551905f1d829258622e8358e1b28528bc48adb6869e852"


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
    if args.mac_build:
        if args.compiler_sha256:
            raise ValueError("choose Mac build or explicit compiler pin")
        build = args.mac_build.resolve(strict=True)
        if build.is_symlink() or not build.is_dir():
            raise ValueError("regular Mac build directory required")
        descriptor_path = HERE.parents[1] / "seed/bootstrap/aarch64-macos/root.json"
        descriptor = json.loads(descriptor_path.read_text())
        report = json.loads((build / "mac-aiueos-user-target.json").read_text())
        generations = report.get("generations", [])
        if (report.get("status") != "PASS_MAC_NATIVE_USER_TARGET_SELFHOST"
                or report.get("source") != descriptor["fullSource"]
                or report.get("bootstrapDescriptor") != native.pin(descriptor_path)
                or len(generations) < 2
                or any(generations[-1][key] != generations[-2][key]
                       for key in ("container", "raw", "unsigned"))
                or generations[-1]["container"]["sha256"] !=
                descriptor["expectedFixedPoint"]["compilerContainerSha256"]):
            raise ValueError("Mac build is not the current source fixed point")
        compiler = build / f"F{generations[-1]['number']}-signed.macho"
        original = native.require_regular(compiler, generations[-1]["signed"]["sha256"])
        if original != generations[-1]["signed"]:
            raise ValueError("Mac compiler image size changed")
    else:
        if not args.compiler_sha256:
            raise ValueError("explicit compiler requires a SHA-256 pin")
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
    call_source = HERE.parents[1] / "seed/tests/aiueos-user-v3-local-model.kotoba"
    (output / "user-v5-call.kotoba").write_bytes(call_source.read_bytes())
    native.native_run(compiler, output, "compile", "user-v5-call.kotoba", "--target",
                      "x86_64-aiueos-user-v5", "--output", "user-v5-call.elf")
    call_elf = (output / "user-v5-call.elf").read_bytes()
    if (hashlib.sha256(call_elf).hexdigest() != CALL_ELF_SHA256
            or struct.unpack_from("<Q", call_elf, 96)[0] != 478
            or call_elf.count(bytes.fromhex("48b80011420000000000")) != 1
            or call_elf.count(bytes.fromhex("b830004200ffd0")) != 1):
        raise ValueError("user-v5 diagnostic syscall lowering changed")
    native.native_run(compiler, output, "package-aiueos-user-payload",
                      "user-v5-call.elf", "--output", "user-v5-call.slot", "--version", "v4")

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
              "diagnosticCallElf": native.pin(output / "user-v5-call.elf"),
              "diagnosticCallSlot": native.pin(output / "user-v5-call.slot"),
              "legacy": legacy, "negativeControls": negative,
              "observer": native.pin(Path(__file__)), "guestAdmission": False,
              "typedKitCall": False, "agentLoop": False, "releaseQualified": False,
              "linuxProcessInThisGate": False}
    (output / "mac-aiueos-user-v5-layout.json").write_text(
        json.dumps(report, indent=2) + "\n")
    print(report["status"], report["elf"]["sha256"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--compiler-image", type=Path)
    source.add_argument("--mac-build", type=Path)
    parser.add_argument("--compiler-sha256")
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args())
