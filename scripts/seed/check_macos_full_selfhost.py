#!/usr/bin/env python3
"""Rebuild full Amu compiler twice on Mac with Mac-native packaging.

Python only stages the pinned unity source and observes native processes.
Run this heavyweight diagnostic through native_build_queue.py.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "seed/FULL-MANIFEST"
UNITY_SHA = "24039e0f0ed95eaad39b71cbd9d71f1e38bd440dc8d0b505b3adfb9aeb347f82"
COMPILER_SHA = "522b3a105a109deec9ce5908407a414fc434b364453b4d89fc1572d1de51cd43"
PACKAGER_SHA = "ce940d5cfce2bb582a18487ba7ecce03a881961fb82bfc4e2d99b0f5ecf67698"
CONTAINER_SHA = "d6612951d7bb5dfdfe4814a26aae0ad8775dde207f80289de0e39b3ac44046c4"
RAW_SHA = "48f724c12ece45c9ba57550932536533a2e340cea27812fb25251678cac97fdd"
MACHO_SHA = "40a30d60c8df36d8f72cf1207952a355b1e563e0729fdb02be11b38560b5baa4"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require_digest(path: Path, expected: str) -> None:
    actual = digest(path)
    if actual != expected:
        raise RuntimeError(f"{path.name} SHA-256 changed: {actual}")


def run(command: list[str], *, timeout=180, **kwargs) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(command, capture_output=True, timeout=timeout, check=False, **kwargs)
    if result.returncode or result.stderr:
        raise RuntimeError(
            f"{command[0]} returned {result.returncode}: "
            f"{result.stderr.decode(errors='replace')[:600]}"
        )
    return result


def mac_run(image: Path, directory: Path, *args: str, timeout=180) -> subprocess.CompletedProcess[bytes]:
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    saved_fd3 = None
    try:
        if fd != 3:
            # native_build_queue passes its flock descriptor on FD3. Preserve
            # it in the child while granting the Mac image the root on FD3.
            os.fstat(3)
            saved_fd3 = os.dup(3)
            os.dup2(fd, 3)
        passed = (3,) if saved_fd3 is None else (3, saved_fd3)
        return run([str(image), *args], cwd=directory, pass_fds=passed, timeout=timeout)
    finally:
        if saved_fd3 is not None:
            os.dup2(saved_fd3, 3)
            os.close(saved_fd3)
        os.close(fd)


def verify_image(image: Path) -> None:
    run(["/usr/bin/codesign", "--verify", "--strict", str(image)], timeout=20)
    dylibs = run(["/usr/bin/otool", "-L", str(image)], timeout=20).stdout.splitlines()
    if dylibs != [f"{image}:".encode()]:
        raise RuntimeError(f"{image.name} has a dylib load command")


def stage_unity(output: Path) -> dict[str, str]:
    paths = [name for name in MANIFEST.read_text().splitlines()
             if name and not name.startswith("#")]
    if len(paths) != 47 or len(set(paths)) != 47:
        raise RuntimeError("FULL-MANIFEST module set changed")
    pieces = [(ROOT / name).read_bytes() + b"\n" for name in paths]
    target = output / "full-unity.kotoba"
    target.write_bytes(b"".join(pieces))
    require_digest(target, UNITY_SHA)
    return {"module_count": len(paths), "source_bytes": target.stat().st_size,
            "source_sha256": UNITY_SHA}


def generation(number: int, producer: Path, packager: Path, output: Path) -> dict[str, object]:
    start = time.monotonic()
    container = output / f"F{number}.kseed"
    raw = output / f"F{number}.raw"
    unsigned = output / f"F{number}.macho"
    signed = output / f"F{number}-signed.macho"
    compiled = mac_run(producer, output, "compile", "full-unity.kotoba",
                       "--target", "aarch64-macos", "--output", container.name)
    require_digest(container, CONTAINER_SHA)
    extracted = mac_run(producer, output, "extract-native", container.name,
                        "--symbol", "main", "--output", raw.name)
    if not re.search(rb":length 3250952, :arity 0}", extracted.stdout):
        raise RuntimeError(f"F{number} extract-native shape changed")
    require_digest(raw, RAW_SHA)
    mac_run(packager, output, unsigned.name, raw.name, "fs2-cli-stdio")
    require_digest(unsigned, MACHO_SHA)
    shutil.copyfile(unsigned, signed)
    signed.chmod(0o755)
    run(["/usr/bin/codesign", "--force", "--sign", "-", str(signed)], timeout=30)
    verify_image(signed)
    print(f"F{number}: Mac compile, extract, pack and sign passed in "
          f"{time.monotonic() - start:.1f}s", flush=True)
    return {
        "generation": number,
        "container_sha256": CONTAINER_SHA,
        "raw_sha256": RAW_SHA,
        "unsigned_macho_sha256": MACHO_SHA,
        "signed_macho_sha256": digest(signed),
        "compile_stdout": compiled.stdout.decode(),
        "extract_stdout": extracted.stdout.decode(),
        "elapsed_seconds": round(time.monotonic() - start, 3),
        "signed_image": signed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler-image", required=True, type=Path)
    parser.add_argument("--packager-image", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    compiler = args.compiler_image.resolve(strict=True)
    packager = args.packager_image.resolve(strict=True)
    output = args.output.resolve()
    require_digest(compiler, COMPILER_SHA)
    require_digest(packager, PACKAGER_SHA)
    verify_image(compiler)
    verify_image(packager)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    staged = stage_unity(output)
    print(f"staged {staged['module_count']} modules; SHA-256 {UNITY_SHA}", flush=True)
    f4 = generation(4, compiler, packager, output)
    f5 = generation(5, f4["signed_image"], packager, output)
    sample = run([
        sys.executable, str(ROOT / "scripts/seed/check_macos_fs2_bc.py"),
        "--image", str(f5["signed_image"]),
        "--expected-image-sha256", f5["signed_macho_sha256"],
        "--scratch-root", str(output),
    ], timeout=45)
    sample_receipt = json.loads(sample.stdout)
    if not sample_receipt.get("ok"):
        raise RuntimeError("F5 sample gate did not pass")
    for row in (f4, f5):
        del row["signed_image"]
    receipt = {
        "gate": "mac-full-selfhost-diagnostic-v1",
        "ok": True,
        "linux_processes_launched_by_gate": 0,
        "compiler_input_sha256": COMPILER_SHA,
        "packager_input_sha256": PACKAGER_SHA,
        "source": staged,
        "generations": [f4, f5],
        "sample_gate": sample_receipt,
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"gate": receipt["gate"], "ok": True, "output": str(output),
                      "container_sha256": CONTAINER_SHA,
                      "unsigned_macho_sha256": MACHO_SHA,
                      "sample_output_sha256": sample_receipt["output_sha256"]},
                     sort_keys=True), flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.TimeoutExpired, ValueError) as error:
        print(f"FAIL mac-full-selfhost-diagnostic-v1: {error}", file=sys.stderr)
        sys.exit(1)
