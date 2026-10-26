#!/usr/bin/env python3
"""Validate proof-v1 control files without third-party dependencies."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKLOADS = {
    "aha-mont64", "crc32", "depthconv", "edn", "huffbench",
    "matmult-int", "md5sum", "nettle-aes", "nettle-sha256",
    "nsichneu", "picojpeg", "qrduino", "sglib-combined", "slre",
    "statemate", "tarfind", "ud", "wikisort", "xgboost",
}


def load(name: str) -> dict:
    with (ROOT / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def load_from_repository(relative_path: str) -> dict:
    with (ROOT.parents[2] / relative_path).open(encoding="utf-8") as handle:
        return json.load(handle)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"PROOF_V1_CONTROL FAIL: {message}")


def main() -> None:
    claims = load("claim-matrix.json")
    protocol = load("protocol.json")
    evidence = load("evidence-index.json")
    schema = load("result-manifest.schema.json")

    require(claims.get("schemaVersion") == 1, "claim matrix schemaVersion")
    claim_ids = {item.get("id") for item in claims.get("claims", [])}
    require(len(claim_ids) == len(claims.get("claims", [])), "claim IDs must be unique")
    require("amu-faster-than-c-universal" in claim_ids, "universal C claim must be explicit")
    universal = next(item for item in claims["claims"] if item["id"] == "amu-faster-than-c-universal")
    require(universal.get("status") == "withheld", "universal C claim must remain withheld")

    require(protocol.get("protocolId") == "kotoba-amu-embench-proof-v1", "protocol ID")
    require(protocol.get("state") == "preregistered-before-new-timing", "protocol must be preregistered")
    require(protocol["scope"].get("workloadSet") == "all-19", "full workload set required")
    require(protocol["scope"].get("subsetHeadlineAllowed") is False, "subset headlines forbidden")
    require(protocol["timing"].get("pairedRounds", 0) >= 10, "at least 10 paired rounds")
    require(protocol["timing"].get("adaptiveRetry") is False, "adaptive retry forbidden")
    require(protocol["statistics"].get("crossHostAverageForbidden") is True, "cross-host average forbidden")
    require(len(protocol.get("negativeControls", [])) >= 7, "seven negative controls required")

    require(evidence.get("schemaVersion") == 1, "evidence index schemaVersion")
    evidence_ids = {item.get("id") for item in evidence.get("evidence", [])}
    require(len(evidence_ids) == len(evidence.get("evidence", [])), "evidence IDs must be unique")
    for item in evidence.get("evidence", []):
        path = ROOT.parents[2] / item["path"]
        require(path.is_file(), f"missing evidence path: {item['path']}")
        require(item.get("official") is False, f"current evidence cannot be marked official: {item['id']}")
    original = next(item for item in evidence["evidence"] if item["id"] == "m104-original-m4")
    original_record = load_from_repository(original["path"])
    require(original_record.get("sourceCommit") == original["sourceRevision"],
            "M104 original source revision drift")
    require(abs(original_record.get("KotobaElapsedDividedByC") - original["ratioKotobaElapsedOverC"]) < 1e-15,
            "M104 original ratio drift")
    second = next(item for item in evidence["evidence"] if item["id"] == "m104-second-m4-macmini")
    second_record = load_from_repository(second["path"])
    require(second_record.get("acceptedKotoba") == 19 and second_record.get("acceptedC") == 19,
            "M104 second host must retain both 19/19 arms")
    require(abs(second_record.get("geometricMean") - second["ratioKotobaElapsedOverC"]) < 1e-9,
            "M104 second-host ratio drift")
    rejected = next(item for item in evidence["evidence"] if item["id"] == "m104-m1-rejected")
    require(rejected.get("ratioKotobaElapsedOverC") is None, "rejected run cannot have a ratio")
    rejected_record = load_from_repository(rejected["path"])
    require(rejected_record.get("acceptedKotoba") == 0 and rejected_record.get("acceptedC") == 0,
            "rejected M1 acceptance drift")
    require(rejected_record.get("geometricMean") is None, "rejected M1 run cannot expose a geometric mean")

    require(schema.get("$schema", "").endswith("2020-12/schema"), "JSON Schema draft")
    required = set(schema.get("required", []))
    require({"attempts", "negativeControls", "qualification", "bundleSha256"} <= required,
            "portable result bundle fields")
    workloads = schema["properties"]["workloads"]
    require(workloads.get("minItems") == len(WORKLOADS), "manifest requires 19 workloads")
    require(schema["properties"]["attempts"].get("minItems", 0) >= 760,
            "manifest requires all ABBA/BAAB observations")
    attempt_required = set(schema["$defs"]["attempt"].get("required", []))
    require("sequencePosition" in attempt_required, "attempt sequence position required")

    print("PROOF_V1_CONTROL PASS")


if __name__ == "__main__":
    main()
