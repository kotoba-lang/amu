#!/usr/bin/env python3
"""Passwordless Mac packager self-rebuild diagnostic (no Linux process in this gate)."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs/evidence/mac-packager-selfhost-20261026/packager-v1.kotoba"
SOURCE_SHA = "22e03a24b9b2bb2d45552799bbe2284030a19d27212ca84c9bdc8fec8831fce0"
COMPILER_SHA = "3dcdaac995fb01a149234e4eb272e78951a33e01904f3adc5c1a33dbff4c6ba2"
BOOTSTRAP_PACKAGER_SHA = "14022d47804c251f5095502b7b29fab747736e1e84258a1fdd08d04c8038d4ca"
FULL_RAW_SHA = "48f724c12ece45c9ba57550932536533a2e340cea27812fb25251678cac97fdd"
PACKAGER_CONTAINER_SHA = "7716f3f7bbdbbbc2ead5fa75731ab1f92764698ab47334c49dd8b0fe52b0e312"
PACKAGER_RAW_SHA = "391dcde64fc44033c555632213b6cd8f654f4d83f188d4d0dc3402ebc942ff33"
PACKAGER_UNSIGNED_SHA = "895a5d571711f31ea9e9ca7f1b45a97aa08a9123081c2db48ce6e2d51f5858eb"
FULL_UNSIGNED_SHA = "40a30d60c8df36d8f72cf1207952a355b1e563e0729fdb02be11b38560b5baa4"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require_pin(path: Path, expected: str) -> None:
    if digest(path) != expected:
        raise RuntimeError(f"digest mismatch: {path.name}")


def checked(command: list[str], **kwargs) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(command, capture_output=True, timeout=120, check=False, **kwargs)
    if result.returncode or result.stderr:
        raise RuntimeError(
            f"command failed ({result.returncode}): {command[0]} "
            f"{result.stderr.decode(errors='replace')[:500]}"
        )
    return result


def mac_run(image: Path, root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        if fd != 3:
            raise RuntimeError(f"expected scoped root on FD3, got FD{fd}")
        return checked([str(image), *args], cwd=root, pass_fds=(fd,))
    finally:
        os.close(fd)


def signed_copy(source: Path, dest: Path) -> Path:
    shutil.copyfile(source, dest)
    dest.chmod(0o755)
    checked(["/usr/bin/codesign", "--force", "--sign", "-", str(dest)])
    checked(["/usr/bin/codesign", "--verify", "--strict", str(dest)])
    return dest


def verify_image(path: Path) -> None:
    checked(["/usr/bin/codesign", "--verify", "--strict", str(path)])
    load = checked(["/usr/bin/otool", "-L", str(path)]).stdout.splitlines()
    if load != [f"{path}:".encode()]:
        raise RuntimeError(f"unexpected dylib load command: {path.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler-image", required=True, type=Path)
    parser.add_argument("--bootstrap-packager-image", required=True, type=Path)
    parser.add_argument("--full-raw", required=True, type=Path)
    parser.add_argument("--scratch-root", required=True, type=Path)
    args = parser.parse_args()
    compiler = args.compiler_image.resolve(strict=True)
    bootstrap = args.bootstrap_packager_image.resolve(strict=True)
    full_raw = args.full_raw.resolve(strict=True)
    scratch = args.scratch_root.resolve(strict=True)
    for path, sha in ((SOURCE, SOURCE_SHA), (compiler, COMPILER_SHA),
                      (bootstrap, BOOTSTRAP_PACKAGER_SHA), (full_raw, FULL_RAW_SHA)):
        require_pin(path, sha)
    verify_image(compiler)
    verify_image(bootstrap)

    with tempfile.TemporaryDirectory(prefix="mac-packager-self-", dir=scratch) as tmp:
        root = Path(tmp)
        shutil.copyfile(SOURCE, root / "packager.kotoba")
        shutil.copyfile(full_raw, root / "full-f2.raw")
        built = mac_run(compiler, root, "compile", "packager.kotoba",
                        "--target", "aarch64-macos", "--output", "packager.kseed")
        if b":bytes 38838}" not in built.stdout:
            raise RuntimeError("packager container byte count changed")
        require_pin(root / "packager.kseed", PACKAGER_CONTAINER_SHA)
        extracted = mac_run(compiler, root, "extract-native", "packager.kseed",
                            "--symbol", "main", "--output", "packager.raw")
        if not re.search(rb":offset 34980, :length 38809, :arity 0}", extracted.stdout):
            raise RuntimeError("packager entry or raw length changed")
        require_pin(root / "packager.raw", PACKAGER_RAW_SHA)

        mac_run(bootstrap, root, "packager-f1.macho", "packager.raw", "fs2-cli-stdio")
        require_pin(root / "packager-f1.macho", PACKAGER_UNSIGNED_SHA)
        f1 = signed_copy(root / "packager-f1.macho", root / "packager-f1-signed.macho")
        verify_image(f1)
        mac_run(f1, root, "packager-f2.macho", "packager.raw", "fs2-cli-stdio")
        require_pin(root / "packager-f2.macho", PACKAGER_UNSIGNED_SHA)
        f2 = signed_copy(root / "packager-f2.macho", root / "packager-f2-signed.macho")
        verify_image(f2)

        mac_run(f2, root, "full-f2.macho", "full-f2.raw", "fs2-cli-stdio")
        require_pin(root / "full-f2.macho", FULL_UNSIGNED_SHA)
        full = signed_copy(root / "full-f2.macho", root / "full-f2-signed.macho")
        verify_image(full)
        full_sha = digest(full)
        sample = checked([
            sys.executable, str(ROOT / "scripts/seed/check_macos_fs2_bc.py"),
            "--image", str(full), "--expected-image-sha256", full_sha,
            "--scratch-root", str(root),
        ])
        sample_receipt = json.loads(sample.stdout)
        if not sample_receipt.get("ok"):
            raise RuntimeError("Mac full compiler sample gate did not pass")
        print(json.dumps({
            "gate": "mac-packager-selfhost-diagnostic-v1",
            "ok": True,
            "source_sha256": SOURCE_SHA,
            "packager_container_sha256": PACKAGER_CONTAINER_SHA,
            "packager_raw_sha256": PACKAGER_RAW_SHA,
            "packager_entry_offset": 34980,
            "packager_f1_f2_unsigned_sha256": PACKAGER_UNSIGNED_SHA,
            "full_compiler_unsigned_sha256": FULL_UNSIGNED_SHA,
            "full_compiler_signed_sha256": full_sha,
            "sample_gate": sample_receipt["gate"],
            "sample_output_sha256": sample_receipt["output_sha256"],
        }, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.TimeoutExpired, ValueError) as error:
        print(f"FAIL mac-packager-selfhost-diagnostic-v1: {error}", file=sys.stderr)
        sys.exit(1)
