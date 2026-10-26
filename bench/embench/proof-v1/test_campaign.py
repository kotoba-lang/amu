#!/usr/bin/env python3
import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("proof_campaign", HERE / "campaign.py")
C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C)


class CampaignTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.bundle = Path(self.temp.name)
        (self.bundle / "fixture.txt").write_text("synthetic verifier fixture\n")

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
        data = json.loads((HERE.parent / "reproduce-20261015/round-sa-m104-20261015/workloads.json").read_text())
        factors = {row["workload"]: 4 / row["multiplier"] for row in data}
        for event in C.make_schedule()["events"]:
            row = dict(event)
            row.update(attemptNumber=1, selected=True, accepted=True, reasons=[],
                       elapsedNs=int(800000000000 / factors[row["workload"]]) if row["arm"] == "kotoba-amu" else 1000000000000,
                       cpuQualification={"passed": True, "preIdlePercent": 90, "duringIdlePercent": 90,
                                         "backgroundIdlePercent": 90, "thermalState": "nominal"},
                       correctness={"passed": True})
            attempts.append(row)
        workloads = C.workload_names()
        result = {
            "schemaVersion": 1,
            "protocolId": "kotoba-amu-embench-proof-v1",
            "runner": {"kind": "project", "organizationDisclosure": "synthetic fixture", "supportReceived": "none"},
            "repository": {"url": "https://github.com/kotoba-lang/amu", "commit": "0" * 40, "dirty": False},
            "host": {"hardware": "synthetic", "architecture": "synthetic", "os": "synthetic",
                     "logicalCpuCount": 1, "powerPolicy": "synthetic"},
            "toolchains": {"amu": {}, "c": {}},
            "artifacts": [{"path": "fixture.txt", "sha256": hashlib.sha256((self.bundle / "fixture.txt").read_bytes()).hexdigest()}],
            "workloads": workloads,
            "normalization": factors,
            "attempts": attempts,
            "statistics": {"bootstrapSeed": 104},
            "negativeControls": [{"name": name, "status": "pending", "evidencePath": None}
                                 for name in json.loads((HERE / "protocol.json").read_text())["negativeControls"]],
            "qualification": {"status": "rejected", "reasons": [C.PENDING_NATIVE_GATE], "evidenceLevel": "unqualified"},
            "bundleSha256": C.ZERO_HASH,
        }
        self.calculate(result)
        return result

    def calculate(self, result):
        stats = C.summarize(result)
        result["statistics"] = {key: stats[key] for key in (
            "complete", "perWorkload", "geometricMean", "confidenceInterval95", "bootstrapSeed"
        )}
        result["qualification"]["reasons"] = stats["rejectionReasons"] + [C.PENDING_NATIVE_GATE]
        result["bundleSha256"] = C.sealed_hash(result)

    def verify(self, result):
        result["bundleSha256"] = C.sealed_hash(result)
        C.verify_manifest(result, self.bundle)

    def test_complete_manifest_is_deterministic(self):
        manifest = self.manifest()
        self.verify(manifest)
        self.assertAlmostEqual(0.8, manifest["statistics"]["geometricMean"])
        for endpoint in manifest["statistics"]["confidenceInterval95"]:
            self.assertAlmostEqual(0.8, endpoint)

    def test_missing_attempt_is_rejected(self):
        manifest = self.manifest()
        manifest["attempts"].pop()
        with self.assertRaisesRegex(ValueError, "760 scheduled positions"):
            C.summarize(manifest)

    def test_cpu_retry_is_retained_and_first_acceptance_selected(self):
        manifest = self.manifest()
        first = manifest["attempts"][0]
        rejected = copy.deepcopy(first)
        rejected.update(attemptNumber=1, selected=False, accepted=False, reasons=["cpu-qualification"], elapsedNs=None)
        rejected["cpuQualification"].update(passed=False, preIdlePercent=50)
        first["attemptNumber"] = 2
        manifest["attempts"].insert(0, rejected)
        stats = C.summarize(manifest)
        self.assertTrue(stats["complete"])
        self.calculate(manifest)
        self.verify(manifest)

    def test_cli_does_not_return_success_for_unqualified_records(self):
        manifest = self.manifest()
        path = self.bundle / "manifest.json"
        path.write_bytes(C.canonical_bytes(manifest))
        result = subprocess.run([sys.executable, str(HERE / "campaign.py"), "verify", str(path)],
                                env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(2, result.returncode)
        self.assertIn("PROOF_V1_RECORDS PASS; QUALIFICATION REJECTED", result.stdout)

    def test_tamper_breaks_seal(self):
        manifest = self.manifest()
        tampered = copy.deepcopy(manifest)
        tampered["attempts"][0]["elapsedNs"] += 1
        with self.assertRaisesRegex(ValueError, "bundle hash mismatch"):
            C.verify_manifest(tampered, self.bundle)

    def test_missing_envelope_rejected(self):
        base = self.manifest()
        for field in ("runner", "repository", "host", "toolchains", "artifacts", "negativeControls"):
            manifest = copy.deepcopy(base)
            del manifest[field]
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "missing required"):
                self.verify(manifest)

    def test_cannot_grant_claim_grade_status(self):
        manifest = self.manifest()
        manifest["qualification"].update(status="qualified", evidenceLevel="claim-grade-author-run", reasons=[])
        with self.assertRaisesRegex(ValueError, "native measurement qualification is pending"):
            self.verify(manifest)

    def test_order_is_enforced(self):
        manifest = self.manifest()
        manifest["attempts"][1], manifest["attempts"][2] = manifest["attempts"][2], manifest["attempts"][1]
        with self.assertRaisesRegex(ValueError, "fixed schedule"):
            C.summarize(manifest)

    def test_correctness_failure_cannot_be_retried(self):
        manifest = self.manifest()
        rejected = copy.deepcopy(manifest["attempts"][0])
        rejected.update(accepted=False, selected=False, reasons=["cpu-qualification"])
        rejected["correctness"]["passed"] = False
        rejected["cpuQualification"]["passed"] = False
        manifest["attempts"][0]["attemptNumber"] = 2
        manifest["attempts"].insert(0, rejected)
        with self.assertRaisesRegex(ValueError, "only for CPU"):
            C.summarize(manifest)

    def test_continuation_after_acceptance_rejected(self):
        manifest = self.manifest()
        extra = copy.deepcopy(manifest["attempts"][0])
        extra["attemptNumber"] = 2
        manifest["attempts"].insert(1, extra)
        with self.assertRaisesRegex(ValueError, "continued after acceptance"):
            C.summarize(manifest)

    def test_cpu_numbers_override_boolean(self):
        manifest = self.manifest()
        manifest["attempts"][0]["cpuQualification"]["preIdlePercent"] = 69.9
        self.calculate(manifest)
        self.assertIsNone(manifest["statistics"]["geometricMean"])
        self.assertEqual(19, len(manifest["statistics"]["perWorkload"]))
        self.verify(manifest)

    def test_one_second_floor_enforced(self):
        manifest = self.manifest()
        manifest["attempts"][0]["elapsedNs"] = 999999999
        self.calculate(manifest)
        self.assertIsNone(manifest["statistics"]["geometricMean"])
        self.verify(manifest)

    def test_rejected_position_retains_full19_without_aggregate(self):
        manifest = self.manifest()
        manifest["attempts"][0].update(accepted=False, selected=False, elapsedNs=None, reasons=["execution-failed"])
        self.calculate(manifest)
        self.assertFalse(manifest["statistics"]["complete"])
        self.assertEqual(19, len(manifest["statistics"]["perWorkload"]))
        self.verify(manifest)

    def test_artifact_hash_checked(self):
        manifest = self.manifest()
        manifest["artifacts"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "artifact hash mismatch"):
            self.verify(manifest)

    def test_path_traversal_rejected(self):
        manifest = self.manifest()
        for path in ("../outside", "/tmp/outside"):
            manifest["artifacts"][0]["path"] = path
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "bounded relative path"):
                self.verify(manifest)

    def test_negative_controls_need_evidence(self):
        manifest = self.manifest()
        manifest["negativeControls"][0].update(status="passed", evidencePath="missing.txt")
        with self.assertRaisesRegex(ValueError, "verified artifact"):
            self.verify(manifest)

    def test_normalization_cannot_be_tuned(self):
        manifest = self.manifest()
        manifest["normalization"][C.workload_names()[0]] *= 0.5
        with self.assertRaisesRegex(ValueError, "pinned iteration counts"):
            C.summarize(manifest)

    def test_bootstrap_keeps_workloads_fixed(self):
        manifest = self.manifest()
        for row in manifest["attempts"]:
            if row["workload"] == C.workload_names()[0] and row["arm"] == "kotoba-amu":
                row["elapsedNs"] *= 2
        stats = C.summarize(manifest)
        for endpoint in stats["confidenceInterval95"]:
            self.assertAlmostEqual(stats["geometricMean"], endpoint)

    def test_bootstrap_captures_round_variation(self):
        manifest = self.manifest()
        for row in manifest["attempts"]:
            if row["arm"] == "kotoba-amu":
                row["elapsedNs"] *= row["round"]
        stats = C.summarize(manifest)
        self.assertLess(stats["confidenceInterval95"][0], stats["geometricMean"])
        self.assertGreater(stats["confidenceInterval95"][1], stats["geometricMean"])


if __name__ == "__main__":
    unittest.main()
