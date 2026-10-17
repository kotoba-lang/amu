#!/usr/bin/env python3
"""Run the pinned M105 xgboost exactness check with the experimental payload."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PKG = ROOT / "bench/embench/reproduce-20261015"
BASE_KSEED_SHA256 = "34086740aa13854f387d49ea43317fd615415e5a9bc85d6eaf437736fc719433"
BASE_IMAGE_SHA256 = "1eac8f0f999f632bd2e33d5f7632674606ec38761976c83582f15288ca81ad65"
PATCHED_IMAGE_SHA256 = "05cac8ddd99914bb5a20cedea5f158bb74749faa7290775bf6b7de3c8919c15e"


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
    patched = a.patched_image.read_bytes()
    if sha(raw) != BASE_KSEED_SHA256:
        raise SystemExit("base KSEED pin mismatch")
    head, base = raw.split(b"\n\n", 1)
    if sha(base) != BASE_IMAGE_SHA256 or sha(patched) != PATCHED_IMAGE_SHA256:
        raise SystemExit("base or candidate image pin mismatch")
    if len(base) != len(patched):
        raise SystemExit("candidate payload size differs from the base image")
    a.out.mkdir(parents=True)
    images = a.out / "images"
    images.mkdir()
    (images / "official-xgboost.kseed").write_bytes(head + b"\n\n" + patched)
    cmd = [sys.executable, str(PKG / "c_exactness.py"), "--out", str(a.out / "exactness"),
           "--images", str(images), "--only", "xgboost"]
    run = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    (a.out / "exactness.stdout").write_text(run.stdout)
    (a.out / "exactness.stderr").write_text(run.stderr)
    report_path = a.out / "exactness/report.json"
    exactness = json.loads(report_path.read_text()) if report_path.is_file() else None
    report = {
        "status": "PASS_LANE_SKIP_XGBOOST_EXACTNESS" if run.returncode == 0 else "FAIL_LANE_SKIP_XGBOOST_EXACTNESS",
        "baseKseedSHA256": sha(raw),
        "baseImageSHA256": sha(base),
        "patchedImageSHA256": sha(patched),
        "exportTablePreserved": True,
        "exactness": exactness,
        "command": cmd,
        "exit": run.returncode,
    }
    (a.out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    if run.returncode:
        raise SystemExit(run.returncode)


if __name__ == "__main__":
    main()
