#!/usr/bin/env python3
"""Exercise the descriptor writer on a disposable receipt-derived fixture.

Ad-hoc Mac signatures can differ by host. This tests update/refusal behavior;
it does not assert that the checkout's signed descriptors match this host.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
FILES = ("scripts/seed/write-bootstrap-descriptors.py",
         "scripts/seed/test-write-bootstrap-descriptors.py",
         "examples/foundation-starter/candidate.json",
         "seed/bootstrap/aarch64-macos/root.json",
         "seed/bootstrap/aarch64-linux-static-root.json", "native-product.json",
         "seed/bootstrap/aarch64-macos/amu-full-root.macho",
         "seed/bootstrap/aarch64-macos/kotoba-packager-root.macho",
         "seed/bootstrap/aarch64-linux-static-root.elf", "bin/amu-linux-x86_64")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mac-build", type=Path, required=True)
    parser.add_argument("--cross-build", type=Path, required=True)
    args = parser.parse_args()
    mac, cross = args.mac_build.resolve(strict=True), args.cross_build.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="descriptor-writer-ci-") as tmp:
        repo = Path(tmp)
        for rel in FILES:
            dst = repo / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, dst)
        writer = repo / "scripts/seed/write-bootstrap-descriptors.py"
        test = repo / "scripts/seed/test-write-bootstrap-descriptors.py"
        # Writer validates receipts and hashes before modifying this fixture.
        subprocess.run([sys.executable, "-I", str(writer), "--mac-build", str(mac),
                        "--cross-build", str(cross), "--repo", str(repo),
                        "--write", "--install"], check=True)
        subprocess.run([sys.executable, "-I", str(test), "--mac-build", str(mac),
                        "--cross-build", str(cross)], check=True)
    print("PASS_DISPOSABLE_DESCRIPTOR_WRITER_FIXTURE", flush=True)


if __name__ == "__main__":
    main()
