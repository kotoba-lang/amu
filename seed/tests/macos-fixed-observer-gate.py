#!/usr/bin/env python3
"""Test-only launcher/observer for an already-built native Kotoba packager.

The packager and tested host image are native. This file only stages a private
directory, signs/launches the image, and checks its observed output.
"""
import argparse
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("packager", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="awai153-fixed-observer-") as tmp:
        root = Path(tmp)
        fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            # The diagnostic FS2 packager uses the designated directory FD 3.
            if fd != 3:
                raise RuntimeError("test launcher requires an unused FD 3")
            subprocess.run([str(args.packager.resolve()), "observer-unsigned.macho"],
                           cwd=root, pass_fds=(fd,), check=True, timeout=10,
                           capture_output=True)
            image = root / "observer.macho"
            image.write_bytes((root / "observer-unsigned.macho").read_bytes())
            image.chmod(0o700)
            subprocess.run(["/usr/bin/codesign", "--force", "--sign", "-", str(image)],
                           check=True, timeout=10, capture_output=True)
            result = subprocess.run([str(image)], check=True, timeout=10, capture_output=True)
            if len(result.stdout) != 113 or not re.fullmatch(rb"[0-9a-f]{112}\n", result.stdout):
                raise AssertionError("malformed fixed observation")
            magic, version, memory, total, available, used, pressure, block_size, blocks = \
                struct.unpack("<4sIQQQQIIQ", bytes.fromhex(result.stdout.decode().strip()))
            actual_memory = int(subprocess.check_output(["/usr/sbin/sysctl", "-n", "hw.memsize"], timeout=5))
            actual_disk = int(subprocess.check_output(["/bin/df", "-Pk", "/"], text=True, timeout=5)
                              .splitlines()[1].split()[3])
            assert magic == b"AOS1" and version == 1 and memory == actual_memory
            assert available <= total and used <= total and 0 <= pressure <= 100 and block_size > 0
            # Disk use may change between observations; this is not a reservation.
            assert abs(block_size * blocks // 1024 - actual_disk) < 65536
            denied = subprocess.run([str(image), "unexpected"], timeout=10, capture_output=True)
            assert denied.returncode == 1 and not denied.stdout
            print("native fixed observer: valid record and argument refusal")
        finally:
            os.close(fd)


if __name__ == "__main__":
    main()
