#!/usr/bin/env python3
"""Build the user-target Amu source with Mac native Amu and emit its ELF.

Python stages pinned source bytes and observes native processes. The signed
compiler and packager are explicit inputs; no Linux, JVM, Node or C compiler
process is part of this Mac gate. This is compiler/artifact evidence, not a
guest, Itonami turn or release qualification.
"""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import struct
import subprocess


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "seed/FULL-MANIFEST"
USER_CHECK = ROOT / "scripts/seed/check-aiueos-user-elf-native.py"
FS2_PRODUCT = ROOT / "seed/tests/fs2-product.kotoba"
ROOT_DESCRIPTOR = ROOT / "seed/bootstrap/aarch64-macos/root.json"
PACKAGER_SOURCE = ROOT / "seed/macos-fs2-runtime-packager.kotoba"


def pin(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def require_regular(path, digest=None):
    if path.is_symlink() or not path.is_file():
        raise ValueError("regular non-symlink input required: " + str(path))
    identity = pin(path)
    if digest is not None and identity["sha256"] != digest:
        raise ValueError("input digest mismatch: " + path.name)
    return identity


def process(argv, *, cwd=None, env=None, pass_fds=(), timeout=1200):
    return subprocess.run([str(arg) for arg in argv], cwd=cwd, env=env,
                          pass_fds=pass_fds, capture_output=True,
                          timeout=timeout, check=False)


def verify_macho(path):
    raw = path.read_bytes()
    if len(raw) < 32 or struct.unpack_from("<IiiI", raw) != (0xfeedfacf, 0x100000c, 0, 2):
        raise ValueError("expected arm64 Mach-O executable: " + path.name)
    commands, size = struct.unpack_from("<II", raw, 16)
    if commands < 2 or commands > 32 or size > 992 or 32 + size > len(raw):
        raise ValueError("invalid Mac load-command extent: " + path.name)
    seen = {2: 0, 11: 0}
    offset = 32
    for _ in range(commands):
        if offset + 8 > 32 + size:
            raise ValueError("truncated Mac load command: " + path.name)
        kind, length = struct.unpack_from("<II", raw, offset)
        if length < 8 or length % 8 or offset + length > 32 + size:
            raise ValueError("invalid Mac load command: " + path.name)
        if kind in seen:
            expected_length = {2: 24, 11: 80}[kind]
            if length != expected_length or any(raw[offset+8:offset+length]):
                raise ValueError("nonempty Mac symbol/relocation table: " + path.name)
            seen[kind] += 1
        offset += length
    if offset != 32 + size or seen != {2: 1, 11: 1}:
        raise ValueError("Mac symbol/relocation commands missing: " + path.name)
    signed = process(["/usr/bin/codesign", "--verify", "--strict", path], timeout=30)
    if signed.returncode:
        raise ValueError("code signature verification failed: " + path.name)
    linked = process(["/usr/bin/otool", "-L", path], timeout=30)
    if linked.returncode or linked.stdout.splitlines() != [f"{path}:".encode()]:
        raise ValueError("undeclared dylib dependency: " + path.name)
    return pin(path)


def native_run(image, directory, *args, expected=0, timeout=1200):
    """Give the native program only the output-owned FD3 file root."""
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    saved = None
    relocated = fd != 3
    try:
        if relocated:
            try:
                saved = os.dup(3)
            except OSError:
                pass
            os.dup2(fd, 3)
        env = {"PATH": "/usr/bin:/bin", "LANG": "C", "TMPDIR": str(directory),
               "TMP": str(directory), "TEMP": str(directory)}
        result = process([image, *args], cwd=directory, env=env,
                         pass_fds=(3,), timeout=timeout)
    finally:
        if relocated:
            if saved is None:
                os.close(3)
            else:
                os.dup2(saved, 3)
                os.close(saved)
        os.close(fd)
    if result.returncode != expected:
        raise ValueError(f"{image.name} returned {result.returncode}, expected {expected}: "
                         + result.stderr.decode(errors="replace")[-800:])
    if expected == 0 and result.stderr:
        raise ValueError(f"{image.name} wrote unexpected stderr: "
                         + result.stderr.decode(errors="replace")[-800:])
    return result


def stage_unity(directory):
    names = [line for line in MANIFEST.read_text().splitlines()
             if line and not line.startswith("#")]
    if len(names) != 59 or len(set(names)) != 59:
        raise ValueError("FULL-MANIFEST must contain 59 unique modules")
    sources = []
    with (directory / "full-unity.kotoba").open("wb") as stream:
        for name in names:
            part = Path(name)
            if part.is_absolute() or ".." in part.parts or part.parts[0] != "seed":
                raise ValueError("invalid source path in FULL-MANIFEST")
            path = ROOT / part
            sources.append({"name": name, **require_regular(path)})
            stream.write(path.read_bytes() + b"\n")
    return sources, pin(directory / "full-unity.kotoba")


def sign(unsigned, signed):
    shutil.copyfile(unsigned, signed)
    signed.chmod(0o755)
    result = process(["/usr/bin/codesign", "--force", "--sign", "-", signed], timeout=30)
    if result.returncode:
        raise ValueError("could not sign native Mach-O: " + signed.name)
    return verify_macho(signed)


def bootstrap_inputs(args):
    fields = (args.compiler_image, args.compiler_sha256,
              args.packager_image, args.packager_sha256)
    if any(value is not None for value in fields):
        if not all(value is not None for value in fields):
            raise ValueError("explicit bootstrap requires both image paths and SHA-256 pins")
        return (args.compiler_image.resolve(strict=True), args.compiler_sha256,
                args.packager_image.resolve(strict=True), args.packager_sha256,
                None, None)
    descriptor_pin = require_regular(ROOT_DESCRIPTOR)
    descriptor = json.loads(ROOT_DESCRIPTOR.read_text())
    if (descriptor.get("schema") != "amu.macos-arm64-selfhost-root.v1"
            or descriptor.get("status") != "diagnostic-candidate"
            or descriptor.get("fullManifest") != "seed/FULL-MANIFEST"):
        raise ValueError("unsupported Mac bootstrap descriptor")
    paths = {"compiler": "seed/bootstrap/aarch64-macos/amu-full-root.macho",
             "packager": "seed/bootstrap/aarch64-macos/kotoba-packager-root.macho"}
    for role, expected in paths.items():
        if descriptor[role]["path"] != expected:
            raise ValueError("Mac bootstrap role path changed: " + role)
        path = ROOT / expected
        if require_regular(path, descriptor[role]["sha256"]) != {
                key: descriptor[role][key] for key in ("bytes", "sha256")}:
            raise ValueError("Mac bootstrap role size changed: " + role)
    if (descriptor["packagerSource"]["path"]
            != "seed/macos-fs2-runtime-packager.kotoba"
            or require_regular(PACKAGER_SOURCE, descriptor["packagerSource"]["sha256"])
            != {key: descriptor["packagerSource"][key]
                for key in ("bytes", "sha256")}):
        raise ValueError("Mac packager source changed")
    return (ROOT / paths["compiler"], descriptor["compiler"]["sha256"],
            ROOT / paths["packager"], descriptor["packager"]["sha256"],
            descriptor, descriptor_pin)


def rebuild_packager(producer, packager, directory, compiler_row):
    shutil.copyfile(PACKAGER_SOURCE, directory / "packager.kotoba")
    native_run(producer, directory, "compile", "packager.kotoba",
               "--target", "aarch64-macos", "--output", "P1.kseed")
    extracted = native_run(producer, directory, "extract-native", "P1.kseed",
                           "--symbol", "main", "--output", "P1.raw")
    match = re.search(rb":offset (\d+), :length (\d+), :arity 0}", extracted.stdout)
    if match is None or int(match.group(2)) != (directory / "P1.raw").stat().st_size:
        raise ValueError("Mac packager main extraction did not match raw bytes")
    entry = int(match.group(1))
    native_run(packager, directory, "P1-unsigned.macho", "P1.raw",
               "fs2-cli-stdio-general", str(entry))
    sign(directory / "P1-unsigned.macho", directory / "P1-signed.macho")
    native_run(directory / "P1-signed.macho", directory, "P2-unsigned.macho",
               "P1.raw", "fs2-cli-stdio-general", str(entry))
    if pin(directory / "P1-unsigned.macho") != pin(directory / "P2-unsigned.macho"):
        raise ValueError("Mac packager did not repackage itself byte for byte")
    native_run(directory / "P1-signed.macho", directory, "F3-unsigned.macho",
               f"F{compiler_row['number']}.raw", "fs2-cli-stdio-general",
               str(compiler_row["entry"]))
    if pin(directory / "F3-unsigned.macho") != compiler_row["unsigned"]:
        raise ValueError("rebuilt Mac packager changed the full compiler image")
    return {"source": pin(PACKAGER_SOURCE), "container": pin(directory / "P1.kseed"),
            "raw": pin(directory / "P1.raw"), "entry": entry,
            "unsigned": pin(directory / "P1-unsigned.macho"),
            "repackagedUnsigned": pin(directory / "P2-unsigned.macho"),
            "repackagedCompilerUnsigned": pin(directory / "F3-unsigned.macho")}


def generation(number, producer, packager, directory):
    container = directory / f"F{number}.kseed"
    raw = directory / f"F{number}.raw"
    unsigned = directory / f"F{number}-unsigned.macho"
    signed = directory / f"F{number}-signed.macho"
    native_run(producer, directory, "compile", "full-unity.kotoba",
               "--target", "aarch64-macos", "--output", container.name)
    extracted = native_run(producer, directory, "extract-native", container.name,
                           "--symbol", "main", "--output", raw.name)
    match = re.search(rb":offset (\d+), :length (\d+), :arity 0}", extracted.stdout)
    if match is None or int(match.group(2)) != raw.stat().st_size:
        raise ValueError("native main extraction did not match raw bytes")
    entry = int(match.group(1))
    native_run(packager, directory, unsigned.name, raw.name,
               "fs2-cli-stdio-general", str(entry))
    signed_pin = sign(unsigned, signed)
    row = {"number": number, "producer": pin(producer),
           "container": pin(container), "raw": pin(raw), "entry": entry,
           "unsigned": pin(unsigned), "signed": signed_pin}
    print(f"F{number} container {row['container']['sha256']}", flush=True)
    return signed, row


def main(args):
    if platform.system() != "Darwin" or platform.machine() not in ("arm64", "aarch64"):
        raise ValueError("Mac native user-target gate requires Apple Silicon")
    (compiler, compiler_sha, packager, packager_sha,
     descriptor, descriptor_pin) = bootstrap_inputs(args)
    compiler_pin = require_regular(compiler, compiler_sha)
    packager_pin = require_regular(packager, packager_sha)
    manifest_pin = require_regular(MANIFEST)
    checker_pin = require_regular(USER_CHECK)
    fs2_product_pin = require_regular(FS2_PRODUCT)
    packager_source_pin = require_regular(PACKAGER_SOURCE)
    verify_macho(compiler)
    verify_macho(packager)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    sources, unity = stage_unity(output)
    if descriptor is not None and unity != descriptor["fullSource"]:
        raise ValueError("Mac bootstrap source graph changed")
    print(f"staged {len(sources)} modules {unity['sha256']}", flush=True)

    rows = []
    producer = compiler
    for number in (1, 2, 3):
        producer, row = generation(number, producer, packager, output)
        rows.append(row)
        if number > 1 and all(row[key] == rows[-2][key]
                              for key in ("container", "raw", "unsigned")):
            break
    else:
        raise ValueError("Mac full compiler did not reach a source fixed point")
    if (descriptor is not None and rows[-1]["container"]["sha256"]
            != descriptor["expectedFixedPoint"]["compilerContainerSha256"]):
        raise ValueError("Mac bootstrap compiler fixed-point digest changed")
    packager_rebuild = rebuild_packager(producer, packager, output, rows[-1])
    if (descriptor is not None and packager_rebuild["unsigned"]["sha256"]
            != descriptor["expectedFixedPoint"]["packagerUnsignedSha256"]):
        raise ValueError("Mac bootstrap packager fixed-point digest changed")

    spec = importlib.util.spec_from_file_location("user_check", USER_CHECK)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    scalar = output / "scalar.kotoba"
    scalar.write_text(checker.SOURCE)
    native_run(producer, output, "compile", scalar.name, "--target", checker.TARGET,
               "--output", "scalar.elf")
    image = output / "scalar.elf"
    checker.verify(image.read_bytes())
    native_run(producer, output, "package-aiueos-user-payload", image.name,
               "--output", "scalar-slot.bin")
    slot = output / "scalar-slot.bin"
    packed = slot.read_bytes()
    assert len(packed) == 524288
    assert struct.unpack_from("<QQQ", packed) == (0x0031444c50554941, 1,
                                                  image.stat().st_size)
    assert packed[64:64 + image.stat().st_size] == image.read_bytes()
    assert not any(packed[64 + image.stat().st_size:])
    existing = native_run(producer, output, "package-aiueos-user-payload",
                          image.name, "--output", slot.name, expected=2)
    if b"E7110" not in existing.stderr:
        raise ValueError("user payload packager did not refuse existing output")
    missing = native_run(producer, output, "package-aiueos-user-payload",
                         "missing.elf", "--output", "missing-slot.bin", expected=1)
    if b"E3" not in missing.stderr or (output / "missing-slot.bin").exists():
        raise ValueError("user payload packager did not refuse missing input")
    (output / "oversized.bin").write_bytes(bytes(524225))
    oversized = native_run(producer, output, "package-aiueos-user-payload",
                           "oversized.bin", "--output", "oversized-slot.bin",
                           expected=1)
    if b"E7112" not in oversized.stderr or (output / "oversized-slot.bin").exists():
        raise ValueError("user payload packager did not refuse oversized input")
    effect = output / "effect.kotoba"
    effect.write_text(checker.EFFECT)
    refused = native_run(producer, output, "compile", effect.name,
                         "--target", checker.TARGET, "--output", "effect.elf",
                         expected=1)
    if b"E7101" not in refused.stderr or (output / "effect.elf").exists():
        raise ValueError("undeclared effect was not refused without an artifact")

    # The Mac wrapper must dispatch real bytes-concat/slice calls, not merely
    # rebuild a compiler whose own source happens not to exercise those slots.
    fs2_source = output / "fs2-product.kotoba"
    shutil.copyfile(FS2_PRODUCT, fs2_source)
    native_run(producer, output, "compile", fs2_source.name,
               "--target", "aarch64-macos", "--output", "fs2-product.kseed")
    extracted = native_run(producer, output, "extract-native", "fs2-product.kseed",
                           "--symbol", "main", "--output", "fs2-product.raw")
    match = re.search(rb":offset (\d+), :length (\d+), :arity 0}", extracted.stdout)
    if match is None or int(match.group(2)) != (output / "fs2-product.raw").stat().st_size:
        raise ValueError("Mac FS2 product main extraction did not match raw bytes")
    native_run(output / "P1-signed.macho", output, "fs2-product-unsigned.macho",
               "fs2-product.raw", "fs2-cli-stdio-general", match.group(1).decode())
    fs2_image_pin = sign(output / "fs2-product-unsigned.macho",
                         output / "fs2-product-signed.macho")
    native_run(output / "fs2-product-signed.macho", output, "raw", "fs2-byte-roundtrip.bin")
    fs2_written = output / "fs2-byte-roundtrip.bin"
    if fs2_written.read_bytes() != b"\x00\xff\x80":
        raise ValueError("Mac FS2 B/C and A byte roundtrip changed")
    parameter = output / "parameter.kotoba"
    parameter.write_text(checker.PARAMETER)
    refused_parameter = native_run(producer, output, "compile", parameter.name,
                                   "--target", checker.TARGET, "--output", "parameter.elf",
                                   expected=1)
    if b"E7102" not in refused_parameter.stderr or (output / "parameter.elf").exists():
        raise ValueError("v1 parameter was not refused without an artifact")
    if (pin(compiler) != compiler_pin or pin(packager) != packager_pin
            or pin(MANIFEST) != manifest_pin or pin(USER_CHECK) != checker_pin
            or pin(FS2_PRODUCT) != fs2_product_pin
            or pin(PACKAGER_SOURCE) != packager_source_pin
            or (descriptor_pin is not None and pin(ROOT_DESCRIPTOR) != descriptor_pin)
            or pin(output / "full-unity.kotoba") != unity
            or any(pin(ROOT / row["name"]) != {key: row[key] for key in ("bytes", "sha256")}
                   for row in sources)):
        raise ValueError("input changed during Mac gate")
    report = {"schema": "amu.mac-aiueos-user-target.v3",
              "status": "PASS_MAC_NATIVE_USER_TARGET_SELFHOST",
              "compiler": compiler_pin, "packager": packager_pin,
              "manifest": manifest_pin, "source": unity, "sources": sources,
              "generations": rows, "fixedPointGeneration": len(rows),
              "packagerSelfRebuild": packager_rebuild,
              "bootstrapDescriptor": descriptor_pin,
              "userSource": pin(scalar), "userElf": pin(image),
              "userPayloadSlot": pin(slot),
              "userPayloadExistingOutputRefused": True,
              "userPayloadMissingInputRefused": True,
              "userPayloadOversizedInputRefused": True,
              "effectSource": pin(effect), "undeclaredEffectRefused": True,
              "parameterSource": pin(parameter), "parameterRefused": True,
              "fs2ProductRaw": {"status": "PASS_MAC_FS2_RAW_BYTES",
                                "source": fs2_product_pin,
                                "container": pin(output / "fs2-product.kseed"),
                                "raw": pin(output / "fs2-product.raw"),
                                "image": fs2_image_pin, "stored": pin(fs2_written)},
              "guestExecution": False, "ItonamiTurn": False,
              "releaseAdmission": False, "linuxProcessInThisGate": False,
              "userVerifier": checker_pin, "observer": pin(Path(__file__))}
    (output / "mac-aiueos-user-target.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], report["userElf"]["sha256"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler-image", type=Path)
    parser.add_argument("--compiler-sha256")
    parser.add_argument("--packager-image", type=Path)
    parser.add_argument("--packager-sha256")
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args())
