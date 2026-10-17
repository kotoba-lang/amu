#!/usr/bin/env python3
"""Exploratory same-host ABBA timing for pinned width-four and exact lane-skip xgboost images."""
import argparse
import json
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

BASE_IMAGE = "1eac8f0f999f632bd2e33d5f7632674606ec38761976c83582f15288ca81ad65"
LANE_SKIP_IMAGE = "05cac8ddd99914bb5a20cedea5f158bb74749faa7290775bf6b7de3c8919c15e"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-kseed", type=Path, required=True)
    ap.add_argument("--lane-skip-image", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--pairs", type=int, default=5)
    a = ap.parse_args()
    R.require_macos_arm64()
    if a.pairs < 1:
        raise SystemExit("pairs must be positive")
    if a.out.exists():
        raise SystemExit("output must be a new directory")
    raw = a.base_kseed.read_bytes()
    _, base = raw.split(b"\n\n", 1)
    exports, _ = R.kseed_parts(raw)
    candidate = a.lane_skip_image.read_bytes()
    if R.sha(base) != BASE_IMAGE or R.sha(candidate) != LANE_SKIP_IMAGE:
        raise SystemExit("width-four or lane-skip payload pin mismatch")
    if len(base) != len(candidate):
        raise SystemExit("image lengths differ")
    rnd = R.load_round()
    workload = R.round_workloads(rnd)["xgboost"]
    expected_rows = json.loads(R.round_path(rnd, "expectedAccounting").read_text())
    expected = next(row for row in expected_rows if row["workload"] == "xgboost")
    a.out.mkdir(parents=True)
    timer_base = R.build_timer(a.out / "timer-width4", PKG / "harness", base, exports, workload)
    timer_candidate = R.build_timer(a.out / "timer-lane-skip", PKG / "harness", candidate, exports, workload)
    caps = R.caps_for("xgboost", workload["extraCaps"])
    report = {
        "schema": "amu.embench.xgboost-lane-skip-abba/v1",
        "status": "RUNNING",
        "round": rnd["round"],
        "host": {"platform": os.uname().sysname, "architecture": os.uname().machine,
                 "logicalCPUCount": os.cpu_count()},
        "hostModel": "Apple M1 Max (user-reported)",
        "qualification": "unqualified exploratory run; user authorized comparison under current load",
        "protocol": "five ABBA blocks; same pinned timer, one warmup, exact n and caps; exact result/fuel/arena checked each time; no CPU quiet gate",
        "n": workload["n"],
        "caps": caps,
        "images": {"width4SHA256": R.sha(base), "laneSkipSHA256": R.sha(candidate)},
        "runs": [],
        "pairs": [],
        "performanceClaim": False,
    }
    out_report = a.out / "report.json"
    out_report.write_text(json.dumps(report, indent=2) + "\n")
    timers = {"width4": timer_base, "laneSkip": timer_candidate}
    for pair in range(a.pairs):
        block = []
        for arm in ("width4", "laneSkip", "laneSkip", "width4"):
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
        base_times = [r["elapsedNs"] for r in block if r["arm"] == "width4"]
        candidate_times = [r["elapsedNs"] for r in block if r["arm"] == "laneSkip"]
        ratio = statistics.mean(candidate_times) / statistics.mean(base_times)
        report["pairs"].append({"pair": pair + 1, "width4MeanNs": statistics.mean(base_times),
                                 "laneSkipMeanNs": statistics.mean(candidate_times), "laneSkipOverWidth4": ratio})
        out_report.write_text(json.dumps(report, indent=2) + "\n")
        print("PAIR", pair + 1, "lane-skip/width4", f"{ratio:.4f}", flush=True)
    ratios = [row["laneSkipOverWidth4"] for row in report["pairs"]]
    base_times = [row["elapsedNs"] for row in report["runs"] if row["arm"] == "width4"]
    candidate_times = [row["elapsedNs"] for row in report["runs"] if row["arm"] == "laneSkip"]
    report["summary"] = {
        "width4MedianNs": statistics.median(base_times),
        "laneSkipMedianNs": statistics.median(candidate_times),
        "medianPairedLaneSkipOverWidth4": statistics.median(ratios),
        "pairedRatios": ratios,
        "allRunsExact": all(row["exact"] for row in report["runs"]),
        "allRunsFuelConsistent": all(row["fuelConsistent"] for row in report["runs"]),
    }
    report["status"] = "PASS_EXPLORATORY_EXACT_ABBA"
    out_report.write_text(json.dumps(report, indent=2) + "\n")
    print("SUMMARY", json.dumps(report["summary"]))


if __name__ == "__main__":
    main()
