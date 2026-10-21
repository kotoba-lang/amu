#!/usr/bin/env python3
"""Wrap the width-two payload in the unchanged KSEED export table and run official xgboost exactness."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PKG = ROOT / "bench/embench/reproduce-20261015"
BASE_IMAGE = "1c4aab16450da5b1deef581688d13b1995b87fa0238789cff8563ddc941a400d"
PATCHED_IMAGE = "15496f2a07e7e37e3c694a423acb08ad7527b30b2f320c5190a40aedab94cd8b"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-kseed", type=Path, required=True)
    ap.add_argument("--patched-image", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit("output must be a new directory")
    raw = a.base_kseed.read_bytes()
    head, base = raw.split(b"\n\n", 1)
    patched = a.patched_image.read_bytes()
    if sha(base) != BASE_IMAGE or sha(patched) != PATCHED_IMAGE:
        raise SystemExit("base or patched image pin mismatch")
    if len(base) != len(patched):
        raise SystemExit("patched payload size differs from current width-four image")
    a.out.mkdir(parents=True)
    images = a.out / "images"
    images.mkdir()
    kseed = images / "official-xgboost.kseed"
    kseed.write_bytes(head + b"\n\n" + patched)
    cmd = [sys.executable, str(PKG / "c_exactness.py"), "--out", str(a.out / "exactness"),
           "--images", str(images), "--only", "xgboost"]
    q = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    (a.out / "exactness.stdout").write_text(q.stdout)
    (a.out / "exactness.stderr").write_text(q.stderr)
    report_path = a.out / "exactness/report.json"
    exactness = json.loads(report_path.read_text()) if report_path.is_file() else None
    report = {
        "status": "PASS_WIDTH2_XGBOOST_EXACTNESS" if q.returncode == 0 else "FAIL_WIDTH2_XGBOOST_EXACTNESS",
        "baseKseedSHA256": sha(raw),
        "baseImageSHA256": sha(base),
        "patchedImageSHA256": sha(patched),
        "exportTablePreserved": True,
        "exactness": exactness,
        "command": cmd,
        "exit": q.returncode,
    }
    (a.out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    if q.returncode:
        raise SystemExit(q.returncode)


if __name__ == "__main__":
    main()
