#!/usr/bin/env python3
"""Controls for write-bootstrap-descriptors.py (JUN-545).

Takes the outputs of the Mac gate and the cross gate (check-aiueos-user-macos-
native.py, check-macos-cross-linux-candidates.py) and runs, on copies:

1. the committed descriptors against their own receipts: DESCRIPTORS_CURRENT;
2. three refusals: one digit of the mac receipt, one byte of the x86 compiler,
   one byte of the signed fixed-point compiler;
3. a descriptor with a wrong digest is reported as differing (exit 1), --write
   repairs it to the committed bytes, and a second --check is current.
"""

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
WRITER = ROOT / "scripts/seed/write-bootstrap-descriptors.py"
FILES = ("seed/bootstrap/aarch64-macos/root.json",
         "seed/bootstrap/aarch64-linux-static-root.json", "native-product.json")


def run(mac, cross, repo=ROOT, *extra):
    return subprocess.run([sys.executable, "-I", str(WRITER), "--mac-build", str(mac),
                           "--cross-build", str(cross), "--repo", str(repo), *extra],
                          capture_output=True, text=True)


def flip(path, offset):
    data = bytearray(path.read_bytes())
    data[offset] ^= 1
    path.write_bytes(bytes(data))


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mac-build", type=Path, required=True)
    ap.add_argument("--cross-build", type=Path, required=True)
    args = ap.parse_args(argv)
    failures = []

    def expect(name, cond, detail=""):
        print(("ok   " if cond else "FAIL ") + name + (f"  {detail}" if not cond else ""))
        if not cond:
            failures.append(name)

    r = run(args.mac_build, args.cross_build)
    expect("committed descriptors are current", r.returncode == 0 and "DESCRIPTORS_CURRENT" in r.stdout,
           r.stdout + r.stderr)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        mac, cross = tmp / "mac", tmp / "cross"
        shutil.copytree(args.mac_build, mac)
        shutil.copytree(args.cross_build, cross)

        receipt = mac / "mac-aiueos-user-target.json"
        text = receipt.read_text()
        i = text.index("e031180f") if "e031180f" in text else text.index('"sha256"') + 12
        receipt.write_text(text[:i] + ("f" if text[i] != "f" else "e") + text[i + 1:])
        r = run(mac, args.cross_build)
        expect("one digit of the mac receipt is refused", r.returncode == 2 and "REFUSED" in r.stderr, r.stderr)
        shutil.copy(args.mac_build / "mac-aiueos-user-target.json", receipt)

        flip(cross / "F-x86_64.elf", 100)
        r = run(args.mac_build, cross)
        expect("one byte of the x86 compiler is refused", r.returncode == 2 and "REFUSED" in r.stderr, r.stderr)
        shutil.copy(args.cross_build / "F-x86_64.elf", cross / "F-x86_64.elf")

        flip(mac / "F2-signed.macho", 5000)
        r = run(mac, args.cross_build)
        expect("one byte of the signed compiler is refused", r.returncode == 2 and "REFUSED" in r.stderr, r.stderr)

        repo = tmp / "repo"
        for rel in FILES:
            (repo / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / rel, repo / rel)
        product = repo / "native-product.json"
        original = product.read_text()
        product.write_text(original.replace("b8652a6d9b55", "000000000000", 1))
        r = run(args.mac_build, args.cross_build, repo)
        expect("a wrong descriptor digest is reported", r.returncode == 1 and "DESCRIPTORS_DIFFER" in r.stdout,
               r.stdout + r.stderr)
        r = run(args.mac_build, args.cross_build, repo, "--write")
        expect("--write repairs it", r.returncode == 0 and product.read_text() == original, r.stdout + r.stderr)
        r = run(args.mac_build, args.cross_build, repo)
        expect("a second check is current", r.returncode == 0 and "DESCRIPTORS_CURRENT" in r.stdout, r.stdout)

    print("PASS_BOOTSTRAP_DESCRIPTOR_WRITER" if not failures else f"FAILED {failures}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
