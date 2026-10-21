#!/usr/bin/env python3
import json
import os
import statistics
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
timers = {
    tag: OUT / "artifacts" / tag / "timer"
    for tag in ("base", "candidate")
}
rows = []
for pair in range(10):
    for order, tag in enumerate(("base", "candidate", "candidate", "base"), 1):
        load = os.getloadavg()
        run = r.run_timer(timers[tag], workload["n"], r.caps_for("statemate"))
        exact = r.exact(run, expected)
        row = {
            "pair": pair + 1,
            "order": order,
            "tag": tag,
            "exact": exact,
            "elapsedNs": run.get("elapsedNs"),
            "loadAvgBefore": load,
        }
        if run.get("sample"):
            row["benchmarkFuel"] = run["sample"].get("benchmarkFuel")
            row["verifyFuel"] = run["sample"].get("verifyFuel")
        rows.append(row)
        print(json.dumps(row, separators=(",", ":")), flush=True)
        if not exact:
            raise SystemExit("exactness failed; report not promoted")

ratios = []
for pair in range(1, 11):
    base = [row["elapsedNs"] for row in rows if row["pair"] == pair and row["tag"] == "base"]
    candidate = [
        row["elapsedNs"] for row in rows
        if row["pair"] == pair and row["tag"] == "candidate"
    ]
    ratios.append(statistics.median(candidate) / statistics.median(base))
report = {
    "schema": "statemate-inline-fuel-abba-v1",
    "pairs": 10,
    "n": workload["n"],
    "hostLoad1Min": min(row["loadAvgBefore"][0] for row in rows),
    "hostLoad1Max": max(row["loadAvgBefore"][0] for row in rows),
    "candidateOverBaseRatios": ratios,
    "medianRatio": statistics.median(ratios),
    "baseMedianNs": statistics.median(
        row["elapsedNs"] for row in rows if row["tag"] == "base"
    ),
    "candidateMedianNs": statistics.median(
        row["elapsedNs"] for row in rows if row["tag"] == "candidate"
    ),
    "allExact": all(row["exact"] for row in rows),
    "rows": rows,
}
(OUT / "replay-abba-report.json").write_text(json.dumps(report, indent=2) + "\n")
