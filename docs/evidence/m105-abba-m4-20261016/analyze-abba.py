#!/usr/bin/env python3
"""Recompute the four-round M105 ABBA comparison from retained raw reports."""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RUNS = {
    "B1": "timing-baseline-m4-clang17-r2",
    "A1": "timing-candidate-m4-clang17-r1",
    "A2": "timing-candidate-m4-clang17-r2",
    "B2": "timing-baseline-m4-clang17-r3",
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def gm(values):
    values = list(values)
    return math.exp(sum(math.log(x) for x in values) / len(values))


def load_campaign(label, name):
    base = HERE / name
    report = json.loads((base / "report.json").read_text())
    if not report.get("full19") or report.get("acceptedKotoba") != 19 or report.get("acceptedC") != 19:
        raise SystemExit(f"{label}: campaign is not accepted full19")
    checks = {}
    minimum_raw_idle = 100.0
    minimum_background_idle = 100.0
    for arm in ("kotoba", "c"):
        rows = report[arm]["rows"]
        if len(rows) != 19:
            raise SystemExit(f"{label}/{arm}: report row count is not 19")
        for workload, row in rows.items():
            raw_path = base / arm / "results/measured/raw" / f"{workload}.json"
            raw = json.loads(raw_path.read_text())
            selected = raw.get("selectedAttempt")
            if selected is None:
                raise SystemExit(f"{label}/{arm}/{workload}: no selected raw attempt")
            sample = raw["samples"][selected]
            if not sample.get("accepted") or sample.get("returncode") != 0:
                raise SystemExit(f"{label}/{arm}/{workload}: selected attempt was not accepted")
            elapsed = (
                sample["sample"].get("elapsedNs")
                if sample.get("sample") is not None
                else sample.get("elapsedNs")
            )
            if elapsed != row.get("elapsedNs"):
                raise SystemExit(f"{label}/{arm}/{workload}: report elapsed time differs from raw")
            activity = sample["cpuActivity"]
            minimum_raw_idle = min(minimum_raw_idle, activity["idlePercent"])
            minimum_background_idle = min(minimum_background_idle, activity["estimatedBackgroundIdlePercent"])
        checks[arm] = {"accepted": len(rows), "rawFilesVerified": len(rows)}
    return report, checks, minimum_raw_idle, minimum_background_idle


def main():
    data = {}
    campaign_summary = {}
    gate_minima = {}
    for label, name in RUNS.items():
        report, checks, raw_idle, background_idle = load_campaign(label, name)
        data[label] = report
        campaign_summary[label] = {
            "directory": name,
            "startedEpochSeconds": report["started"],
            "endedEpochSeconds": report["ended"],
            "geometricMeanKotobaOverC": report["geometricMean"],
            "acceptedKotoba": report["acceptedKotoba"],
            "acceptedC": report["acceptedC"],
            "rawRowsVerified": checks,
        }
        gate_minima[label] = {
            "minimumEnclosingRawIdlePercent": raw_idle,
            "minimumEstimatedBackgroundIdlePercent": background_idle,
        }

    workload_rows = json.loads(
        (ROOT / "bench/embench/reproduce-20261015/round-sa-m104-20261015/workloads.json").read_text()
    )
    multipliers = {row["workload"]: row["multiplier"] for row in workload_rows}
    names = sorted(multipliers)
    for label, report in data.items():
        if set(report["ratios"]) != set(names):
            raise SystemExit(f"{label}: normalized ratio set is not the pinned 19 workloads")
        for workload in names:
            k = report["kotoba"]["rows"][workload]["elapsedNs"]
            c = report["c"]["rows"][workload]["elapsedNs"]
            recomputed = (4 / multipliers[workload]) * k / c
            if not math.isclose(recomputed, report["ratios"][workload], rel_tol=1e-12):
                raise SystemExit(f"{label}/{workload}: normalized ratio does not match raw elapsed times")

    baseline_table = json.loads(
        (ROOT / "docs/evidence/crossdomain-m105-all19-20261016/m105-baseline-images.json").read_text()
    )
    candidate_table = json.loads(
        (ROOT / "docs/evidence/crossdomain-m105-all19-20261016/images.json").read_text()
    )
    changed = sorted(
        workload for workload in names
        if baseline_table[workload]["native"]["sha256"] != candidate_table[workload]["native"]["sha256"]
    )
    unchanged = sorted(set(names) - set(changed))

    variants = {
        "baseline": [data["B1"]["geometricMean"], data["B2"]["geometricMean"]],
        "candidate": [data["A1"]["geometricMean"], data["A2"]["geometricMean"]],
    }
    variant_gm = {key: gm(values) for key, values in variants.items()}
    per_workload = {}
    raw_ratios = {"kotoba": {}, "c": {}}
    for workload in names:
        baseline_ratio = gm(data[label]["ratios"][workload] for label in ("B1", "B2"))
        candidate_ratio = gm(data[label]["ratios"][workload] for label in ("A1", "A2"))
        per_workload[workload] = {
            "baselineGeometricMeanKotobaOverC": baseline_ratio,
            "candidateGeometricMeanKotobaOverC": candidate_ratio,
            "candidateOverBaselineNormalizedRatio": candidate_ratio / baseline_ratio,
        }
        for arm in ("kotoba", "c"):
            baseline_time = gm(data[label][arm]["rows"][workload]["elapsedNs"] for label in ("B1", "B2"))
            candidate_time = gm(data[label][arm]["rows"][workload]["elapsedNs"] for label in ("A1", "A2"))
            raw_ratios[arm][workload] = candidate_time / baseline_time
            per_workload[workload][f"candidateOverBaseline{arm.title()}RawTime"] = candidate_time / baseline_time

    c_receipt = HERE / RUNS["B1"] / "c-build/build-c.json"
    if not c_receipt.is_file():
        raise SystemExit("common C build receipt is missing")
    result = {
        "schemaVersion": 1,
        "comparisonOrder": ["B1", "A1", "A2", "B2"],
        "interpretation": "Repeated translated-port comparison on one M4 host; per-campaign d_timing gates accepted all 19 workloads in both arms.",
        "protocol": data["B1"]["protocol"],
        "host": data["B1"]["host"],
        "commonCBuildReceiptSHA256": sha256(c_receipt),
        "campaigns": campaign_summary,
        "minimumObservedCpuGates": gate_minima,
        "baselineMeanOfTwoCampaignGeometricMeans": variant_gm["baseline"],
        "candidateMeanOfTwoCampaignGeometricMeans": variant_gm["candidate"],
        "candidateOverBaselineNormalizedRatio": variant_gm["candidate"] / variant_gm["baseline"],
        "imageChangedWorkloads": changed,
        "imageUnchangedWorkloads": unchanged,
        "rawKotobaElapsedCandidateOverBaselineGM": {
            "all19": gm(raw_ratios["kotoba"].values()),
            "unchangedImages": gm(raw_ratios["kotoba"][w] for w in unchanged),
            "changedImages": gm(raw_ratios["kotoba"][w] for w in changed),
        },
        "rawCElapsedCandidateOverBaselineGM": {
            "all19": gm(raw_ratios["c"].values()),
            "unchangedImages": gm(raw_ratios["c"][w] for w in unchanged),
            "changedImages": gm(raw_ratios["c"][w] for w in changed),
        },
        "perWorkload": per_workload,
    }
    output = HERE / "analysis.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"WROTE {output}")


if __name__ == "__main__":
    main()
