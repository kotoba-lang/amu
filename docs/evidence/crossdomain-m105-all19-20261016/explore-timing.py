#!/usr/bin/env python3
"""Loaded-host diagnostic for selected M105 selfhost workload images.

This deliberately bypasses the official quiet-admission gate. It uses the
round's Kotoba native timer and C binaries from a recorded same-host -O2 build,
checks Kotoba result/fuel/arena data on every run, and must never be reported
as qualified timing or an Embench score.
"""
import argparse
import hashlib
import json
import os
import re
import resource
import statistics
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PKG = REPO / "bench/embench/reproduce-20261015"
sys.path.insert(0, str(PKG / "tools"))
sys.path.insert(0, str(PKG / "harness"))
import repro_lib as R
from darwin_cpu_idle import background_activity, interval, snapshot

DEFAULT_DOMAINS = ["xgboost", "picojpeg", "slre", "qrduino", "sglib-combined"]
ROUND = "rounds/sa-m104-20261015.json"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_kotoba(timer, name, workload, expected):
    load_before = os.getloadavg()[0]
    usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    before = snapshot()
    run = R.run_timer(timer, workload["n"], R.caps_for(name, workload["extraCaps"]))
    after = snapshot()
    usage_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu_ns = int((usage_after.ru_utime + usage_after.ru_stime - usage_before.ru_utime - usage_before.ru_stime) * 1e9)
    activity = interval(before, after)
    activity = background_activity(activity, cpu_ns, os.cpu_count())
    if not R.exact(run, expected):
        raise RuntimeError(f"{name} {run.get('stdout')} {run.get('stderr')}")
    return {
        "arm": "baseline" if "baseline" in str(timer) else "candidate",
        "elapsedNs": run["elapsedNs"],
        "resultFuelArenaExact": True,
        "sample": run["sample"],
        "host": {"load1Before": load_before, "load1After": os.getloadavg()[0],
                 "rawIdlePercent": activity["idlePercent"],
                 "estimatedBackgroundIdlePercent": activity["estimatedBackgroundIdlePercent"]},
    }


def run_c(binary):
    load_before = os.getloadavg()[0]
    usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    before = snapshot()
    proc = subprocess.run([str(binary)], capture_output=True, text=True, timeout=1805)
    after = snapshot()
    usage_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu_ns = int((usage_after.ru_utime + usage_after.ru_stime - usage_before.ru_utime - usage_before.ru_stime) * 1e9)
    activity = background_activity(interval(before, after), cpu_ns, os.cpu_count())
    values = re.findall(r"^EMBENCH_NS=(\d+)$", proc.stdout, re.MULTILINE)
    if proc.returncode != 0 or proc.stderr or len(values) != 1:
        raise RuntimeError(f"C run failed: rc={proc.returncode} stdout={proc.stdout!r} stderr={proc.stderr!r}")
    return {
        "arm": "c",
        "elapsedNs": int(values[0]),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "host": {"load1Before": load_before, "load1After": os.getloadavg()[0],
                 "rawIdlePercent": activity["idlePercent"],
                 "estimatedBackgroundIdlePercent": activity["estimatedBackgroundIdlePercent"]},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-images", type=Path,
                         help="directory of baseline official-<workload>.kseed images; default is the round's pinned images")
    parser.add_argument("--candidate-images", type=Path, required=True)
    parser.add_argument("--c-binaries", type=Path, required=True)
    parser.add_argument("--c-receipt", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--domains", default=",".join(DEFAULT_DOMAINS))
    parser.add_argument("--pairs", type=int, default=4)
    args = parser.parse_args()
    R.require_macos_arm64()
    names = args.domains.split(",")
    if not names or len(names) != len(set(names)) or args.pairs < 1:
        raise SystemExit("domains must be unique and pairs must be positive")
    rnd = R.load_round(ROUND)
    workloads = R.round_workloads(rnd)
    expected = {row["workload"]: row for row in R.load("round-sa-m104-20261015/records/round/expected-accounting-mw.json")}
    base_dir = args.baseline_images if args.baseline_images else PKG / rnd["images"]
    c_receipt = json.loads(args.c_receipt.read_text())
    if c_receipt.get("gsf") != 32768 or "Apple clang version 21.0.0" not in c_receipt.get("compiler", ""):
        raise SystemExit("C receipt is not the recorded M1 Apple clang 21 build")
    out = R.fresh_dir(args.out)
    report = {
        "status": "EXPLORATORY_LOADED_HOST_NOT_QUALIFIED",
        "round": rnd["round"],
        "host": {"platform": sys.platform, "architecture": os.uname().machine,
                 "model": "Apple M1 Max (user-reported)", "loadAverageBefore": os.getloadavg()},
        "protocol": "4 alternating baseline/C/candidate triplets per workload; one warmup per arm; official Kotoba timer; official C binary; no quiet admission",
        "baselineImages": "verified M105 baseline compiler built from the current port sources; see m105-baseline-build.json",
        "candidateImages": "current M105 G3 selfhost build; see images.json and compiler-chain.json",
        "quietGatePassed": False,
        "officialEmbenchScore": False,
        "cReceiptSha256": sha256(args.c_receipt),
        "domains": {},
    }
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")

    for name in names:
        if name not in workloads:
            raise SystemExit(f"unknown workload {name}")
        w = workloads[name]
        base_path = next((path for path in (base_dir / f"official-{name}.kseed", base_dir / f"{name}.kseed") if path.is_file()), None)
        candidate_path = next((path for path in (args.candidate_images / f"official-{name}.kseed", args.candidate_images / f"{name}.kseed") if path.is_file()), None)
        if base_path is None or candidate_path is None:
            raise SystemExit(f"missing image for {name}")
        c_binary = args.c_binaries / name / name
        c_row = next((row for row in c_receipt["rows"] if row["workload"] == name), None)
        if not c_row or not c_binary.is_file() or sha256(c_binary) != c_row["sha256"]:
            raise SystemExit(f"C binary receipt mismatch for {name}")
        if "-O2" not in c_row.get("argv", []):
            raise SystemExit(f"C binary is not recorded as -O2 for {name}")

        timers = {}
        image_hashes = {}
        for arm, image_path in (("baseline", base_path), ("candidate", candidate_path)):
            exports, native = R.kseed_parts(image_path.read_bytes())
            image_hashes[arm] = R.sha(native)
            timers[arm] = R.build_timer(out / f"{name}-{arm}-timer", PKG / "harness", native, exports, w)

        # One untimed warm-up per arm; validate the same semantic record as a measured run.
        for arm in ("baseline", "candidate"):
            run_kotoba(timers[arm], name, w, expected[name])
        run_c(c_binary)

        blocks = []
        for pair in range(args.pairs):
            order = ("baseline", "c", "candidate") if pair % 2 == 0 else ("candidate", "c", "baseline")
            rows = []
            for arm in order:
                if arm == "c":
                    row = run_c(c_binary)
                else:
                    row = run_kotoba(timers[arm], name, w, expected[name])
                row["arm"] = arm
                row["orderIndex"] = len(rows)
                rows.append(row)
            times = {row["arm"]: row["elapsedNs"] for row in rows}
            factor = 4 / w["multiplier"]
            blocks.append({"pair": pair + 1, "order": list(order), "samples": rows,
                           "baselineOverC": factor * times["baseline"] / times["c"],
                           "candidateOverC": factor * times["candidate"] / times["c"],
                           "candidateOverBaseline": times["candidate"] / times["baseline"]})
            section = report["domains"].setdefault(name, {"n": w["n"], "multiplier": w["multiplier"],
                "baselineImageSha256": image_hashes["baseline"], "candidateImageSha256": image_hashes["candidate"],
                "cBinarySha256": c_row["sha256"], "pairs": []})
            section["pairs"].append(blocks[-1])
            (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
            print(name, pair + 1, "baseline/C=%.4f candidate/C=%.4f candidate/baseline=%.4f" % (
                blocks[-1]["baselineOverC"], blocks[-1]["candidateOverC"], blocks[-1]["candidateOverBaseline"]), flush=True)

        report["domains"][name]["summary"] = {
            "baselineMedianNs": statistics.median([p["samples"][0 if p["order"][0] == "baseline" else 2]["elapsedNs"] for p in blocks]),
            "candidateMedianNs": statistics.median([p["samples"][2 if p["order"][2] == "candidate" else 0]["elapsedNs"] for p in blocks]),
            "cMedianNs": statistics.median([p["samples"][1]["elapsedNs"] for p in blocks]),
            "medianCandidateOverBaseline": statistics.median([p["candidateOverBaseline"] for p in blocks]),
            "medianCandidateOverC": statistics.median([p["candidateOverC"] for p in blocks]),
        }
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")

    report["host"]["loadAverageAfter"] = os.getloadavg()
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("EXPLORATORY ONLY; quiet gate not passed; no score")


if __name__ == "__main__":
    main()
