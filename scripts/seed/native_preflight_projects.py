#!/usr/bin/env python3
"""Stage the ordered local-project -> FS35 candidate preflight.

No native verdict or source semantics are implemented here. The existing
observers retain their exact native compiler, fixtures, refusals and flags.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main(compiler, temporary):
    subprocess.run([sys.executable, str(ROOT / "scripts/seed/check-x86-project-native.py"),
                    "--compiler", str(compiler),
                    "--output", str(temporary / "local-native-project")], check=True)
    image = json.loads((ROOT / "native-product.json").read_text())["image"]["sha256"]
    subprocess.run([sys.executable, str(ROOT / "scripts/seed/check-x86-project-fs-native.py"),
                    "--compiler", str(compiler), "--compiler-sha256", image,
                    "--runner", str(temporary / "local-native-project/runner.elf"),
                    "--output", str(temporary / "project-fs-candidate"), "--derive"], check=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--compiler", type=Path, required=True)
    p.add_argument("--temporary", type=Path, required=True)
    a = p.parse_args()
    main(a.compiler.resolve(), a.temporary.resolve())
