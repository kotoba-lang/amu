#!/usr/bin/env python3
"""Controls for write-bootstrap-descriptors.py (JUN-545).

Takes the outputs of the Mac gate and the cross gate (check-aiueos-user-macos-
native.py, check-macos-cross-linux-candidates.py) and runs, on copies:

1. the committed descriptors against their own receipts: DESCRIPTORS_CURRENT;
2. three refusals: one digit of the mac receipt, one byte of the x86 compiler,
   one byte of the signed fixed-point compiler;
3. a descriptor with a wrong digest is reported as differing (exit 1), --write
   repairs it to the committed bytes, and a second --check is current;
4. the source phase on the same receipt is current, an unknown cross-gate
   status is refused, and the final phase without a cross build is refused;
5. --install is refused without --write, installs nothing when the repository
   already holds the verified bytes, and restores a corrupted binary.
"""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
WRITER = ROOT / "scripts/seed/write-bootstrap-descriptors.py"
BINARIES = ("seed/bootstrap/aarch64-macos/amu-full-root.macho",
            "seed/bootstrap/aarch64-macos/kotoba-packager-root.macho",
            "seed/bootstrap/aarch64-linux-static-root.elf", "bin/amu-linux-x86_64")
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
        mutated = json.loads(original)
        digest = mutated["image"]["sha256"]
        mutated["image"]["sha256"] = ("0" if digest[0] != "0" else "1") + digest[1:]
        mutated["compilerGenerations"] = [dict(mutated["image"])] * 3
        for field in ("nativePinnedCheckAndCompile", "controllerQualified",
                      "currentCompilerLinkVerified", "broaderPublicCompatibilityQualified"):
            mutated[field] = True
        product.write_text(json.dumps(mutated, indent=2, ensure_ascii=False) + "\n")
        expect("descriptor negative control actually changes image digest",
               mutated["image"]["sha256"] != digest)
        r = run(args.mac_build, args.cross_build, repo)
        expect("a wrong descriptor digest is reported", r.returncode == 1 and "DESCRIPTORS_DIFFER" in r.stdout,
               r.stdout + r.stderr)
        r = run(args.mac_build, args.cross_build, repo, "--write")
        repaired = json.loads(product.read_text())
        expected = json.loads(original)
        expect("--write repairs pins and invalidates prior compiler qualification",
               r.returncode == 0 and repaired["image"] == expected["image"]
               and repaired["sourceUnity"] == expected["sourceUnity"]
               and repaired["sourceRevision"] is None
               and repaired["compilerGenerations"] == []
               and all(repaired[k] is False for k in
                       ("nativePinnedCheckAndCompile", "controllerQualified",
                        "currentCompilerLinkVerified", "broaderPublicCompatibilityQualified")),
               r.stdout + r.stderr)
        r = run(args.mac_build, args.cross_build, repo)
        expect("a second check is current", r.returncode == 0 and "DESCRIPTORS_CURRENT" in r.stdout, r.stdout)

    r = subprocess.run([sys.executable, "-I", str(WRITER), "--phase", "source",
                        "--mac-build", str(args.mac_build)], capture_output=True, text=True)
    expect("the source phase is current on the same receipt", r.returncode == 0 and "DESCRIPTORS_CURRENT" in r.stdout,
           r.stdout + r.stderr)
    r = subprocess.run([sys.executable, "-I", str(WRITER), "--mac-build", str(args.mac_build)],
                       capture_output=True, text=True)
    expect("the final phase needs a cross build", r.returncode == 2 and "REFUSED" in r.stderr, r.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        cross = Path(tmp) / "cross"
        shutil.copytree(args.cross_build, cross)
        receipt = cross / "cross.json"
        receipt.write_text(receipt.read_text().replace("MAC_NATIVE_CROSS_ARTIFACTS_UNEXECUTED", "SOMETHING_ELSE"))
        r = run(args.mac_build, cross)
        expect("an unknown cross status is refused", r.returncode == 2 and "REFUSED" in r.stderr, r.stderr)

    r = run(args.mac_build, args.cross_build, ROOT, "--install")
    expect("--install without --write is refused", r.returncode == 2 and "REFUSED" in r.stderr, r.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        for rel in FILES + BINARIES:
            (repo / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / rel, repo / rel)
        r = run(args.mac_build, args.cross_build, repo, "--write", "--install")
        expect("--install leaves a current repository alone",
               r.returncode == 0 and "installed" not in r.stdout and "DESCRIPTORS_CURRENT" in r.stdout, r.stdout + r.stderr)
        flip(repo / "bin/amu-linux-x86_64", 1000)
        r = run(args.mac_build, args.cross_build, repo, "--write", "--install")
        expect("--install restores a corrupted binary",
               r.returncode == 0 and "installed bin/amu-linux-x86_64" in r.stdout
               and (repo / "bin/amu-linux-x86_64").read_bytes() == (ROOT / "bin/amu-linux-x86_64").read_bytes(), r.stdout + r.stderr)

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        for rel in FILES:
            (repo / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / rel, repo / rel)
        candidate = repo / "examples/foundation-starter/candidate.json"
        candidate.parent.mkdir(parents=True)
        expected = json.loads((ROOT / "examples/foundation-starter/candidate.json").read_text())
        stale = json.loads(json.dumps(expected))
        stale["compilerImage"]["sha256"] = "0" * 64
        stale["compilerSourceUnity"]["sha256"] = "0" * 64
        stale["publicReleaseReady"] = True
        candidate.write_text(json.dumps(stale, indent=2) + "\n")
        r = run(args.mac_build, args.cross_build, repo, "--write")
        repaired = json.loads(candidate.read_text())
        product = json.loads((repo / "native-product.json").read_text())
        expect("changed compiler rebinds starter pins without carrying release authority",
               r.returncode == 0 and repaired["compilerImage"] == product["image"]
               and repaired["compilerSourceUnity"] == product["sourceUnity"]
               and repaired["upstreamRevision"] is None
               and repaired["publicReleaseReady"] is False
               and repaired["fixtures"] == expected["fixtures"], r.stdout + r.stderr)
        r = run(args.mac_build, args.cross_build, repo)
        expect("rebound starter is idempotent", r.returncode == 0 and "DESCRIPTORS_CURRENT" in r.stdout,
               r.stdout + r.stderr)

    print("PASS_BOOTSTRAP_DESCRIPTOR_WRITER" if not failures else f"FAILED {failures}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
