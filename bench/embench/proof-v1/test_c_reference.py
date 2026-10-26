#!/usr/bin/env python3
"""Pure record/source controls; no C compiler runs in native CDCI tests."""
import struct
import tempfile
import unittest
from pathlib import Path

import prepare_c_reference as C


class CReferenceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def source_fixture(self):
        sources = {"src/test/fixture.c": b"int value;\n", "support/support.h": b"/* fixture */\n"}
        sources.update({"baseline-data/f%d.json" % i: b"{}\n" for i in range(38)})
        for name, raw in sources.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        return {name: C.pin_bytes(raw)["sha256"] for name, raw in sources.items()}

    def image(self, machine=183, kind=3):
        raw = bytearray(128)
        raw[:8] = b"\x7fELF\x02\x01\x01\0"
        struct.pack_into("<HH", raw, 16, kind, machine)
        struct.pack_into("<Q", raw, 32, 64)
        struct.pack_into("<HH", raw, 54, 56, 1)
        struct.pack_into("<I", raw, 64, 1)
        path = self.root / "fixture.elf"
        path.write_bytes(raw)
        return path

    def test_fixed_flags_preserve_registered_c_profile(self):
        self.assertEqual(("-O2", "-std=gnu11", "-DWARMUP_HEAT=1", "-DGLOBAL_SCALE_FACTOR=32768"), C.FLAGS)

    def test_c_counts_bind_the_original_kotoba_normalization(self):
        rows = [dict(workload="fixture", LSF=170, n=170 * 8192 * 2, multiplier=2)]
        result = C.count_bindings({"src/fixture/source.c": b"#define LOCAL_SCALE_FACTOR 170\n"}, rows)
        self.assertEqual(170 * 32768, result["fixture"]["cScaleIterations"])
        self.assertEqual(2, result["fixture"]["declaredNormalization"])

    def test_different_c_local_factor_is_not_a_count_profile(self):
        rows = [dict(workload="fixture", LSF=170, n=170 * 8192 * 2, multiplier=2)]
        with self.assertRaisesRegex(ValueError, "local scale factor differs"):
            C.count_bindings({"src/fixture/source.c": b"#define LOCAL_SCALE_FACTOR 171\n"}, rows)

    def test_changed_registered_count_is_rejected(self):
        rows = [dict(workload="fixture", LSF=170, n=1, multiplier=2)]
        with self.assertRaisesRegex(ValueError, "scale count differs"):
            C.count_bindings({"src/fixture/source.c": b"#define LOCAL_SCALE_FACTOR 170\n"}, rows)

    def test_complete_source_snapshot(self):
        expected = self.source_fixture()
        snapshots = C.source_snapshot(self.root, expected)
        self.assertEqual(40, len(snapshots))
        self.assertEqual(b"int value;\n", snapshots["src/test/fixture.c"])

    def test_changed_source_refuses(self):
        expected = self.source_fixture()
        (self.root / "src/test/fixture.c").write_bytes(b"changed\n")
        with self.assertRaisesRegex(ValueError, "pinned upstream source differs"):
            C.source_snapshot(self.root, expected)

    def test_even_ignored_extra_c_input_refuses(self):
        expected = self.source_fixture()
        (self.root / "src/test/.gitignore").write_bytes(b"extra.c\n")
        (self.root / "src/test/extra.c").write_bytes(b"int hidden;\n")
        with self.assertRaisesRegex(ValueError, "extra or missing C/header"):
            C.source_snapshot(self.root, expected)

    def test_missing_header_refuses(self):
        expected = self.source_fixture()
        (self.root / "support/support.h").unlink()
        with self.assertRaisesRegex(ValueError, "extra or missing C/header"):
            C.source_snapshot(self.root, expected)

    def test_symlink_input_refuses_even_when_bytes_match(self):
        expected = self.source_fixture()
        path = self.root / "src/test/fixture.c"
        raw = path.read_bytes()
        path.unlink()
        target = self.root / "copy"
        target.write_bytes(raw)
        path.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "symlink source input"):
            C.source_snapshot(self.root, expected)

    def test_source_path_cannot_escape(self):
        for value in ("../outside", "/tmp/outside"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "bounded source path"):
                C.read_source(self.root, value)

    def test_elf_records_native_reference_not_kotoba_loader(self):
        record = C.elf_record(self.image(), 183)
        self.assertEqual("c-reference-only-not-kotoba-loader", record["role"])
        self.assertEqual(183, record["machine"])
        self.assertIsNone(record["interpreter"])

    def test_foreign_isa_refuses(self):
        with self.assertRaisesRegex(ValueError, "ISA differs"):
            C.elf_record(self.image(machine=62), 183)

    def test_gnu_linux_osabi_is_a_native_c_compiler(self):
        path = self.image()
        raw = bytearray(path.read_bytes())
        raw[7] = 3
        path.write_bytes(raw)
        self.assertEqual(183, C.elf_record(path, 183)["machine"])

    def test_foreign_osabi_refuses(self):
        path = self.image()
        raw = bytearray(path.read_bytes())
        raw[7] = 9
        path.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, "Linux ELF64"):
            C.elf_record(path, 183)

    def test_non_executable_elf_refuses(self):
        with self.assertRaisesRegex(ValueError, "ISA differs"):
            C.elf_record(self.image(kind=1), 183)

    def test_truncated_headers_refuse(self):
        path = self.image()
        path.write_bytes(path.read_bytes()[:80])
        with self.assertRaisesRegex(ValueError, "program headers"):
            C.elf_record(path, 183)

    def test_invalid_interpreter_refuses(self):
        path = self.image()
        raw = bytearray(path.read_bytes())
        struct.pack_into("<I", raw, 64, 3)
        struct.pack_into("<Q", raw, 72, 120)
        struct.pack_into("<Q", raw, 96, 1000)
        path.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, "invalid ELF interpreter"):
            C.elf_record(path, 183)

    def test_c_correctness_requires_exit_and_both_raw_streams(self):
        self.assertTrue(C.correctness(0, b"EMBENCH_NS=1\n", b""))
        for code, stdout, stderr in ((1, b"EMBENCH_NS=1\n", b""),
                                      (False, b"EMBENCH_NS=1\n", b""),
                                      (0, b"EMBENCH_NS=0\n", b""),
                                      (0, b"EMBENCH_NS=1\nextra\n", b""),
                                      (0, b"EMBENCH_NS=1\n", b"warning"),
                                      ("observer-timeout", b"EMBENCH_NS=1\n", b"")):
            with self.subTest(code=code, stdout=stdout, stderr=stderr):
                self.assertFalse(C.correctness(code, stdout, stderr))

    def test_duplicate_metadata_refuses(self):
        with self.assertRaisesRegex(ValueError, "duplicate metadata"):
            C.unique([("source", 1), ("source", 2)])


if __name__ == "__main__":
    unittest.main()
