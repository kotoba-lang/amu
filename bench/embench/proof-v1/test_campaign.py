#!/usr/bin/env python3
import copy
import importlib.util
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("proof_campaign", HERE / "campaign.py")
C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C)


class CampaignTest(unittest.TestCase):
    def test_schedule_is_complete_and_balanced(self):
        schedule = C.make_schedule()
        C.validate_schedule(schedule)
        self.assertEqual(760, len(schedule["events"]))
        for workload in C.workload_names():
            rows = [row for row in schedule["events"] if row["workload"] == workload]
            self.assertEqual(5, len({row["round"] for row in rows if row["order"] == "ABBA"}))
            self.assertEqual(5, len({row["round"] for row in rows if row["order"] == "BAAB"}))

    def manifest(self):
        attempts = []
        for event in C.make_schedule()["events"]:
            row = dict(event)
            row.update(attemptNumber=1, selected=True, accepted=True,
                       elapsedNs=80 if row["arm"] == "kotoba-amu" else 100,
                       cpuQualification={"passed": True}, correctness={"passed": True})
            attempts.append(row)
        workloads = C.workload_names()
        result = {
            "protocolId": "kotoba-amu-embench-proof-v1",
            "workloads": workloads,
            "normalization": {name: 1 for name in workloads},
            "attempts": attempts,
            "statistics": {"bootstrapSeed": 104},
            "qualification": {"status": "qualified", "reasons": []},
            "bundleSha256": C.ZERO_HASH,
        }
        stats = C.summarize(result, bootstrap_samples=10000)
        result["statistics"] = {key: stats[key] for key in (
            "complete", "perWorkload", "geometricMean", "confidenceInterval95", "bootstrapSeed"
        )}
        result["bundleSha256"] = C.sealed_hash(result)
        return result

    def test_complete_manifest_is_deterministic(self):
        manifest = self.manifest()
        C.verify_manifest(manifest)
        self.assertAlmostEqual(0.8, manifest["statistics"]["geometricMean"])
        self.assertEqual([0.8, 0.8], manifest["statistics"]["confidenceInterval95"])

    def test_missing_attempt_is_rejected(self):
        manifest = self.manifest()
        manifest["attempts"].pop()
        with self.assertRaisesRegex(ValueError, "760 scheduled positions"):
            C.summarize(manifest)

    def test_cpu_retry_is_retained_and_first_acceptance_selected(self):
        manifest = self.manifest()
        first = manifest["attempts"][0]
        rejected = copy.deepcopy(first)
        rejected.update(attemptNumber=1, selected=False, accepted=False, elapsedNs=None,
                        cpuQualification={"passed": False})
        first["attemptNumber"] = 2
        manifest["attempts"].insert(0, rejected)
        stats = C.summarize(manifest)
        self.assertTrue(stats["complete"])

    def test_tamper_breaks_seal(self):
        manifest = self.manifest()
        tampered = copy.deepcopy(manifest)
        tampered["attempts"][0]["elapsedNs"] += 1
        with self.assertRaisesRegex(ValueError, "bundle hash mismatch"):
            C.verify_manifest(tampered)


if __name__ == "__main__":
    unittest.main()
