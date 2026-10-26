#!/usr/bin/env python3
"""Verify retained native observations; this grants no performance status."""
import hashlib
import json
import re
from pathlib import Path

from campaign import require, verify_artifacts, workload_names

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/evidence/embench-native-preparation-20261026"
COMPILER_SHA = "881c26ff74ec67cb0e6a1885bd185f203657c33bbb5e3cc43c1e5f141fe80292"


def check_pin(path, expected):
    raw = path.read_bytes()
    require({"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)} == expected,
            f"pin differs: {path.name}")


def verify_record(directory, snapshot, accepted):
    report = json.loads((directory / "native-build.json").read_text())
    require(report["schema"] == "amu.embench.native-preparation.v1", "native record schema")
    require(report["host"][:2] == ["Linux", "x86_64"], "native record host")
    require(report["fixedPoint"] is True and len(report["compilerGenerations"]) == 3,
            "three native generations required")
    require(report["compiler"]["sha256"] == COMPILER_SHA, "observed compiler identity")
    require(all(generation == report["compiler"] for generation in report["compilerGenerations"]),
            "native fixed point differs")
    require(report["performanceQualified"] is False, "preparation cannot be performance-qualified")
    check_pin(EVIDENCE / snapshot, report["preparationScript"])
    check_pin(ROOT / "bench/embench/proof-v1/native-entry.kotoba", report["entry"])
    names = workload_names()
    require([row["workload"] for row in report["workloads"]] == names, "full sorted19 required")
    expected_calls = ["selfbuild-F2", "selfbuild-F3", "native-runner-compile"]
    for name in names:
        expected_calls.extend([name + "-compile", name + "-run"])
    require([call["name"] for call in report["calls"]] == expected_calls, "native call order/coverage differs")
    artifacts = []
    for call in report["calls"]:
        for stream in ("stdout", "stderr"):
            entry = call[stream]
            artifacts.append({"path": entry["path"], "sha256": entry["sha256"]})
            check_pin(directory / entry["path"], {key: entry[key] for key in ("bytes", "sha256")})
    verify_artifacts({"artifacts": artifacts}, directory)
    counts = {row["workload"]: row["n"] for row in json.loads(
        (ROOT / "bench/embench/reproduce-20261015/round-sa-m104-20261015/workloads.json").read_text())}
    calls = {call["name"]: call for call in report["calls"]}
    for row in report["workloads"]:
        name = row["workload"]
        source = ROOT / "bench/embench/reproduce-20261015/ports" / ("official-" + name + ".kotoba")
        check_pin(source, row["originalSource"])
        require(row["originalSource"] == row["stagedSource"], "original workload bytes changed")
        require(calls[name + "-compile"]["exit"] == 0, f"compile failed: {name}")
        observed = calls[name + "-run"]
        stdout = (directory / observed["stdout"]["path"]).read_bytes()
        stderr = (directory / observed["stderr"]["path"]).read_bytes()
        values = re.findall(rb":result (-?[0-9]+)\b", stdout)
        result = int(values[0]) if len(values) == 1 else None
        require(row["result"] == result, "result differs from native stdout")
        passed = observed["exit"] == 0 and not stderr and result == 1
        require(row["accepted"] is passed, "acceptance differs from process output")
        if report.get("iterationProfile") == "m104-counts":
            require(row["iterations"] == counts[name], "registered count differs")
        else:
            require(row.get("iterations", report.get("iterations")) == 1, "one-body count differs")
    require(sum(row["accepted"] for row in report["workloads"]) == report["acceptedWorkloads"] == accepted,
            "accepted count differs")
    return report


def main():
    verify_record(EVIDENCE / "one-body", "native-build-one-body.source.txt", 19)
    full = verify_record(EVIDENCE / "full-counts", "native-build-m104-counts.source.txt", 0)
    failures = [call for call in full["calls"] if call["name"].endswith("-run")]
    messages = [(EVIDENCE / "full-counts" / call["stderr"]["path"]).read_bytes() for call in failures]
    require(sum(b"vector-table-exhausted" in message for message in messages) == 1 and
            sum(b"SIGALRM" in message for message in messages) == 18, "diagnostic refusal classification differs")
    traced = verify_record(EVIDENCE / "traced/observations-traced-one-body", "native-build-m104-counts.source.txt", 19)
    trace = (EVIDENCE / "traced/execution-closure.trace").read_text()
    paths = re.findall(r'execve\("([^\"]+)"', trace)
    expected = ["/usr/bin/python3"] + [call["argv"][0] for call in traced["calls"]]
    require(paths == expected and len(paths) == 42 and "execveat(" not in trace,
            "execution trace contains unexpected or missing child programs")
    require(all(line.endswith("= 0") for line in trace.splitlines() if " execve(" in line),
            "execution trace contains an unsuccessful program launch")
    print("NATIVE_PREPARATION_RECORDS PASS: one-body19/19, full-count0/19, traced42 execs; performance unqualified")


if __name__ == "__main__":
    main()
