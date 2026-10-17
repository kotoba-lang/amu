#!/usr/bin/env python3
"""Exploratory same-host ABBA timing for the Sglib pointer-cache candidate."""
import hashlib
import json
import os
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path('worktrees/codex/amu-crossdomain-coscientist-20261016')
PKG = ROOT / "bench/embench/reproduce-20261015"
sys.path.insert(0, str(PKG / "tools"))
import repro_lib as R

CONTROL = ROOT / "workspaces/codex/amu-sglib-list-merge-pointer-cache-20261017/attempt-2/control-build/sglib-control/official-sglib-combined.kseed"
CANDIDATE = HERE / "all19-images/official-sglib-combined.kseed"
OUT = HERE / "timing-abba"
CONTROL_NATIVE_SHA256 = "5e0b9072eb8a404479d569c5986ba6f008bd6143b8815fb0ea2db3f2e91d0040"
BLOCKS = 10

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    R.require_macos_arm64()
    if OUT.exists():
        raise SystemExit("preserving existing timing output")
    control_exports, control_image = R.kseed_parts(CONTROL.read_bytes())
    candidate_exports, candidate_image = R.kseed_parts(CANDIDATE.read_bytes())
    if R.sha(control_image) != CONTROL_NATIVE_SHA256:
        raise SystemExit("control image is not the pinned M105 Sglib control")
    if set(control_exports) != set(candidate_exports):
        raise SystemExit("candidate export symbols differ from the control")
    if any(control_exports[sym][1] != candidate_exports[sym][1] for sym in control_exports):
        raise SystemExit("candidate export arity differs from the control")
    export_deltas = {candidate_exports[sym][0] - control_exports[sym][0] for sym in control_exports}
    if export_deltas != {8}:
        raise SystemExit(f"expected all exports to shift by the 8-byte kernel growth, got {sorted(export_deltas)}")
    rnd = R.load_round("rounds/sa-m104-20261015.json")
    w = R.round_workloads(rnd)["sglib-combined"]
    expected = {x["workload"]: x for x in json.loads(R.round_path(rnd, "expectedAccounting").read_text())}["sglib-combined"]
    OUT.mkdir(parents=True)
    control_timer = R.build_timer(OUT / "timer-control", R.PKG / "harness", control_image, control_exports, w)
    candidate_timer = R.build_timer(OUT / "timer-candidate", R.PKG / "harness", candidate_image, candidate_exports, w)
    timers = {"control": control_timer, "candidate": candidate_timer}
    report = {
        "status": "RUNNING",
        "qualification": "loaded-host exploratory only; not an official score",
        "round": rnd["round"],
        "n": w["n"],
        "controlKseedSHA256": sha(CONTROL),
        "controlImageSHA256": R.sha(control_image),
        "candidateKseedSHA256": sha(CANDIDATE),
        "candidateImageSHA256": R.sha(candidate_image),
        "candidateExportOffsetDeltaBytes": 8,
        "warmups": [],
        "blocks": [],
    }
    report_path = OUT / "report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    caps = R.caps_for("sglib-combined", w["extraCaps"])

    def run(label, timer, phase, block=None, slot=None):
        result = R.run_timer(timer, w["n"], caps)
        exact = R.exact(result, expected)
        row = {
            "arm": label,
            "phase": phase,
            "block": block,
            "slot": slot,
            "exact": exact,
            "elapsedNs": result["elapsedNs"],
            "loadAverage": os.getloadavg(),
            "benchmarkFuel": (result["sample"] or {}).get("benchmarkFuel"),
            "verifyFuel": (result["sample"] or {}).get("verifyFuel"),
        }
        if not exact or not result["sample"]:
            row["stderr"] = result["stderr"][-2000:]
            report.setdefault("invalidRuns", []).append(row)
            report["status"] = "FAIL_NONEXACT_RUN"
            report_path.write_text(json.dumps(report, indent=2) + "\n")
            raise SystemExit(f"non-exact {label} run in {phase}")
        return row

    for label in ("control", "candidate"):
        row = run(label, timers[label], "warmup")
        report["warmups"].append(row)
        report_path.write_text(json.dumps(report, indent=2) + "\n")

    orders = [("control", "candidate", "candidate", "control"),
              ("candidate", "control", "control", "candidate")]
    for block in range(BLOCKS):
        order = orders[block % len(orders)]
        rows = [run(label, timers[label], "measurement", block, slot) for slot, label in enumerate(order)]
        c = [r["elapsedNs"] for r in rows if r["arm"] == "control"]
        k = [r["elapsedNs"] for r in rows if r["arm"] == "candidate"]
        ratio = statistics.mean(k) / statistics.mean(c)
        report["blocks"].append({"order": order, "runs": rows, "candidateOverControl": ratio})
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        print(f"block {block + 1:02d} candidate/control={ratio:.5f} load1={rows[0]['loadAverage'][0]:.2f}", flush=True)

    ratios = [x["candidateOverControl"] for x in report["blocks"]]
    report["summary"] = {
        "medianCandidateOverControl": statistics.median(ratios),
        "candidateFasterBlocks": sum(x < 1 for x in ratios),
        "blocks": len(ratios),
        "timedAtUnix": time.time(),
    }
    report["status"] = "COMPLETE_EXPLORATORY_ABBA"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"], indent=2))

if __name__ == "__main__":
    main()
