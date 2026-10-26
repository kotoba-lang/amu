#!/usr/bin/env python3
"""Synthetic observer-format controls, never native benchmark qualification."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("candidate", HERE / "check-embench-native-candidate.py")
C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C)


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.payload = Path(self.temp.name) / "payload.bin"
        self.payload.write_bytes(b"\0" * 8)

    def header(self, offset=4, length=8, arity=0):
        return (f'{{:ok true, :output "{self.payload}", :offset {offset}, '
                f':length {length}, :arity {arity}}}\n').encode()

    def test_nonzero_reported_entry_is_preserved(self):
        self.assertEqual(4, C.entry_offset(self.header(), self.payload))
        self.assertEqual(0, C.entry_offset(self.header(offset=0), self.payload))

    def test_invalid_entry_report_refuses(self):
        for raw in (self.header(offset=2), self.header(offset=8),
                    self.header(length=9), self.header(arity=1),
                    self.header() * 2, self.header().replace(b"payload.bin", b"other.bin")):
            with self.subTest(raw=raw), self.assertRaises(AssertionError):
                C.entry_offset(raw, self.payload)

    def test_all17_counters_are_required_in_canonical_order(self):
        raw = b"KEXE_ARENA_USE {" + b" ".join(b":" + f.encode() + b" 0" for f in C.FIELDS) + b"}\n"
        self.assertEqual(dict.fromkeys(C.FIELDS, 0), C.arena(raw))
        for bad in (raw + raw, raw.replace(b":pairs 0 ", b""), raw.replace(b":pairs 0", b":pairs -1"),
                    raw.replace(b":pairs 0 :string-pool-bytes 0", b":string-pool-bytes 0 :pairs 0"),
                    raw + b"unexpected\n"):
            with self.subTest(raw=bad):
                self.assertIsNone(C.arena(bad))

    def test_canonical_source_count_and_reference_tables_match_frozen_hashes(self):
        C.verify_bundle_data(C.ROOT / "bench/embench/reproduce-20261015",
                             C.ROOT / "bench/embench/proof-v1/native-entry.kotoba")

    def test_modified_entry_template_refuses(self):
        entry = Path(self.temp.name) / "entry.kotoba"
        entry.write_bytes((C.ROOT / "bench/embench/proof-v1/native-entry.kotoba").read_bytes() + b" ")
        with self.assertRaises(AssertionError):
            C.verify_bundle_data(C.ROOT / "bench/embench/reproduce-20261015", entry)


if __name__ == "__main__":
    unittest.main()
