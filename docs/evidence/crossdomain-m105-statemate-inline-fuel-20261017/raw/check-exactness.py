#!/usr/bin/env python3
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "bench/embench/reproduce-20261015/tools"))
import repro_lib as r

round_data = r.load_round()
workload = r.round_workloads(round_data)["statemate"]
expected = next(
    row for row in r.load(round_data["expectedAccounting"])
    if row["workload"] == "statemate"
)
results = {}
for tag in ("base", "candidate"):
    timer = OUT / "artifacts" / tag / "timer"
    run = r.run_timer(timer, workload["n"], r.caps_for("statemate"))
    exact = r.exact(run, expected)
    results[tag] = {"exact": exact, "run": run}
    print(tag, "exact", exact, "elapsedNs", run.get("elapsedNs"), flush=True)

report = {
    "kind": "statemate-registered-exactness-replay",
    "n": workload["n"],
    "results": results,
    "status": "PASS" if all(row["exact"] for row in results.values()) else "FAIL",
}
(OUT / "exactness-replay-report.json").write_text(json.dumps(report, indent=2) + "\n")
if report["status"] != "PASS":
    raise SystemExit(report["status"])
