#!/usr/bin/env python3
"""Exploratory same-host ABBA timing for pinned width-four and exact width-two xgboost images."""
import argparse
import json
import math
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PKG = ROOT / "bench/embench/reproduce-20261015"
sys.path.insert(0, str(PKG / "tools"))
sys.path.insert(0, str(PKG / "harness"))
import repro_lib as R
from darwin_cpu_idle import snapshot, interval

BASE_IMAGE = "1c4aab16450da5b1deef581688d13b1995b87fa0238789cff8563ddc941a400d"
WIDTH2_IMAGE = "15496f2a07e7e37e3c694a423acb08ad7527b30b2f320c5190a40aedab94cd8b"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-kseed", type=Path, required=True)
    ap.add_argument("--width2-image", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--pairs", type=int, default=5)
    a = ap.parse_args()
    R.require_macos_arm64()
    if a.pairs < 1:
        raise SystemExit("pairs must be positive")
    if a.out.exists():
        raise SystemExit("output must be a new directory")
    raw = a.base_kseed.read_bytes()
    head, base = raw.split(b"\n\n", 1)
    exports, _ = R.kseed_parts(raw)
    candidate = a.width2_image.read_bytes()
    if R.sha(base) != BASE_IMAGE or R.sha(candidate) != WIDTH2_IMAGE:
        raise SystemExit("width-four or width-two payload pin mismatch")
    if len(base) != len(candidate):
        raise SystemExit("image lengths differ")
    rnd = R.load_round()
    workload = R.round_workloads(rnd)["xgboost"]
    expected_rows = json.loads(R.round_path(rnd, "expectedAccounting").read_text())
    expected = next(row for row in expected_rows if row["workload"] == "xgboost")
    a.out.mkdir(parents=True)
    timer4 = R.build_timer(a.out / "timer-width4", PKG / "harness", base, exports, workload)
    timer2 = R.build_timer(a.out / "timer-width2", PKG / "harness", candidate, exports, workload)
    caps = R.caps_for("xgboost", workload["extraCaps"])
    report = {
        "schema": "amu.embench.xgboost-width2-abba/v1",
        "status": "RUNNING",
        "round": rnd["round"],
        "host": {"platform": os.uname().sysname, "architecture": os.uname().machine,
                 "logicalCPUCount": os.cpu_count()},
        "hostModel": "Apple M1 Max (reported in the preceding qualification attempt)",
        "qualification": "unqualified exploratory run; user authorized comparison under current load",
        "protocol": "five ABBA blocks; every invocation uses the pinned c-exactness timer, one warmup, exact n and caps; exact result/fuel/arena checked each time; no CPU quiet gate",
        "n": workload["n"],
        "caps": caps,
        "images": {"width4SHA256": R.sha(base), "width2SHA256": R.sha(candidate)},
        "runs": [],
        "pairs": [],
        "performanceClaim": False,
    }
    out_report = a.out / "report.json"
    out_report.write_text(json.dumps(report, indent=2) + "\n")
    timers = {"width4": timer4, "width2": timer2}
    # Each block is A-B-B-A; the repeated order reduces sensitivity to monotonic drift.
    for pair in range(a.pairs):
        block = []
        for arm in ("width4", "width2", "width2", "width4"):
            load_before = os.getloadavg()
            cpu_before = snapshot()
            wall_before = time.monotonic_ns()
            result = R.run_timer(timers[arm], workload["n"], caps)
            wall_after = time.monotonic_ns()
            cpu_after = snapshot()
            load_after = os.getloadavg()
            row = {
                "pair": pair + 1,
                "arm": arm,
                "exact": R.exact(result, expected),
                "fuelConsistent": result["fuelConsistent"],
                "elapsedNs": result["elapsedNs"],
                "wallElapsedNs": wall_after - wall_before,
                "loadBefore": load_before,
                "loadAfter": load_after,
                "cpuActivity": interval(cpu_before, cpu_after),
                "sample": result["sample"],
                "stderr": result["stderr"],
                "returncode": result["returncode"],
            }
            block.append(row)
            report["runs"].append(row)
            out_report.write_text(json.dumps(report, indent=2) + "\n")
            if not row["exact"]:
                report["status"] = "FAIL_EXACTNESS_ABORTED"
                out_report.write_text(json.dumps(report, indent=2) + "\n")
                raise SystemExit("timing stopped: an arm did not match exact xgboost output/fuel/arena")
        a_times = [r["elapsedNs"] for r in block if r["arm"] == "width4"]
        b_times = [r["elapsedNs"] for r in block if r["arm"] == "width2"]
        ratio = statistics.mean(b_times) / statistics.mean(a_times)
        report["pairs"].append({"pair": pair + 1, "width4MeanNs": statistics.mean(a_times),
                                 "width2MeanNs": statistics.mean(b_times), "width2OverWidth4": ratio})
        out_report.write_text(json.dumps(report, indent=2) + "\n")
        print("PAIR", pair + 1, "width2/width4", f"{ratio:.4f}", flush=True)
    ratios = [row["width2OverWidth4"] for row in report["pairs"]]
    report["summary"] = {
        "width4MedianNs": statistics.median(row["elapsedNs"] for row in report["runs"] if row["arm"] == "width4"),
        "width2MedianNs": statistics.median(row["elapsedNs"] for row in report["runs"] if row["arm"] == "width2"),
        "medianPairedWidth2OverWidth4": statistics.median(ratios),
        "pairedRatios": ratios,
        "allRunsExact": all(row["exact"] for row in report["runs"]),
        "allRunsFuelConsistent": all(row["fuelConsistent"] for row in report["runs"]),
    }
    report["status"] = "PASS_EXPLORATORY_EXACT_ABBA"
    out_report.write_text(json.dumps(report, indent=2) + "\n")
    print("SUMMARY", json.dumps(report["summary"]))


if __name__ == "__main__":
    main()
