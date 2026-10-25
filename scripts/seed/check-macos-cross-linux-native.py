#!/usr/bin/env python3
"""Execute Mac-produced Linux compiler candidates on their native ISA.

Linux is an independent verifier here, never the producer of the candidate
under test. This bounded fixed-point check does not replace full native CI.
"""

import argparse
import hashlib
import json
import os
import platform
import shutil
import struct
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FULL = ROOT / "seed/FULL-MANIFEST"


def pin(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def check_elf(path, machine):
    raw = path.read_bytes()
    if raw[:8] != b"\x7fELF\x02\x01\x01\0" or struct.unpack_from("<HH", raw, 16) != (2, machine):
        raise ValueError("wrong Linux static ELF target")
    offset = struct.unpack_from("<Q", raw, 32)[0]
    size, count = struct.unpack_from("<HH", raw, 54)
    if size != 56 or not 0 < count <= 16 or offset + count * size > len(raw):
        raise ValueError("invalid ELF program headers")
    types = [struct.unpack_from("<I", raw, offset + i * size)[0] for i in range(count)]
    if 2 in types or 3 in types:
        raise ValueError("dynamic image or interpreter")
    return pin(path)


def main(candidate, output, isa):
    expected_machine = {"aarch64": ("aarch64", "arm64"), "x86_64": ("x86_64",)}
    if platform.system() != "Linux" or platform.machine() not in expected_machine[isa]:
        raise ValueError("native Linux " + isa + " kernel required")
    if candidate.is_symlink() or not candidate.is_dir():
        raise ValueError("regular candidate directory required")
    record = json.loads((candidate / "cross.json").read_text())
    if record.get("schema") != "amu.mac-cross-linux-candidates.v1" or record.get("status") != "MAC_NATIVE_CROSS_ARTIFACTS_UNEXECUTED":
        raise ValueError("unexpected Mac candidate record")
    if pin(ROOT / "seed/x86_64-kx64-runner.kotoba") != record["runnerSource"]:
        raise ValueError("runner source changed since Mac generation")
    paths = [name for name in FULL.read_text().splitlines() if name and not name.startswith("#")]
    if len(paths) != 47 or len(set(paths)) != 47:
        raise ValueError("unexpected complete manifest")
    if pin(FULL) != record["fullSource"]["manifest"]:
        raise ValueError("full manifest changed")
    full_bytes = b"".join((ROOT / name).read_bytes() + b"\n" for name in paths)
    full_pin = {"bytes": len(full_bytes), "sha256": hashlib.sha256(full_bytes).hexdigest()}
    if full_pin != record["fullSource"]["unity"]:
        raise ValueError("full source changed since Mac generation")
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    full = output / "full-unity.kotoba"
    full.write_bytes(full_bytes)
    for filename, field in (("F.kseed", "container"), ("F-aarch64.elf", "aarch64Root"),
                            ("F-x86_64.elf", "x86FullCompiler"), ("S-x86_64.elf", "x86SelfhostCompiler")):
        source = candidate / filename
        if source.is_symlink() or not source.is_file() or pin(source) != record[field]:
            raise ValueError("Mac candidate artifact changed: " + filename)
    image_name = "F-aarch64.elf" if isa == "aarch64" else "F-x86_64.elf"
    image = output / image_name
    shutil.copyfile(candidate / image_name, image)
    image.chmod(0o700)
    original = check_elf(image, 183 if isa == "aarch64" else 62)
    env = {"PATH": "/nonexistent", "KEXE_CAP_RESOURCES_35": str(output),
           "KEXE_STACK_BYTES": "8388608"}
    calls = []

    def run(name, argv):
        started = time.monotonic()
        result = subprocess.run([str(item) for item in argv], cwd=output, env=env,
                                capture_output=True, timeout=1200, check=False)
        calls.append({"name": name, "exit": result.returncode,
                      "seconds": round(time.monotonic() - started, 3),
                      "stdoutSHA256": hashlib.sha256(result.stdout).hexdigest(),
                      "stderrSHA256": hashlib.sha256(result.stderr).hexdigest()})
        if result.returncode or result.stderr:
            raise ValueError(f"{name} failed: exit={result.returncode} " +
                             result.stderr.decode(errors="replace")[-800:])

    generations = [original]
    previous = image
    for number in (1, 2):
        fresh = output / f"F{number}.elf"
        if isa == "aarch64":
            container = output / f"F{number}.kseed"
            run(f"F{number}-compile", [previous, "compile", full,
                                       "--target", "aarch64-macos", "--output", container])
            if pin(container) != record["container"]:
                raise ValueError("native ARM compiler container differs from Mac")
            runner = output / "runner.kotoba"
            if not runner.exists():
                shutil.copyfile(ROOT / "seed/x86_64-kx64-runner.kotoba", runner)
            run(f"F{number}-pack", [previous, "compile", runner,
                                    "--target", "aarch64-linux", "--output", fresh,
                                    "--format", "packed", "--payload", container])
        else:
            run(f"F{number}-compile", [previous, "compile", full,
                                       "--target", "x86_64-linux", "--output", fresh,
                                       "--format", "static"])
        fresh.chmod(0o700)
        generations.append(check_elf(fresh, 183 if isa == "aarch64" else 62))
        previous = fresh
    if not generations[0] == generations[1] == generations[2]:
        raise ValueError("Mac-produced Linux compiler did not self-rebuild byte for byte")
    if pin(candidate / image_name) != original:
        raise ValueError("candidate input changed during execution")
    receipt = {"schema": "amu.mac-cross-native-fixed-point.v1",
               "status": "PASS_MAC_CROSS_NATIVE_FIXED_POINT",
               "isa": isa, "macCandidate": pin(candidate / "cross.json"),
               "source": full_pin, "generations": generations, "calls": calls,
               "linuxWasIndependentVerifier": True,
               "fullNativeCorpusQualified": False,
               "publicProductAdopted": False,
               "observer": pin(Path(__file__))}
    (output / "native-fixed-point.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["status"], isa, original["sha256"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--isa", choices=("aarch64", "x86_64"), required=True)
    args = parser.parse_args()
    main(args.candidate.resolve(), args.output.resolve(), args.isa)
