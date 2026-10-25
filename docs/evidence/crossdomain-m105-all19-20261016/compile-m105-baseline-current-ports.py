#!/usr/bin/env python3
"""Compile the current 19 ports with the verified M105 baseline compiler."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PKG = REPO / "bench/embench/reproduce-20261015"
sys.path.insert(0, str(PKG / "tools"))
import repro_lib as R

BASELINE_COMPILER_SHA256 = "6b158aa8654706743462b8a730f189072ba05f364b00af28a3f6d23045add2eb"
BASELINE_COMPILER_SOURCE_COMMIT = "9892fc06a5f40cf392e02750f5d6a7fa0731a585"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--loader", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    R.require_macos_arm64()
    compiler = REPO / "seed/bootstrap/adopted-20261012.bin"
    if sha256(compiler) != BASELINE_COMPILER_SHA256:
        raise SystemExit("adopted image does not match the verified M105 baseline compiler")
    if not args.loader.is_file():
        raise SystemExit("trusted native loader is missing")

    rnd = R.load_round("rounds/sa-m104-20261015.json")
    workloads = R.round_workloads(rnd)
    out = R.fresh_dir(args.out)
    report = {
        "status": "RUNNING",
        "baselineCompilerSourceCommit": BASELINE_COMPILER_SOURCE_COMMIT,
        "baselineCompilerSha256": BASELINE_COMPILER_SHA256,
        "loaderSha256": sha256(args.loader),
        "round": rnd["round"],
        "portsSource": rnd["ports"],
        "started": time.time(),
        "images": {},
    }
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    for name in sorted(workloads):
        source = PKG / rnd["ports"] / f"official-{name}.kotoba"
        result = R.compile_port(args.loader, compiler, source.read_bytes(), out, f"official-{name}")
        report["images"][name] = {
            "sourceSha256": sha256(source),
            "kseed": result["kseed"],
            "native": result["native"],
            "exports": result["exports"],
        }
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(f"{name:15} {result['native']['sha256'][:16]}", flush=True)
    report["status"] = "PASS_COMPILED_19_WITH_VERIFIED_M105_BASELINE"
    report["ended"] = time.time()
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"])


if __name__ == "__main__":
    main()
