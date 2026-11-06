#!/usr/bin/env python3
"""Fail when a post-merge repin touched anything other than derived pins (ADR 0406, JUN-818).

Usage: repin_allowlist.py [--root DIR]   (reads `git status --porcelain` in DIR)
"""
import argparse
import re
import subprocess
import sys

EXACT = {
    "bin/amu-linux-x86_64", "bin/x86_64-linux/amu",
    "examples/foundation-starter/MACOS-ARM64.md", "examples/foundation-starter/candidate.json",
    "native-product.json", "seed/bootstrap/aarch64-linux-static-root.elf",
    "seed/bootstrap/aarch64-linux-static-root.json", "seed/bootstrap/aarch64-macos/amu-cli.macho",
    "seed/bootstrap/aarch64-macos/amu-full-root.macho", "seed/bootstrap/aarch64-macos/cli.json",
    "seed/bootstrap/aarch64-macos/root.json", "seed/bootstrap/aarch64-macos/kotoba-packager-root.macho",
    "seed/cdci/policy.json", "seed/cdci/controller.kotoba", "seed/cdci/kotoba-gate.kotoba",
    "seed/compiler-core.json", "seed/79-native-cdci.kotoba",
}
PATTERNS = (re.compile(r"^seed/adoption-[^/]+\.json$"),)
ROLE_LINE = re.compile(r'\(string=\? role "[a-z-]+"\) "[0-9a-f]{64}"')


def allowed(path):
    return path in EXACT or any(p.search(path) for p in PATTERNS)


def seed79_only_role_hashes(root):
    diff = subprocess.run(["git", "-C", root, "diff", "-U0", "--", "seed/79-native-cdci.kotoba"],
                          capture_output=True, text=True, check=True).stdout
    for line in diff.splitlines():
        if line[:1] in "+-" and not line.startswith(("+++", "---")) and not ROLE_LINE.search(line):
            return False
    return True


def check(paths, root="."):
    bad = [p for p in paths if not allowed(p)]
    if "seed/79-native-cdci.kotoba" in paths and not seed79_only_role_hashes(root):
        bad.append("seed/79-native-cdci.kotoba (non-hash line changed)")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    out = subprocess.run(["git", "-C", args.root, "status", "--porcelain", "-z"],
                         capture_output=True, text=True, check=True).stdout
    paths = [e[3:] for e in out.split("\0") if e]
    bad = check(paths, args.root)
    if bad:
        print("repin touched non-pin paths:", *bad, sep="\n  ")
        return 1
    print(f"repin allowlist ok ({len(paths)} paths)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
