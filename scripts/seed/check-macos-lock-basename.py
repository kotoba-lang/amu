#!/usr/bin/env python3
"""Observe Mac FD3 lock admission with an explicitly pinned native compiler.

Python stages the Kotoba fixture and observes processes; it is not a compiler.
This limited gate does not qualify Linux execution, output-path handling or CI.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "seed/tests/mac-lock-basename.kotoba"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(image, root, args):
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        if fd != 3:
            raise RuntimeError(f"scope must be FD3, got {fd}")
        return subprocess.run([str(image), *args], cwd=root, pass_fds=(fd,),
                              capture_output=True, timeout=120, check=False)
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--scratch-root", required=True, type=Path)
    args = parser.parse_args()
    image = args.image.resolve(strict=True)
    scratch = args.scratch_root.resolve(strict=True)
    if sha(image) != args.sha256:
        raise RuntimeError("compiler digest mismatch")
    subprocess.run(["/usr/bin/codesign", "--verify", "--strict", str(image)], check=True)
    with tempfile.TemporaryDirectory(prefix="mac-lock-basename-", dir=scratch) as tmp:
        root = Path(tmp)
        shutil.copyfile(FIXTURE, root / "good.kotoba")
        lock = root / "good.ksl"
        lock.write_text("KSL1\nentry /good.kotoba\nfile " + sha(root / "good.kotoba") + " /good.kotoba\n")
        lock_hash = sha(lock)
        (root / "sub").mkdir()
        shutil.copyfile(lock, root / "sub/good.ksl")
        (root / "link.ksl").symlink_to("good.ksl")
        cases = [("valid", "good.ksl", lock_hash, 0),
                 ("absolute", "/good.ksl", lock_hash, 1),
                 ("nested", "sub/good.ksl", lock_hash, 1),
                 ("traversal", "../good.ksl", lock_hash, 1),
                 ("missing", "missing.ksl", lock_hash, 1),
                 ("symlink", "link.ksl", lock_hash, 1),
                 ("dot", ".", lock_hash, 1),
                 ("dotdot", "..", lock_hash, 1),
                 ("digest", "good.ksl", "0" * 64, 1)]
        results = []
        for name, path, digest, expected in cases:
            result = run(image, root, ["check", "/good.kotoba", "--source-lock", path,
                                       "--source-lock-sha256", digest])
            if result.returncode != expected or (expected and b"E6015" not in result.stderr):
                raise RuntimeError(f"{name}: exit {result.returncode}, stderr {result.stderr!r}")
            if not expected and (result.stdout != b"ok\n" or result.stderr):
                raise RuntimeError(f"{name}: unexpected success output")
            results.append({"name": name, "exit": result.returncode})
        command = ["compile", "/good.kotoba", "--target", "x86_64-linux", "--output",
                   "refused.elf", "--format", "static", "--source-lock", "/good.ksl",
                   "--source-lock-sha256", lock_hash]
        result = run(image, root, command)
        if result.returncode != 1 or b"E6015" not in result.stderr or (root / "refused.elf").exists():
            raise RuntimeError("invalid lock did not refuse static compilation without output")
        good_command = ["compile", "/good.kotoba", "--target", "x86_64-linux", "--output",
                        "valid.elf", "--format", "static", "--source-lock", "good.ksl",
                        "--source-lock-sha256", lock_hash]
        result = run(image, root, good_command)
        output = root / "valid.elf"
        if result.returncode or result.stderr or not output.is_file() or output.read_bytes()[:4] != b"\x7fELF":
            raise RuntimeError("valid lock did not produce a static ELF")
        sentinel = root / "existing.elf"
        sentinel.write_bytes(b"mac-lock-basename-sentinel\n")
        sentinel_hash = sha(sentinel)
        existing_command = good_command.copy()
        existing_command[5] = "existing.elf"
        result = run(image, root, existing_command)
        if result.returncode == 0 or sha(sentinel) != sentinel_hash:
            raise RuntimeError("existing output was not refused without modification")
        if sha(lock) != lock_hash:
            raise RuntimeError("source lock was modified")
        print(json.dumps({"gate": "mac-lock-basename-v1", "ok": True,
                          "compiler_sha256": args.sha256, "fixture_sha256": sha(FIXTURE),
                          "lock_sha256": lock_hash, "cases": results,
                          "refused_output_absent": True, "valid_elf_sha256": sha(output),
                          "existing_output_unchanged": True, "linux_guest_executed": False}, sort_keys=True))


if __name__ == "__main__":
    main()
