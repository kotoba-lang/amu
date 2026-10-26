#!/usr/bin/env python3
"""Qualify native Mac AIUEOS font+user-slot EFI packaging and refusals.

Python stages pinned inputs and observes. The selfhost Amu image packages
both payloads and the legacy control without Linux, JVM, Node or C compiler.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if not __debug__:
    raise RuntimeError("native packaging assertions must be enabled")


def pin(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def gate_helpers():
    spec = importlib.util.spec_from_file_location(
        "mac_user_gate", HERE / "check-aiueos-user-macos-native.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(args):
    files = (args.compiler, args.compiler_receipt, args.kernel, args.font,
             args.slot, args.legacy_efi)
    if any(path.is_symlink() or not path.is_file() for path in files):
        raise ValueError("all inputs must be regular non-symlink files")
    if args.output.exists():
        raise ValueError("output must be a new private directory")
    helpers = gate_helpers()
    helpers.verify_macho(args.compiler)
    if pin(args.compiler)["sha256"] != args.compiler_sha256:
        raise ValueError("compiler digest mismatch")
    receipt = json.loads(args.compiler_receipt.read_text())
    if (receipt.get("status") != "PASS_MAC_NATIVE_USER_TARGET_SELFHOST"
            or not receipt.get("generations")
            or receipt["generations"][-1].get("signed") != pin(args.compiler)
            or receipt.get("fixedPointGeneration", 0) < 2):
        raise ValueError("compiler lacks a matching Mac selfhost fixed-point receipt")
    sources = {row["name"]: row for row in receipt["sources"]}
    for name in ("seed/78-full-entry.kotoba", "seed/84-aiueos-boot.kotoba",
                 "seed/86-aiueos-kernel-runtime.kotoba",
                 "seed/97-aiueos-desktop-regions.kotoba"):
        if pin(ROOT / name) != {key: sources[name][key] for key in ("bytes", "sha256")}:
            raise ValueError("fixed-point compiler source drift: " + name)
    if pin(args.font)["bytes"] != 524288 or pin(args.slot)["bytes"] != 524288:
        raise ValueError("font and user slot must each be 512 KiB")
    args.output.mkdir(mode=0o700)
    for source, name in ((args.kernel, "KERNEL.ELF"), (args.font, "font.bin"),
                         (args.slot, "user-slot.bin")):
        shutil.copyfile(source, args.output / name)
    compiler = args.compiler.resolve(strict=True)
    def run(name, *options, expected=0):
        return helpers.native_run(compiler, args.output, "package-aiueos-boot",
                                  "KERNEL.ELF", "--output", name, *options,
                                  expected=expected)
    dual = ("--font", "font.bin", "--user-slot", "user-slot.bin",
            "--pci-resources", "v1")
    run("dual.efi", *dual)
    run("dual.reproduced.efi", *dual)
    actual = (args.output / "dual.efi").read_bytes()
    if actual != (args.output / "dual.reproduced.efi").read_bytes():
        raise ValueError("native dual EFI reproduction mismatch")
    kernel, font, slot = (path.read_bytes() for path in
                          (args.kernel, args.font, args.slot))
    if (actual.count(kernel) != 1 or actual.count(font) != 1
            or actual.count(slot) != 1 or actual.index(slot) != actual.index(font) + 524288):
        raise ValueError("dual payload bytes or order mismatch")
    run("legacy.efi", "--payload", "font.bin", "--pci-resources", "v1")
    if (args.output / "legacy.efi").read_bytes() != args.legacy_efi.read_bytes():
        raise ValueError("legacy single-font EFI bytes changed")
    refusals = {}
    for kind, original, offset in (("font-magic", font, 0),
                                   ("slot-magic", slot, 0),
                                   ("slot-version", slot, 8)):
        changed = bytearray(original)
        changed[offset] ^= 1
        changed_name = kind + ".bin"
        (args.output / changed_name).write_bytes(changed)
        font_name = changed_name if kind == "font-magic" else "font.bin"
        slot_name = changed_name if kind != "font-magic" else "user-slot.bin"
        output_name = kind + ".efi"
        result = run(output_name, "--font", font_name,
                     "--user-slot", slot_name, "--pci-resources", "v1", expected=1)
        if b"E7111" not in result.stderr or (args.output / output_name).exists():
            raise ValueError(kind + " did not refuse before output")
        refusals[kind] = {"changedByte": offset, "outputAbsent": True, "code": "E7111"}
    result = run("missing.efi", "--font", "font.bin", "--user-slot",
                 "missing.bin", "--pci-resources", "v1", expected=1)
    if b"E3" not in result.stderr or (args.output / "missing.efi").exists():
        raise ValueError("missing user slot did not refuse")
    refusals["missing-slot"] = {"outputAbsent": True, "code": "E3"}
    result = run("dual.efi", *dual, expected=2)
    if b"E7110" not in result.stderr:
        raise ValueError("existing output was not refused")
    refusals["existing-output"] = {"code": "E7110"}
    if any(pin(source) != pin(args.output / name) for source, name in
           ((args.kernel, "KERNEL.ELF"), (args.font, "font.bin"),
            (args.slot, "user-slot.bin"))):
        raise ValueError("native input changed during packaging")
    report = {"schema": "amu.macos-aiueos-dual-payload.v1",
              "status": "PASS_MAC_NATIVE_AIUEOS_DUAL_PAYLOAD_AND_REFUSALS",
              "compiler": pin(args.compiler), "compilerReceipt": pin(args.compiler_receipt),
              "kernel": pin(args.kernel), "font": pin(args.font), "userSlot": pin(args.slot),
              "dualEfi": pin(args.output / "dual.efi"),
              "dualReproducedEfi": pin(args.output / "dual.reproduced.efi"),
              "legacyEfi": pin(args.output / "legacy.efi"),
              "legacyReference": pin(args.legacy_efi), "refusals": refusals,
              "sources": {name: pin(ROOT / name) for name in
                          ("seed/78-full-entry.kotoba", "seed/84-aiueos-boot.kotoba",
                           "seed/86-aiueos-kernel-runtime.kotoba",
                           "seed/97-aiueos-desktop-regions.kotoba")},
              "observer": pin(Path(__file__)), "macNativePackaging": True,
              "linuxJVMNodeOrCCompilerInThisGate": False,
              "guestBootQualified": False, "releaseQualified": False}
    (args.output / "dual-payload-macos-native.json").write_text(
        json.dumps(report, indent=2) + "\n")
    print(report["status"], report["dualEfi"]["sha256"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--compiler-sha256", required=True)
    parser.add_argument("--compiler-receipt", type=Path, required=True)
    parser.add_argument("--kernel", type=Path, required=True)
    parser.add_argument("--font", type=Path, required=True)
    parser.add_argument("--slot", type=Path, required=True)
    parser.add_argument("--legacy-efi", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args())
