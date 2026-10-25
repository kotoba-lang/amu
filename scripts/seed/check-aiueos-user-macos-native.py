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
    if len(names) != 47 or len(set(names)) != 47:
        raise ValueError("FULL-MANIFEST must contain 47 unique modules")
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
    compiler = args.compiler_image.resolve(strict=True)
    packager = args.packager_image.resolve(strict=True)
    compiler_pin = require_regular(compiler, args.compiler_sha256)
    packager_pin = require_regular(packager, args.packager_sha256)
    manifest_pin = require_regular(MANIFEST)
    checker_pin = require_regular(USER_CHECK)
    verify_macho(compiler)
    verify_macho(packager)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    sources, unity = stage_unity(output)
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

    spec = importlib.util.spec_from_file_location("user_check", USER_CHECK)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    scalar = output / "scalar.kotoba"
    scalar.write_text(checker.SOURCE)
    native_run(producer, output, "compile", scalar.name, "--target", checker.TARGET,
               "--output", "scalar.elf")
    image = output / "scalar.elf"
    checker.verify(image.read_bytes())
    effect = output / "effect.kotoba"
    effect.write_text(checker.EFFECT)
    refused = native_run(producer, output, "compile", effect.name,
                         "--target", checker.TARGET, "--output", "effect.elf",
                         expected=1)
    if b"E7101" not in refused.stderr or (output / "effect.elf").exists():
        raise ValueError("undeclared effect was not refused without an artifact")
    if (pin(compiler) != compiler_pin or pin(packager) != packager_pin
            or pin(MANIFEST) != manifest_pin or pin(USER_CHECK) != checker_pin
            or pin(output / "full-unity.kotoba") != unity
            or any(pin(ROOT / row["name"]) != {key: row[key] for key in ("bytes", "sha256")}
                   for row in sources)):
        raise ValueError("input changed during Mac gate")
    report = {"schema": "amu.mac-aiueos-user-target.v1",
              "status": "PASS_MAC_NATIVE_USER_TARGET_SELFHOST",
              "compiler": compiler_pin, "packager": packager_pin,
              "manifest": manifest_pin, "source": unity, "sources": sources,
              "generations": rows, "fixedPointGeneration": len(rows),
              "userSource": pin(scalar), "userElf": pin(image),
              "effectSource": pin(effect), "undeclaredEffectRefused": True,
              "guestExecution": False, "ItonamiTurn": False,
              "releaseAdmission": False, "linuxProcessInThisGate": False,
              "userVerifier": checker_pin, "observer": pin(Path(__file__))}
    (output / "mac-aiueos-user-target.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], report["userElf"]["sha256"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler-image", type=Path, required=True)
    parser.add_argument("--compiler-sha256", required=True)
    parser.add_argument("--packager-image", type=Path, required=True)
    parser.add_argument("--packager-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args())
