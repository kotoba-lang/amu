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

def raw_idle(cpu, label):
    before = cpu.get("before", {})
    after = cpu.get("after", {})
    before_ticks = before.get("ticks", [])
    after_ticks = after.get("ticks", [])
    valid = (len(before_ticks) == 4 and len(after_ticks) == 4 and
             all(type(x) is int and 0 <= x <= 0xffffffff for x in before_ticks + after_ticks))
    check(valid, f"{label}: raw CPU ticks missing or invalid")
    if not valid:
        return None
    delta = [(b - a) & 0xffffffff for a, b in zip(before_ticks, after_ticks)]
    check(cpu.get("deltaTicks") == delta and sum(delta) > 0, f"{label}: tick deltas differ")
    processors = before.get("processors")
    check(type(processors) is int and processors > 0 and after.get("processors") == processors,
          f"{label}: processor count is missing or changed")
    idle = 100 * delta[2] / sum(delta) if sum(delta) else 0.0
    check(math.isclose(idle, cpu.get("idlePercent", float("nan")), rel_tol=0, abs_tol=1e-9),
          f"{label}: idle percent differs from raw tick counters")
    envelope = after.get("monotonicNs", 0) - before.get("monotonicNs", 0)
    check(envelope == cpu.get("envelopeNs") and envelope > 0, f"{label}: monotonic envelope differs")
    return idle

def verify_activity(cpu, label):
    idle = raw_idle(cpu, label)
    check(idle is not None and idle >= 70, f"{label}: raw idle gate below 70%")
    envelope = cpu.get("envelopeNs", 0)
    children = cpu.get("childCpuNs", -1)
    logical = cpu.get("before", {}).get("processors", 0)
    check(cpu.get("logicalCpuCount") == logical, f"{label}: logical CPU count differs from raw snapshots")
    if isinstance(envelope, int) and envelope > 0 and isinstance(children, int) and children >= 0 and isinstance(logical, int) and logical > 0:
        background = min(100, idle + 100 * children / (envelope * logical)) if idle is not None else float("nan")
        check(math.isclose(background, cpu.get("estimatedBackgroundIdlePercent", float("nan")),
                           rel_tol=0, abs_tol=1e-9), f"{label}: estimated background idle differs from raw counters")
        check(background >= 70, f"{label}: estimated background-idle gate below 70%")
    else:
        check(False, f"{label}: background-idle inputs missing or invalid")

def verify_quiet(quiet, label):
    probes = quiet.get("probes", [])
    required = quiet.get("requiredConsecutive", 0)
    minimum = quiet.get("rawIdleMinimumPercent", float("nan"))
    check(bool(probes) and type(required) is int and required == 1 and minimum == 70,
          f"{label}: quiet probes or protocol thresholds differ")
    streak = 0
    ready = False
    for i, probe in enumerate(probes):
        idle = raw_idle(probe.get("cpuActivity", {}), f"{label}/probe-{i}")
        is_quiet = idle is not None and idle >= minimum
        streak = streak + 1 if is_quiet else 0
        check(probe.get("quiet") is is_quiet, f"{label}/probe-{i}: quiet decision differs from raw counters")
        check(probe.get("consecutive") == streak, f"{label}/probe-{i}: quiet streak differs")
        ready = ready or streak >= required
    check(quiet.get("ready") is ready, f"{label}: admission result differs from raw probe counters")
    return ready

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
        verify_activity(cpu, f"{arm}/{workload}/selected")
        quiet_path = rawdir / f"{workload}-quiet-{selected}.json"
        quiet = json.loads(quiet_path.read_text())
        check(quiet.get("workload") == workload and quiet.get("attempt") == selected,
              f"{arm}/{workload}: quiet record workload or attempt differs")
        check(verify_quiet(quiet, f"{arm}/{workload}") is True, f"{arm}/{workload}: quiet admission")
        if arm == "kotoba":
            sample = row.get("sample") or {}
            check(sample.get("elapsedNs") == row.get("elapsedNs"),
                  f"kotoba/{workload}: structured elapsed time differs from row")
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
