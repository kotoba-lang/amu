#!/usr/bin/env python3
"""Passwordless, scoped Mac full-compiler diagnostic gate (not selfhost proof)."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


EXPECTED_ELF_SHA256 = "50bf68c6ea23a4b3325e7f29292fb132b90077f1eea15a4306d538190b4e6791"
EXPECTED_COMPILE_STDOUT = (
    b"{:ok true, :target :aarch64-linux, :format :static, "
    b":code-bytes 301650, :bytes 307712}\n"
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run(image: Path, root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        if fd != 3:
            raise RuntimeError(f"expected free FD3 for scoped FS2 root, got FD{fd}")
        return subprocess.run(
            [str(image), *args], cwd=root, pass_fds=(fd,),
            capture_output=True, timeout=30, check=False,
        )
    finally:
        os.close(fd)


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise RuntimeError(reason)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--expected-image-sha256", required=True)
    parser.add_argument("--scratch-root", required=True, type=Path)
    args = parser.parse_args()
    image = args.image.resolve(strict=True)
    scratch = args.scratch_root.resolve(strict=True)
    fixture = Path(__file__).resolve().parents[2] / "seed/macos-utf8-main.kotoba"
    require(sha256(image) == args.expected_image_sha256, "Mac image SHA-256 mismatch")
    subprocess.run(["/usr/bin/codesign", "--verify", "--strict", str(image)], check=True)
    load = subprocess.run(["/usr/bin/otool", "-L", str(image)], check=True, capture_output=True)
    require(load.stdout.splitlines() == [f"{image}:".encode()], "unexpected dylib load command")

    with tempfile.TemporaryDirectory(prefix="mac-fs2-bc-", dir=scratch) as tmp:
        root = Path(tmp) / "root"
        root.mkdir()
        shutil.copyfile(fixture, root / "sample.kotoba")
        check = run(image, root, "check", "sample.kotoba")
        require((check.returncode, check.stdout, check.stderr) == (0, b"ok\n", b""), "check mismatch")
        command = ("compile", "sample.kotoba", "--target", "aarch64-linux",
                   "--output", "sample.elf", "--format", "static")
        compiled = run(image, root, *command)
        require((compiled.returncode, compiled.stdout, compiled.stderr) ==
                (0, EXPECTED_COMPILE_STDOUT, b""), "compile mismatch")
        output = root / "sample.elf"
        require(output.is_file() and output.stat().st_size == 307712, "ELF output missing or wrong size")
        require(output.read_bytes()[:4] == b"\x7fELF", "output is not ELF")
        require(sha256(output) == EXPECTED_ELF_SHA256, "ELF digest mismatch")
        existing = run(image, root, *command)
        require(existing.returncode == 2 and existing.stdout == b"" and
                b"E7100" in existing.stderr, "existing output was not refused")
        traversal = run(image, root, "compile", "sample.kotoba", "--target",
                        "aarch64-linux", "--output", "../escape.elf", "--format", "static")
        require(traversal.returncode != 0 and not (Path(tmp) / "escape.elf").exists(),
                "traversal output escaped the scoped root")
        print(json.dumps({
            "gate": "mac-fs2-bc-diagnostic-v1", "ok": True,
            "image_sha256": args.expected_image_sha256,
            "check_exit": check.returncode, "compile_exit": compiled.returncode,
            "output_bytes": output.stat().st_size, "output_sha256": sha256(output),
            "existing_output_exit": existing.returncode,
            "traversal_exit": traversal.returncode,
            "traversal_created_file": False,
        }, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(f"FAIL mac-fs2-bc-diagnostic-v1: {error}", file=sys.stderr)
        sys.exit(1)
