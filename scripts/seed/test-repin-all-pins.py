#!/usr/bin/env python3
"""Negative controls for repin-all-pins.py --check (JUN-759). Mac arm64.

usage: test-repin-all-pins.py [--mac-build DIR]
DIR is a mac-root fixed-point build of the current tree (default: built here).
Each control runs the checker on a scratch copy of the pin inputs:
  current tree                     -> exit 0
  stale policy amuSelfhostGate pin  -> exit 10
  stale controller pin row          -> exit 10
  stale kotoba-gate image row       -> exit 10
  stale seed/79 role hash           -> exit 10
  core module changed (adoption)    -> exit 11
A control that does not fail as required fails this test.
"""
import argparse, json, re, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "scripts/seed/repin-all-pins.py"


def copy_tree(dst):
    shutil.copytree(ROOT / "seed", dst / "seed", symlinks=True)
    (dst / "scripts/seed").mkdir(parents=True)
    shutil.copy2(ROOT / "scripts/seed/check-aiueos-user-macos-native.py", dst / "scripts/seed/")


def sub_once(path, pattern, repl):
    t = path.read_text()
    n, c = re.subn(pattern, repl, t, count=1)
    assert c == 1, (path, pattern)
    path.write_text(n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mac-build", type=Path)
    a = ap.parse_args()
    work = Path(tempfile.mkdtemp(prefix="test-repin-all-"))
    mac = a.mac_build
    if mac is None:
        subprocess.run([sys.executable, str(ROOT / "scripts/seed/check-aiueos-user-macos-native.py"), "--output", str(work / "mac-root")], check=True, cwd=ROOT)
        mac = work / "mac-root"
    mac = mac.resolve()

    def control(name, mutate, want):
        scratch = work / name
        scratch.mkdir()
        copy_tree(scratch)
        mutate(scratch)
        r = subprocess.run([sys.executable, str(TOOL), "--root", str(scratch), "--check", "--mac-build", str(mac)], capture_output=True, text=True)
        ok = r.returncode == want
        print(("PASS " if ok else "FAIL ") + name, "exit", r.returncode, "want", want)
        if not ok:
            print(r.stdout[-600:], r.stderr[-600:])
        return ok

    def flip_policy(s):
        p = s / "seed/cdci/policy.json"
        d = json.loads(p.read_text())
        d["amuSelfhostGateSHA256"] = "0" * 64
        p.write_text(json.dumps(d, indent=2) + "\n")

    results = [
        control("current", lambda s: None, 0),
        control("stale-policy", flip_policy, 10),
        control("stale-controller-row", lambda s: sub_once(s / "seed/cdci/controller.kotoba", r"(h2_0 \(kc-word [^\n]*?)0x[0-9a-f]+", r"\g<1>0x3030303030303030"), 10),
        control("stale-gate-row", lambda s: sub_once(s / "seed/cdci/kotoba-gate.kotoba", r"(h1_0 \(kc-word [^\n]*?)0x[0-9a-f]+", r"\g<1>0x3030303030303030"), 10),
        control("stale-role-hash", lambda s: sub_once(s / "seed/79-native-cdci.kotoba", r'(string=\? role "controller"\) ")[0-9a-f]{64}', r"\g<1>" + "0" * 64), 10),
        control("core-drift", lambda s: (s / "seed/10-lex.kotoba").write_text((s / "seed/10-lex.kotoba").read_text() + "\n;; drift\n"), 11),
    ]
    shutil.rmtree(work, ignore_errors=True)
    if all(results):
        print("PASS_REPIN_ALL_PINS_NEGATIVE_CONTROLS")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
