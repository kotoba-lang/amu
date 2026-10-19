#!/usr/bin/env python3
"""Validate and summarize the isolated M105 compiler-variant timing campaigns."""

import json
import math
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT.parent
RAW = ROOT / "raw"
CAMPAIGNS = (
    "timing-reciprocal-m4-clang17-r1",
    "timing-reciprocal-m4-clang17-r2",
    "timing-msub-m4-clang17-r1",
    "timing-msub-m4-clang17-r2",
)
EXPECTED_WORKLOADS = {
    "aha-mont64", "crc32", "depthconv", "edn", "huffbench", "matmult-int",
    "md5sum", "nettle-aes", "nettle-sha256", "nsichneu", "picojpeg", "qrduino",
    "sglib-combined", "slre", "statemate", "tarfind", "ud", "wikisort", "xgboost",
}


def gm(values):
    values = list(values)
    if not values or any(value <= 0 for value in values):
        raise ValueError("geometric mean requires non-empty positive values")
    return math.exp(sum(math.log(value) for value in values) / len(values))


def load_report(name):
    archive = RAW / (name + ".tar.gz")
    with tarfile.open(archive, "r:gz") as tar:
        report_member = next(member for member in tar.getmembers()
                             if member.name.endswith("/report.json"))
        report = json.load(tar.extractfile(report_member))
        if report.get("level") != "d-timing" or report.get("full19") is not True:
            raise ValueError(f"{name}: not a full-19 d_timing report")
        if report.get("acceptedKotoba") != 19 or report.get("acceptedC") != 19:
            raise ValueError(f"{name}: expected 19 accepted measurements on both arms")
        if set(report["kotoba"]["rows"]) != EXPECTED_WORKLOADS:
            raise ValueError(f"{name}: Kotoba report workload set mismatch")
        if set(report["c"]["rows"]) != EXPECTED_WORKLOADS:
            raise ValueError(f"{name}: C report workload set mismatch")

        raw_rows = {}
        for side in ("kotoba", "c"):
            for workload in sorted(EXPECTED_WORKLOADS):
                suffix = f"/{side}/results/measured/raw/{workload}.json"
                member = next(member for member in tar.getmembers()
                              if member.name.endswith(suffix))
                raw = json.load(tar.extractfile(member))
                index = raw.get("selectedAttempt")
                if not raw.get("complete") or index is None:
                    raise ValueError(f"{name}/{side}/{workload}: no selected raw attempt")
                sample = raw["samples"][index]
                if not sample.get("accepted") or sample.get("reasons"):
                    raise ValueError(f"{name}/{side}/{workload}: selected attempt was not accepted")
                elapsed = sample.get("elapsedNs")
                if elapsed != report[side]["rows"][workload]["elapsedNs"]:
                    raise ValueError(f"{name}/{side}/{workload}: raw/report elapsed mismatch")
                raw_rows.setdefault(side, 0)
                raw_rows[side] += 1
        if raw_rows != {"kotoba": 19, "c": 19}:
            raise ValueError(f"{name}: raw-row count mismatch: {raw_rows}")
    return report


def main():
    reports = {name: load_report(name) for name in CAMPAIGNS}
    reciprocal_images = json.loads(
        (EVIDENCE / "reciprocal-compiler/images.json").read_text())
    msub_images = json.loads((EVIDENCE / "msub-compiler/images.json").read_text())
    baseline_images = json.loads((EVIDENCE / "m105-baseline-images.json").read_text())
    baseline_analysis = json.loads(
        (EVIDENCE.parent / "m105-abba-m4-20261016/analysis.json").read_text())
    baseline_ratios = {
        workload: row["baselineGeometricMeanKotobaOverC"]
        for workload, row in baseline_analysis["perWorkload"].items()
    }
    if set(baseline_ratios) != EXPECTED_WORKLOADS:
        raise ValueError("M105 ABBA baseline does not cover the expected workloads")

    summaries = {}
    for name, report in reports.items():
        ratios = report["ratios"]
        summaries[name] = {
            "round": report["round"],
            "acceptedKotoba": report["acceptedKotoba"],
            "acceptedC": report["acceptedC"],
            "geometricMeanKotobaOverC": report["geometricMean"],
            "kotobaFasterWorkloads": sum(value < 1 for value in ratios.values()),
            "kotobaElapsedGeometricMeanNs": gm(
                row["elapsedNs"] for row in report["kotoba"]["rows"].values()),
            "cElapsedGeometricMeanNs": gm(
                row["elapsedNs"] for row in report["c"]["rows"].values()),
        }

    variants = {
        "reciprocal": {
            "images": reciprocal_images,
            "reports": [reports[CAMPAIGNS[0]], reports[CAMPAIGNS[1]]],
        },
        "msub": {
            "images": msub_images,
            "reports": [reports[CAMPAIGNS[2]], reports[CAMPAIGNS[3]]],
        },
    }
    variant_comparisons = {}
    for variant, data in variants.items():
        changed = sorted(workload for workload in EXPECTED_WORKLOADS
                         if baseline_images[workload]["native"]["sha256"]
                         != data["images"][workload]["native"]["sha256"])
        unchanged = sorted(EXPECTED_WORKLOADS - set(changed))
        variant_ratios = {
            workload: gm(report["ratios"][workload] for report in data["reports"])
            for workload in EXPECTED_WORKLOADS
        }
        baseline_changed = gm(baseline_ratios[workload] for workload in changed)
        variant_changed = gm(variant_ratios[workload] for workload in changed)
        baseline_control = gm(baseline_ratios[workload] for workload in unchanged)
        variant_control = gm(variant_ratios[workload] for workload in unchanged)
        control_shift = variant_control / baseline_control
        changed_shift = variant_changed / baseline_changed
        per_changed_workload = {
            workload: {
                "baselineKotobaOverC": baseline_ratios[workload],
                "variantMeanKotobaOverC": variant_ratios[workload],
                "variantOverBaseline": variant_ratios[workload] / baseline_ratios[workload],
                "controlAdjustedVariantOverBaseline": (
                    variant_ratios[workload] / baseline_ratios[workload] / control_shift
                ),
            }
            for workload in changed
        }
        variant_comparisons[variant] = {
            "imageChangedWorkloads": changed,
            "sameImageControlWorkloads": unchanged,
            "baselineChangedGroupKotobaOverC": baseline_changed,
            "variantChangedGroupKotobaOverC": variant_changed,
            "changedGroupVariantOverBaseline": changed_shift,
            "baselineSameImageControlKotobaOverC": baseline_control,
            "variantSameImageControlKotobaOverC": variant_control,
            "sameImageControlVariantOverBaseline": control_shift,
            "controlAdjustedChangedGroupVariantOverBaseline": changed_shift / control_shift,
            "perChangedWorkload": per_changed_workload,
        }

    reciprocal_to_msub_changed = sorted(
        workload for workload in EXPECTED_WORKLOADS
        if reciprocal_images[workload]["native"]["sha256"]
        != msub_images[workload]["native"]["sha256"])
    reciprocal_to_msub_unchanged = sorted(
        EXPECTED_WORKLOADS - set(reciprocal_to_msub_changed))
    reciprocal_reports = variants["reciprocal"]["reports"]
    msub_reports = variants["msub"]["reports"]
    reciprocal_changed_group = gm(
        report["ratios"][workload]
        for report in reciprocal_reports for workload in reciprocal_to_msub_changed)
    msub_changed_group = gm(
        report["ratios"][workload]
        for report in msub_reports for workload in reciprocal_to_msub_changed)
    reciprocal_control = gm(
        report["ratios"][workload]
        for report in reciprocal_reports for workload in reciprocal_to_msub_unchanged)
    msub_control = gm(
        report["ratios"][workload]
        for report in msub_reports for workload in reciprocal_to_msub_unchanged)
    reciprocal_to_msub_control_shift = msub_control / reciprocal_control
    reciprocal_to_msub_changed_shift = msub_changed_group / reciprocal_changed_group

    output = {
        "schemaVersion": 1,
        "host": "Apple M4 Mac mini (Mac16,10), macOS 26.2, Apple clang 17.0.0",
        "cBuildReceiptSHA256": "3e7ba67fe72a8763215069fef37679a1cb0ab8370b8df93438548b36b17d53dd",
        "comparisonOrder": list(CAMPAIGNS),
        "campaigns": summaries,
        "variantVsM105Baseline": variant_comparisons,
        "reciprocalVsMsub": {
            "imageChangedWorkloads": reciprocal_to_msub_changed,
            "sameImageControlWorkloads": reciprocal_to_msub_unchanged,
            "reciprocalChangedGroupKotobaOverC": reciprocal_changed_group,
            "msubChangedGroupKotobaOverC": msub_changed_group,
            "changedGroupMsubOverReciprocal": reciprocal_to_msub_changed_shift,
            "reciprocalSameImageControlKotobaOverC": reciprocal_control,
            "msubSameImageControlKotobaOverC": msub_control,
            "sameImageControlMsubOverReciprocal": reciprocal_to_msub_control_shift,
            "controlAdjustedChangedGroupMsubOverReciprocal": (
                reciprocal_to_msub_changed_shift / reciprocal_to_msub_control_shift
            ),
            "interpretation": (
                "MSub and reciprocal are separate fixed-point variants, not a simple "
                "incremental sequence: five images differ between them. The adjusted "
                "comparison is descriptive and does not establish a speedup with two "
                "campaigns per variant."
            ),
        },
    }
    (ROOT / "analysis.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
