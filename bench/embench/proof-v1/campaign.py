#!/usr/bin/env python3
"""Create and verify proof-v1 schedules and result manifests.

This module is intentionally independent from the platform timing driver.  The
driver must execute the emitted schedule verbatim and append one attempt record
for every scheduled position, including rejected and failed observations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ZERO_HASH = "0" * 64
ARM_FOR = {"A": "kotoba-amu", "B": "c-reference"}
ORDERS = ("ABBA", "BAAB") * 5


def canonical_bytes(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sealed_hash(manifest: dict) -> str:
    copy = dict(manifest)
    copy["bundleSha256"] = ZERO_HASH
    return hashlib.sha256(canonical_bytes(copy)).hexdigest()


def workload_names() -> list[str]:
    data = json.loads((ROOT.parent / "reproduce-20261015" / "round-sa-m104-20261015" / "workloads.json").read_text())
    return sorted(row["workload"] for row in data)


def make_schedule() -> dict:
    events = []
    for workload in workload_names():
        for round_number, order in enumerate(ORDERS, 1):
            for position, symbol in enumerate(order, 1):
                events.append({
                    "workload": workload,
                    "round": round_number,
                    "order": order,
                    "sequencePosition": position,
                    "arm": ARM_FOR[symbol],
                })
    return {
        "schemaVersion": 1,
        "protocolId": "kotoba-amu-embench-proof-v1",
        "events": events,
    }


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_schedule(schedule: dict) -> None:
    expected = make_schedule()
    require(schedule == expected, "schedule differs from the preregistered 19 x 10 x 4 order")
    require(len(schedule["events"]) == 760, "schedule must contain exactly 760 positions")


def _attempt_key(item: dict) -> tuple:
    return tuple(item[key] for key in ("workload", "round", "order", "sequencePosition", "arm"))


def _percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    index = (len(ordered) - 1) * p
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - index) + ordered[upper] * (index - lower)


def summarize(manifest: dict, *, bootstrap_samples: int = 10000) -> dict:
    schedule = make_schedule()
    attempts = manifest.get("attempts", [])
    expected_keys = {_attempt_key(event) for event in schedule["events"]}
    actual_keys = [_attempt_key(item) for item in attempts]
    require(760 <= len(attempts) <= 2280, "manifest must retain 760 scheduled positions and at most three attempts each")
    require(set(actual_keys) == expected_keys, "attempts do not cover the fixed schedule")
    selected = []
    for key in expected_keys:
        rows = [item for item in attempts if _attempt_key(item) == key]
        numbers = [item.get("attemptNumber") for item in rows]
        require(numbers == list(range(1, len(rows) + 1)), f"non-contiguous attempt numbers for {key}")
        require(len(rows) <= 3, f"more than three attempts for {key}")
        accepted_indexes = [index for index, item in enumerate(rows) if item.get("accepted")]
        selected_rows = [item for item in rows if item.get("selected")]
        if accepted_indexes:
            first = accepted_indexes[0]
            require(first == len(rows) - 1, f"attempts continued after acceptance for {key}")
            require(selected_rows == [rows[first]], f"first accepted attempt must be selected for {key}")
            selected.append(rows[first])
        else:
            require(not selected_rows, f"rejected attempts cannot be selected for {key}")

    reasons = []
    ratios = []
    per_workload = []
    normalization = manifest.get("normalization", {})
    for workload in workload_names():
        accepted = [item for item in selected if item["workload"] == workload]
        if len(accepted) != 40:
            reasons.append(f"{workload}: accepted {len(accepted)}/40")
            continue
        if not all(item.get("elapsedNs", 0) > 0 for item in accepted):
            reasons.append(f"{workload}: missing positive elapsed time")
            continue
        if not all(item.get("correctness", {}).get("passed") is True for item in accepted):
            reasons.append(f"{workload}: correctness did not pass")
            continue
        if not all(item.get("cpuQualification", {}).get("passed") is True for item in accepted):
            reasons.append(f"{workload}: CPU qualification did not pass")
            continue
        factor = normalization.get(workload)
        if not isinstance(factor, (int, float)) or factor <= 0:
            reasons.append(f"{workload}: invalid normalization factor")
            continue
        paired = []
        for round_number in range(1, 11):
            round_rows = [item for item in accepted if item["round"] == round_number]
            a = [item["elapsedNs"] for item in round_rows if item["arm"] == "kotoba-amu"]
            b = [item["elapsedNs"] for item in round_rows if item["arm"] == "c-reference"]
            require(len(a) == 2 and len(b) == 2, f"{workload}: incomplete round {round_number}")
            paired.append(factor * statistics.median(a) / statistics.median(b))
        ratio = statistics.median(paired)
        ratios.append(ratio)
        per_workload.append({"workload": workload, "pairedRatios": paired, "medianRatio": ratio})

    complete = len(ratios) == 19 and not reasons
    geometric_mean = math.exp(statistics.mean(math.log(value) for value in ratios)) if complete else None
    seed = manifest.get("statistics", {}).get("bootstrapSeed")
    require(isinstance(seed, int), "statistics.bootstrapSeed must be an integer")
    ci = None
    if complete:
        rng = random.Random(seed)
        boot = []
        for _ in range(bootstrap_samples):
            sample = [ratios[rng.randrange(len(ratios))] for _ in ratios]
            boot.append(math.exp(statistics.mean(math.log(value) for value in sample)))
        ci = [_percentile(boot, 0.025), _percentile(boot, 0.975)]
    return {
        "complete": complete,
        "perWorkload": per_workload,
        "geometricMean": geometric_mean,
        "confidenceInterval95": ci,
        "bootstrapSeed": seed,
        "rejectionReasons": reasons,
    }


def verify_manifest(manifest: dict) -> None:
    require(manifest.get("protocolId") == "kotoba-amu-embench-proof-v1", "protocol ID mismatch")
    require(manifest.get("workloads") == workload_names(), "workload list must be the sorted full-19 set")
    require(manifest.get("bundleSha256") == sealed_hash(manifest), "bundle hash mismatch")
    calculated = summarize(manifest)
    require(manifest.get("statistics") == {key: calculated[key] for key in (
        "complete", "perWorkload", "geometricMean", "confidenceInterval95", "bootstrapSeed"
    )}, "statistics differ from deterministic recomputation")
    qualification = manifest.get("qualification", {})
    if calculated["complete"]:
        require(qualification.get("status") == "qualified", "complete result must be qualified")
    else:
        require(qualification.get("status") == "rejected", "incomplete result must be rejected")
        require(qualification.get("reasons") == calculated["rejectionReasons"], "rejection reasons differ")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    emit = sub.add_parser("schedule")
    emit.add_argument("--out", type=Path)
    verify = sub.add_parser("verify")
    verify.add_argument("manifest", type=Path)
    args = parser.parse_args()
    if args.command == "schedule":
        value = canonical_bytes(make_schedule()).decode()
        if args.out:
            args.out.write_text(value)
        else:
            print(value, end="")
    else:
        manifest = json.loads(args.manifest.read_text())
        verify_manifest(manifest)
        print("PROOF_V1_RESULT PASS")


if __name__ == "__main__":
    main()
