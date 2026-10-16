#!/usr/bin/env python3
"""Independently verify the archived full-19 M104 follow-up run."""
import json
import math
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parents[2]
round_config = json.loads((PKG / "rounds/sa-m104-20261015.json").read_text())
workloads_raw = json.loads((PKG / round_config["workloads"]).read_text())
workloads = workloads_raw if isinstance(workloads_raw, dict) else {x["workload"]: x for x in workloads_raw}
expected_raw = json.loads((PKG / round_config["expectedAccounting"]).read_text())
expected = {x["workload"]: x for x in expected_raw}
report = json.loads((HERE / "report.json").read_text())
errors = []
ratios = {}
CPU_ONLY_REASONS = {"quiet-admission-timeout", "raw-post-cpu", "background-cpu"}

def check(condition, message):
    if not condition:
        errors.append(message)

names = report.get("workloads", [])
check(len(names) == 19, "report is not full-19")
check(set(names) == set(workloads), "round workload set differs")
check(report.get("round") == round_config["round"], "round id differs")
check("UPSTREAM PASS" in (HERE / "upstream-verification.txt").read_text(), "upstream verification missing")

for arm in ("kotoba", "c"):
    rawdir = HERE / arm / "measured/raw"
    accepted = 0
    for workload in names:
        raw = json.loads((rawdir / f"{workload}.json").read_text())
        selected = raw.get("selectedAttempt")
        check(raw.get("complete") is True, f"{arm}/{workload}: incomplete")
        first_accepted = next((row.get("attempt") for row in raw.get("samples", []) if row.get("accepted")), None)
        check(selected == first_accepted, f"{arm}/{workload}: selection is not the first qualified attempt")
        if selected is None:
            continue
        row = raw["samples"][selected]
        for previous in raw["samples"]:
            if previous.get("attempt", selected) < selected:
                check(previous.get("accepted") is not True, f"{arm}/{workload}: earlier attempt was accepted")
                check(previous.get("retryEligible") is True and set(previous.get("reasons", [])) <= CPU_ONLY_REASONS,
                      f"{arm}/{workload}: retry followed a non-CPU failure")
        check(row.get("returncode") == 0, f"{arm}/{workload}: runner exit")
        check(row.get("accepted") is True and row.get("reasons") == [], f"{arm}/{workload}: rejected")
        check(row.get("elapsedNs", 0) >= 500_000_000, f"{arm}/{workload}: timed interval too short")
        cpu = row.get("cpuActivity", {})
        check(cpu.get("idlePercent", 0) >= 70, f"{arm}/{workload}: raw idle gate")
        check(cpu.get("estimatedBackgroundIdlePercent", 0) >= 70, f"{arm}/{workload}: background-idle gate")
        quiet_path = rawdir / f"{workload}-quiet-{selected}.json"
        quiet = json.loads(quiet_path.read_text())
        check(quiet.get("ready") is True and bool(quiet.get("probes")), f"{arm}/{workload}: quiet admission")
        if quiet.get("probes"):
            check(quiet["probes"][-1]["cpuActivity"].get("idlePercent", 0) >= 70,
                  f"{arm}/{workload}: admission idle below threshold")
        if arm == "kotoba":
            sample = row.get("sample") or {}
            check({k: v for k, v in sample.items() if k != "elapsedNs"} == expected[workload]["expectedSample"],
                  f"kotoba/{workload}: expected sample differs")
            check(row.get("stderr") == expected[workload]["expectedStderr"],
                  f"kotoba/{workload}: expected stderr differs")
            fuel = re.search(r":status :ok :result 1 .*:fuel \{:initial (\d+) :remaining (\d+)\}",
                             row.get("stdout", ""))
            check(bool(fuel), f"kotoba/{workload}: fuel receipt missing")
            if fuel:
                check(int(fuel[1]) == 34359738368, f"kotoba/{workload}: initial fuel differs")
                check(int(fuel[1]) - int(fuel[2]) == sample.get("benchmarkFuel", 0) + sample.get("verifyFuel", 0),
                      f"kotoba/{workload}: fuel accounting differs")
        else:
            output = re.fullmatch(r"EMBENCH_NS=(\d+)\n", row.get("stdout", ""))
            check(bool(output), f"c/{workload}: EMBENCH_NS output missing")
            if output:
                check(int(output[1]) == row["elapsedNs"], f"c/{workload}: elapsed output differs")
            check(row.get("stderr") == "", f"c/{workload}: unexpected stderr")
        accepted += int(row.get("accepted") is True)
    check(accepted == 19, f"{arm}: accepted {accepted}/19")
    check(report.get(arm, {}).get("driverExit") == 0, f"{arm}: upstream driver exit")

for workload in names:
    k = json.loads((HERE / "kotoba/measured/raw" / f"{workload}.json").read_text())
    c = json.loads((HERE / "c/measured/raw" / f"{workload}.json").read_text())
    k_ns = k["samples"][k["selectedAttempt"]]["elapsedNs"]
    c_ns = c["samples"][c["selectedAttempt"]]["elapsedNs"]
    multiplier = workloads[workload]["multiplier"]
    ratios[workload] = (4 / multiplier) * k_ns / c_ns
    check(math.isclose(ratios[workload], report.get("ratios", {}).get(workload, float("nan")),
                       rel_tol=1e-15, abs_tol=1e-15), f"{workload}: reported ratio differs")

gm = math.exp(sum(math.log(value) for value in ratios.values()) / 19) if len(ratios) == 19 else float("nan")
check(len(report.get("ratios", {})) == 19, "report ratio count differs")
check(report.get("acceptedKotoba") == 19 and report.get("acceptedC") == 19, "report accepted counts differ")
check(math.isclose(gm, report.get("geometricMean", float("nan")), rel_tol=1e-15, abs_tol=1e-15),
      "reported geometric mean differs")

if errors:
    raise SystemExit("FAIL\n" + "\n".join(errors))
print("PASS: 19/19 Kotoba and 19/19 C; exact Kotoba outputs; CPU gates; ratios; full-19 GM %.16f" % gm)
