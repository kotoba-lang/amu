#!/usr/bin/env python3
"""Exercise scoped Mac FS2 F/E through an Amu-built Kotoba native program.

Python stages fixed inputs and records process results. The implementation
under test is the signed Mach-O image emitted by the Kotoba packager.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import struct
import subprocess


ROOT = Path(__file__).resolve().parents[2]
PARTS = [ROOT / ("seed/" + name) for name in
         ("00-ns-static.kotoba", "01-mem.kotoba", "02-io.kotoba")]
PARTS.append(ROOT / "scripts/seed/fixtures/mac-fs2-ef-probe.kotoba")


def pin(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def verify_image(path, expected):
    if pin(path)["sha256"] != expected:
        raise ValueError("Mac image pin changed")
    raw = path.read_bytes()
    if len(raw) < 32 or struct.unpack_from("<IiiI", raw) != (0xfeedfacf, 0x100000c, 0, 2):
        raise ValueError("expected arm64 Mach-O executable")
    subprocess.run(["/usr/bin/codesign", "--verify", "--strict", str(path)],
                   check=True, capture_output=True)
    linked = subprocess.run(["/usr/bin/otool", "-L", str(path)],
                            check=True, capture_output=True).stdout.splitlines()
    if linked != [f"{path}:".encode()]:
        raise ValueError("unexpected dylib dependency")


def main(args):
    if platform.system() != "Darwin" or platform.machine() not in ("arm64", "aarch64"):
        raise ValueError("Mac FS2 gate requires Apple Silicon")
    compiler = args.compiler.resolve(strict=True)
    packager = args.packager.resolve(strict=True)
    efi = args.efi.resolve(strict=True)
    if any(path.is_symlink() for path in (args.compiler, args.packager, args.efi)):
        raise ValueError("input symlink refused")
    verify_image(compiler, args.compiler_sha256)
    verify_image(packager, args.packager_sha256)
    original = pin(efi)
    if original["sha256"] != args.efi_sha256 or original["bytes"] < 4:
        raise ValueError("EFI pin mismatch")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    for source in PARTS:
        if source.is_symlink() or not source.is_file():
            raise ValueError("fixture source missing or symlink")
    source_pins = [pin(source) for source in PARTS]
    (output / "probe.kotoba").write_bytes(
        b"".join(source.read_bytes() + b"\n" for source in PARTS))
    shutil.copyfile(efi, output / "BOOTX64.EFI")
    scope = os.open(output, os.O_RDONLY | os.O_DIRECTORY)
    saved = None
    if scope != 3:
        try:
            saved = os.dup(3)
        except OSError:
            pass
        os.dup2(scope, 3)
    passed = (3,) if saved is None else (3, saved)
    calls = []

    def run(name, command, expected):
        result = subprocess.run([str(part) for part in command], cwd=output,
                                pass_fds=passed, capture_output=True, timeout=180,
                                env={"PATH": "/nonexistent"})
        (output / (name + ".stdout")).write_bytes(result.stdout)
        (output / (name + ".stderr")).write_bytes(result.stderr)
        calls.append({"name": name, "exit": result.returncode,
                      "stdout": pin(output / (name + ".stdout")),
                      "stderr": pin(output / (name + ".stderr"))})
        if result.returncode != expected or (expected == 0 and result.stderr):
            raise ValueError(f"{name}: native exit {result.returncode}: "
                             + result.stderr.decode(errors="replace")[-500:])
        return result.stdout

    try:
        run("compile", [compiler, "compile", "probe.kotoba", "--target",
                        "aarch64-macos", "--output", "probe.kseed"], 0)
        extracted = run("extract", [compiler, "extract-native", "probe.kseed",
                                    "--symbol", "main", "--output", "probe.raw"], 0)
        match = re.search(rb":offset (\d+), :length (\d+), :arity 0\}", extracted)
        if not match or int(match.group(2)) != pin(output / "probe.raw")["bytes"]:
            raise ValueError("native main extraction mismatch")
        run("package", [packager, "probe-unsigned.macho", "probe.raw",
                        "fs2-cli-stdio-general", match.group(1).decode("ascii")], 0)
        program = output / "probe.macho"
        shutil.copyfile(output / "probe-unsigned.macho", program)
        program.chmod(0o755)
        subprocess.run(["/usr/bin/codesign", "--force", "--sign", "-", str(program)],
                       check=True, capture_output=True)
        verify_image(program, pin(program)["sha256"])
        if b"PASS_MAC_FS2_EF" not in run("valid-metadata-and-range",
                                        [program, "BOOTX64.EFI", "0:4"], 0):
            raise ValueError("positive fixture omitted marker")
        run("missing-F-returns-empty", [program, "missing.efi", "F"], 0)
        (output / "link.efi").symlink_to("BOOTX64.EFI")
        run("symlink-F-returns-empty", [program, "link.efi", "F"], 0)
        size = original["bytes"]
        for name, path, tail in (
            ("past-end-E", "BOOTX64.EFI", str(size) + ":1"),
            ("overflow-E", "BOOTX64.EFI", "4294967296:1"),
            ("oversize-E", "BOOTX64.EFI", "0:262145"),
            ("traversal-E", "../" + output.name + "/BOOTX64.EFI", "0:4"),
            ("missing-E", "missing.efi", "0:4"),
            ("symlink-E", "link.efi", "0:4"),
        ):
            run(name, [program, path, tail], -5)
        if (pin(efi) != original or pin(output / "BOOTX64.EFI") != original
                or pin(compiler)["sha256"] != args.compiler_sha256
                or pin(packager)["sha256"] != args.packager_sha256
                or any(pin(source) != expected for source, expected in zip(PARTS, source_pins))):
            raise ValueError("fixture input changed")
        receipt = {
            "schema": "amu.macos-fs2-ef.v1", "status": "PASS_MAC_FS2_EF",
            "compiler": pin(compiler), "packager": pin(packager),
            "sourceUnity": pin(output / "probe.kotoba"), "sourceParts": source_pins,
            "efi": original, "program": pin(program), "calls": calls,
            "negativeControls": 8, "fd3Scoped": True,
            "linuxJVMNodeOrCCompiler": False,
        }
        (output / "fs2-ef.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(receipt["status"])
    finally:
        if saved is not None:
            os.dup2(saved, 3)
            os.close(saved)
        elif scope != 3:
            os.close(3)
        os.close(scope)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--compiler-sha256", required=True)
    parser.add_argument("--packager", type=Path, required=True)
    parser.add_argument("--packager-sha256", required=True)
    parser.add_argument("--efi", type=Path, required=True)
    parser.add_argument("--efi-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args())
