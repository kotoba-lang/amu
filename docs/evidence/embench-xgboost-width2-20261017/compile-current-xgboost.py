#!/usr/bin/env python3
"""Reproduce the current M105 xgboost image from its pinned selfhost fixed point."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "bench/embench/reproduce-20261015/tools"))
import repro_lib as R

SOURCE = ROOT / "bench/embench/reproduce-20261015/ports/official-xgboost.kotoba"
EXPECTED_SOURCE = "78c33ca4cb05425ad5a6b6f4de0725dedb07a05ef772b9f370768d0b1d23acdf"
EXPECTED_IMAGE = "1c4aab16450da5b1deef581688d13b1995b87fa0238789cff8563ddc941a400d"
EXPECTED_COMPILER = "b10e381344a1f5a8b82cac981c0011bd20ecbcc4b48dd5f5dce97364c74e8a00"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--loader", type=Path, required=True)
    ap.add_argument("--compiler", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    R.require_macos_arm64()
    if sha(SOURCE) != EXPECTED_SOURCE:
        raise SystemExit("xgboost source pin mismatch")
    if sha(a.compiler) != EXPECTED_COMPILER:
        raise SystemExit("selfhost compiler fixed-point pin mismatch")
    if not a.loader.is_file():
        raise SystemExit("trusted C loader is missing")
    if a.out.exists():
        raise SystemExit("output must be a new directory")
    a.out.mkdir(parents=True)
    result = R.compile_port(a.loader, a.compiler, SOURCE.read_bytes(), a.out, "official-xgboost")
    if result["native"]["sha256"] != EXPECTED_IMAGE:
        raise SystemExit("regenerated width-four image does not match its current M105 pin")
    report = {
        "status": "PASS_CURRENT_M105_XGBOOST_IMAGE_REPRODUCED",
        "source": {"path": str(SOURCE), "bytes": SOURCE.stat().st_size, "sha256": EXPECTED_SOURCE},
        "compiler": {"path": str(a.compiler), "sha256": sha(a.compiler)},
        "loader": {"path": str(a.loader), "sha256": sha(a.loader)},
        "compiled": result,
        "JVMNodeOrGraalFallback": False,
    }
    (a.out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
