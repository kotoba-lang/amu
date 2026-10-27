#!/usr/bin/env python3
"""Rebuild the bounded general-entry Mac packager without a Linux process."""

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
SOURCE = ROOT / "docs/evidence/mac-generic-packager-20261026/packager-v2.kotoba"
PINS = {
    "source": "bdfcaa02041623fca241352a092c5033b74f83faf0209c0fafefeb99278f9a66",
    "compiler": "78a006e488b72ea75542bfc592bf80c9a31f9be441df8e98ddb41950ca373717",
    "bootstrap": "5a683407fd72eebd349ffcfa184baf46024743f2cb91a4845e2bcbbe3074a8d1",
    "full_raw": "48f724c12ece45c9ba57550932536533a2e340cea27812fb25251678cac97fdd",
    "container": "bd5a9e2cfcad053023a8c2cb9f059e24f267afc642c37f84d41bdda380c841f1",
    "packager_raw": "85b7eed0a4435e6f6d9a6a305de31c49b069dfe65320223d9286ca908020b8fc",
    "packager_unsigned": "14281f2326b7ba115369aa114644bc8e40d41a50032661573c0e87ff36828173",
    "full_unsigned": "40a30d60c8df36d8f72cf1207952a355b1e563e0729fdb02be11b38560b5baa4",
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def pin(path: Path, name: str) -> None:
    if digest(path) != PINS[name]:
        raise RuntimeError(f"{name} digest changed: {path}")


def process(command: list[str], *, expected=0, **kwargs) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(command, capture_output=True, timeout=120, check=False, **kwargs)
    if result.returncode != expected or result.stderr:
        raise RuntimeError(
            f"{command[0]} exit {result.returncode}, expected {expected}: "
            f"{result.stderr.decode(errors='replace')[:500]}"
        )
    return result


def native(image: Path, root: Path, *args: str, expected=0) -> subprocess.CompletedProcess[bytes]:
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        if fd != 3:
            raise RuntimeError(f"expected scoped root on FD3, got FD{fd}")
        return process([str(image), *args], expected=expected, cwd=root, pass_fds=(fd,))
    finally:
        os.close(fd)


def verify(image: Path) -> None:
    process(["/usr/bin/codesign", "--verify", "--strict", str(image)])
    dylibs = process(["/usr/bin/otool", "-L", str(image)]).stdout.splitlines()
    if dylibs != [f"{image}:".encode()]:
        raise RuntimeError(f"unexpected dylib load command: {image}")


def sign(source: Path, dest: Path) -> Path:
    shutil.copyfile(source, dest)
    dest.chmod(0o755)
    process(["/usr/bin/codesign", "--force", "--sign", "-", str(dest)])
    verify(dest)
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler-image", type=Path, required=True)
    parser.add_argument("--bootstrap-packager-image", type=Path, required=True)
    parser.add_argument("--full-raw", type=Path, required=True)
    parser.add_argument("--scratch-root", type=Path, required=True)
    args = parser.parse_args()
    compiler = args.compiler_image.resolve(strict=True)
    bootstrap = args.bootstrap_packager_image.resolve(strict=True)
    full_raw = args.full_raw.resolve(strict=True)
    scratch = args.scratch_root.resolve(strict=True)
    for path, name in ((SOURCE, "source"), (compiler, "compiler"),
                       (bootstrap, "bootstrap"), (full_raw, "full_raw")):
        pin(path, name)
    verify(compiler)
    verify(bootstrap)

    with tempfile.TemporaryDirectory(prefix="mac-generic-packager-", dir=scratch) as tmp:
        root = Path(tmp)
        shutil.copyfile(SOURCE, root / "packager.kotoba")
        shutil.copyfile(full_raw, root / "full.raw")
        compiled = native(compiler, root, "compile", "packager.kotoba",
                          "--target", "aarch64-macos", "--output", "packager.kseed")
        if b":bytes 39534}" not in compiled.stdout:
            raise RuntimeError("packager container size changed")
        pin(root / "packager.kseed", "container")
        extracted = native(compiler, root, "extract-native", "packager.kseed",
                           "--symbol", "main", "--output", "packager.raw")
        if not re.search(rb":offset 35312, :length 39505, :arity 0}", extracted.stdout):
            raise RuntimeError("packager entry or raw size changed")
        pin(root / "packager.raw", "packager_raw")

        mode = "fs2-cli-stdio-general"
        native(bootstrap, root, "packager-f1.macho", "packager.raw", mode, "35312")
        pin(root / "packager-f1.macho", "packager_unsigned")
        f1 = sign(root / "packager-f1.macho", root / "packager-f1-signed.macho")
        native(f1, root, "packager-f2.macho", "packager.raw", mode, "35312")
        pin(root / "packager-f2.macho", "packager_unsigned")
        f2 = sign(root / "packager-f2.macho", root / "packager-f2-signed.macho")
        native(f2, root, "full.macho", "full.raw", mode, "0")
        pin(root / "full.macho", "full_unsigned")
        full = sign(root / "full.macho", root / "full-signed.macho")

        refusals = {}
        for name, entry in (("nondecimal", "abc"), ("unaligned", "35313"),
                            ("out-of-bounds", "99999999")):
            target = name + ".macho"
            native(f2, root, target, "packager.raw", mode, entry, expected=2)
            if (root / target).exists():
                raise RuntimeError(f"{name} entry created output")
            refusals[name] = 2
        native(f2, root, "legacy.macho", "packager.raw", "fs2-cli-stdio", expected=2)
        if (root / "legacy.macho").exists():
            raise RuntimeError("legacy mode accepted a new raw length")
        refusals["legacy-length"] = 2

        full_sha = digest(full)
        sample = process([
            sys.executable, str(ROOT / "scripts/seed/check_macos_fs2_bc.py"),
            "--image", str(full), "--expected-image-sha256", full_sha,
            "--scratch-root", str(root),
        ])
        sample_receipt = json.loads(sample.stdout)
        if not sample_receipt.get("ok"):
            raise RuntimeError("Mac full compiler sample gate failed")
        print(json.dumps({
            "gate": "mac-generic-packager-diagnostic-v1", "ok": True,
            "source_sha256": PINS["source"],
            "packager_container_sha256": PINS["container"],
            "packager_entry_offset": 35312,
            "packager_f1_f2_unsigned_sha256": PINS["packager_unsigned"],
            "full_compiler_unsigned_sha256": PINS["full_unsigned"],
            "full_compiler_signed_sha256": full_sha,
            "refusals": refusals,
            "sample_gate": sample_receipt["gate"],
            "sample_output_sha256": sample_receipt["output_sha256"],
        }, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.TimeoutExpired, ValueError) as error:
        print(f"FAIL mac-generic-packager-diagnostic-v1: {error}", file=sys.stderr)
        sys.exit(1)
