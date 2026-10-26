#!/usr/bin/env python3
"""Record-integrity tests, not executed benchmark negative controls."""
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import audit_measurement_records as A


class MeasurementRecordTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        archive = A.ANCHOR.parent / "measurement-arm-records-r3.tar.gz"
        if A.C.pin(archive)["sha256"] != "e1970cd8ebd2cbe7598459b724d8d0de2847cf7cca89869f783042257c830897":
            raise ValueError("reviewed record archive differs")
        # Read a bounded, fixed member set; never extract archive paths.
        wanted = {"observations.json", "host.kotoba", "registry.kotoba", "observer.py"}
        wanted.update(name + "." + suffix for name in
                      ("build", *A.FACTORY, *A.RUNTIME, *A.workload_names())
                      for suffix in ("stdout", "stderr"))
        cls.fixture = {}
        with tarfile.open(archive, "r|gz") as source:
            for member in source:
                prefix = "measurement-host-controls-r4/"
                if not member.name.startswith(prefix):
                    continue
                name = member.name[len(prefix):]
                if name in wanted:
                    if name in cls.fixture or not member.isfile() or member.size > 16 * 1024 * 1024:
                        raise ValueError("invalid reviewed fixture member")
                    cls.fixture[name] = source.extractfile(member).read()
        if set(cls.fixture) != wanted:
            raise ValueError("incomplete reviewed raw fixture")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        for name, raw in self.fixture.items():
            (self.directory / name).write_bytes(raw)
        self.report = A.decode(self.fixture["observations.json"])

    def save(self):
        (self.directory / "observations.json").write_bytes(A.canonical_bytes(self.report))

    def audit(self):
        self.save()
        return A.audit(self.directory)

    def change_receipt(self, field, value, raw=None):
        row = self.report["workloads"][0]
        row["observation"][field] = value
        name = row["workload"]
        stream = self.directory / (name + ".stdout")
        stream.write_bytes(A.canonical_bytes(row["observation"]) if raw is None else raw)
        call = next(call for call in self.report["calls"] if call["name"] == name)
        call["stdout"] = A.C.pin(stream)

    def test_reviewed_raw_records_are_consistent_but_not_a_campaign(self):
        result = self.audit()
        self.assertEqual("consistent", result["records"])
        self.assertEqual(19, result["originalCountWorkloads"])
        self.assertEqual(25, result["rawRefusalRecords"])
        for key in ("performanceQualified", "nativeVerdictAuthority", "campaignReady"):
            self.assertIs(False, result[key])
        self.assertNotIn("geometricMean", result)
        self.assertNotIn("elapsedNs", result)
        self.assertEqual(result, self.audit())

    def test_raw_tampering_is_rejected(self):
        path = self.directory / "crc32.stdout"
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "pin differs"):
            self.audit()

    def test_changed_source_graph_is_rejected(self):
        self.report["sources"]["seed/01-mem.kotoba"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "complete source graph differs"):
            self.audit()

    def test_omitted_workload_is_rejected(self):
        self.report["workloads"].pop()
        with self.assertRaisesRegex(ValueError, "full sorted19"):
            self.audit()

    def test_wrong_payload_is_rejected(self):
        self.report["workloads"][0]["payload"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "payload identity differs"):
            self.audit()

    def test_wrong_host_is_rejected(self):
        self.report["host"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "host identity differs"):
            self.audit()

    def test_unknown_observer_is_rejected(self):
        self.report["observer"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "reviewed observer identity differs"):
            self.audit()

    def test_diagnostic_report_is_not_registered_evidence(self):
        self.report["mode"] = "diagnostic-one-body"
        with self.assertRaisesRegex(ValueError, "registered complete ARM"):
            self.audit()

    def test_diagnostic_raw_receipt_is_rejected(self):
        self.change_receipt("diagnostic", 1)
        with self.assertRaisesRegex(ValueError, "registered native receipt"):
            self.audit()

    def test_wrong_accounting_cannot_be_hidden_by_rehash(self):
        for field in ("benchmarkFuel", "verifyFuel", "warmSeed", "benchmarkArena", "finalArena"):
            with self.subTest(field=field):
                original = self.report["workloads"][0]["observation"][field]
                changed = [value + 1 for value in original] if isinstance(original, list) else original + 1
                self.change_receipt(field, changed)
                with self.assertRaisesRegex(ValueError, "independent accounting differs"):
                    self.audit()
                self.change_receipt(field, original)

    def test_stored_receipt_cannot_disagree_with_stdout(self):
        self.report["workloads"][0]["observation"]["elapsedNs"] += 1
        with self.assertRaisesRegex(ValueError, "differs from raw stdout"):
            self.audit()

    def test_bool_float_and_duplicate_native_fields_are_rejected(self):
        for value in (True, 1.0):
            self.change_receipt("result", value)
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "registered native receipt"):
                self.audit()
        self.change_receipt("result", 1)
        raw = A.canonical_bytes(self.report["workloads"][0]["observation"])
        self.change_receipt("result", 1, raw.replace(b'"result":1', b'"result":1,"result":1'))
        with self.assertRaisesRegex(ValueError, "duplicate native receipt field"):
            self.audit()

    def test_modified_staged_source_is_rejected(self):
        (self.directory / "host.kotoba").write_bytes(b"changed source")
        with self.assertRaisesRegex(ValueError, "staged hostSource pin differs"):
            self.audit()

    def test_process_timeout_cannot_pass(self):
        self.report["calls"][-1]["exit"] = "observer-timeout"
        with self.assertRaisesRegex(ValueError, "terminal process exit"):
            self.audit()

    def test_changed_count_in_invocation_is_rejected(self):
        self.report["calls"][-1]["argv"][3] = "1"
        with self.assertRaisesRegex(ValueError, "registered workload invocation differs"):
            self.audit()

    def test_different_launch_program_is_rejected(self):
        self.report["calls"][0]["argv"][0] = "/usr/bin/cc"
        with self.assertRaisesRegex(ValueError, "host build invocation differs"):
            self.audit()

    def test_historical_graph_is_not_misreported_as_current(self):
        pin = A.C.pin

        def changed(path):
            result = pin(path)
            if path == A.ROOT / "seed/01-mem.kotoba":
                return dict(result, sha256="0" * 64)
            return result

        with patch.object(A.C, "pin", side_effect=changed):
            result = self.audit()
        self.assertIs(False, result["sourceGraphCurrent"])
        self.assertIs(False, result["campaignReady"])

    def test_missing_or_reordered_refusals_are_rejected(self):
        self.report["factoryRefusals"].reverse()
        with self.assertRaisesRegex(ValueError, "complete refusal observations"):
            self.audit()

    def test_qualification_promotion_is_rejected(self):
        self.report["performanceQualified"] = True
        with self.assertRaisesRegex(ValueError, "cannot promote qualification"):
            self.audit()

    def test_symlink_raw_record_is_rejected(self):
        path = self.directory / "crc32.stderr"
        path.unlink()
        path.symlink_to("empty-fuel.stdout")
        with self.assertRaisesRegex(ValueError, "symlink record refused"):
            self.audit()

    def test_duplicate_report_fields_are_rejected(self):
        self.save()
        path = self.directory / "observations.json"
        raw = path.read_bytes()
        path.write_bytes(raw.replace(b'"mode":"registered"', b'"mode":"registered","mode":"registered"'))
        with self.assertRaisesRegex(ValueError, "duplicate native receipt field"):
            A.audit(self.directory)

    def test_subsecond_record_is_retained_without_campaign_promotion(self):
        self.change_receipt("elapsedNs", 1)
        result = self.audit()
        self.assertLess(result["observedOneSecondFloorWorkloads"], 19)
        self.assertIs(False, result["campaignReady"])

    def test_cli_invalid_record_exits_two(self):
        (self.directory / "observations.json").write_bytes(b"{}")
        result = subprocess.run([sys.executable, str(Path(A.__file__)), str(self.directory)],
                                capture_output=True, timeout=30)
        self.assertEqual(2, result.returncode)
        self.assertIn(b"MEASUREMENT_RECORD_AUDIT REJECTED", result.stderr)


if __name__ == "__main__":
    unittest.main()
