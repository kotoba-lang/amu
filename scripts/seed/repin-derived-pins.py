#!/usr/bin/env python3
"""Regenerate every derived seed pin for the current tree in one command.

JUN-631 / ADR 0388. Derived pins (compiler images, descriptors, the public
Mac CLI) are outputs of the seed sources. A seed PR that is behind main
must never hand-resolve them: merge main, take main's side of each pin file
(`--take-pins-from FETCH_HEAD`), then run this to rebuild all of them on the
merged source with the repository's own two-phase writer. Mac arm64 only;
the native compiler does the work, this script stages and hashes.
"""
import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "scripts/seed"
PINS = [
    "bin/amu-linux-x86_64",
    "bin/x86_64-linux/amu",
    "examples/foundation-starter/MACOS-ARM64.md",
    "examples/foundation-starter/candidate.json",
    "native-product.json",
    "seed/bootstrap/aarch64-linux-static-root.elf",
    "seed/bootstrap/aarch64-linux-static-root.json",
    "seed/bootstrap/aarch64-macos/amu-cli.macho",
    "seed/bootstrap/aarch64-macos/amu-full-root.macho",
    "seed/bootstrap/aarch64-macos/cli.json",
    "seed/bootstrap/aarch64-macos/root.json",
]


def run(*args):
    print("+", " ".join(str(a) for a in args), flush=True)
    subprocess.run([str(a) for a in args], cwd=ROOT, check=True)


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True,
                          stdout=subprocess.PIPE).stdout.decode()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pin(path):
    return {"bytes": path.stat().st_size, "sha256": sha(path)}


def take_pins(ref):
    for path in PINS:
        git("checkout", ref, "--", path)
    left = git("diff", "--name-only", "--diff-filter=U").split()
    if left:
        sys.exit("unresolved non-pin conflicts: " + " ".join(left))


def repin_cli(out):
    build = json.loads((out / "cli/cli-build.json").read_text())
    cli_path = ROOT / "seed/bootstrap/aarch64-macos/cli.json"
    cli = json.loads(cli_path.read_text())
    root = json.loads((ROOT / "seed/bootstrap/aarch64-macos/root.json").read_text())
    if build["sources"] != cli["sources"]:
        sys.exit("CLI source list changed; update cli.json sources first")
    old = cli["image"]["sha256"]
    image = ROOT / cli["image"]["path"]
    shutil.copyfile(out / "cli/amu-cli.macho", image)
    image.chmod(0o755)
    cli["image"].update(pin(image))
    cli["unsigned"] = pin(out / "cli/amu-cli-unsigned.macho")
    cli["compiler"], cli["packager"], cli["unity"] = root["compiler"], root["packager"], build["unity"]
    cli_path.write_text(json.dumps(cli, indent=2) + "\n")
    md = ROOT / "examples/foundation-starter/MACOS-ARM64.md"
    text = md.read_text()
    if old not in text:
        sys.exit("MACOS-ARM64.md does not name the previous CLI digest")
    md.write_text(text.replace(old, cli["image"]["sha256"]))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--take-pins-from", metavar="REF",
                   help="first restore every pin file from REF (e.g. FETCH_HEAD after a merge)")
    p.add_argument("--work", type=Path, help="build directory (default: a new temporary one)")
    args = p.parse_args()
    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        sys.exit("derived pins are produced on Mac arm64")
    if args.take_pins_from:
        take_pins(args.take_pins_from)
    out = args.work or Path(tempfile.mkdtemp(prefix="amu-repin-"))
    compiler = ROOT / "seed/bootstrap/aarch64-macos/amu-full-root.macho"
    packager = ROOT / "seed/bootstrap/aarch64-macos/kotoba-packager-root.macho"
    # Phase source: the pinned root compiles the new sources.
    run(sys.executable, SEED / "check-aiueos-user-macos-native.py", "--compiler-image", compiler,
        "--compiler-sha256", sha(compiler), "--packager-image", packager,
        "--packager-sha256", sha(packager), "--output", out / "mac-root-src")
    run(sys.executable, SEED / "write-bootstrap-descriptors.py", "--mac-build", out / "mac-root-src",
        "--phase", "source", "--install", "--write")
    # Phase final: the new root reproduces itself and the Linux candidates.
    run(sys.executable, SEED / "check-aiueos-user-macos-native.py", "--output", out / "mac-root")
    run(sys.executable, SEED / "check-macos-cross-linux-candidates.py", "--mac-build", out / "mac-root",
        "--output", out / "mac-cross", "--produce-candidates")
    run(sys.executable, SEED / "write-bootstrap-descriptors.py", "--mac-build", out / "mac-root",
        "--cross-build", out / "mac-cross", "--phase", "final", "--install", "--write")
    run(sys.executable, SEED / "build-macos-cli.py", "--output", out / "cli")
    repin_cli(out)
    run(sys.executable, SEED / "check-public-macos-product.py", "--output", out / "public")
    run(sys.executable, SEED / "write-bootstrap-descriptors.py", "--mac-build", out / "mac-root",
        "--cross-build", out / "mac-cross", "--phase", "final", "--check")
    git("add", "--", *PINS)
    print("REPINNED", out)


if __name__ == "__main__":
    main()
