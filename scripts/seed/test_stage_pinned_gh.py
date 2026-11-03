#!/usr/bin/env python3
"""Pinned verifier archive staging, refusal and no-clobber controls."""
import hashlib
import io
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import stage_pinned_gh as stage


class StageControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="gh-stage-")
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def archive(self, name, *, symlink=False, duplicate=False):
        path = self.root / name
        with tarfile.open(path, "w:gz") as tar:
            row = tarfile.TarInfo(stage.MEMBER)
            if symlink:
                row.type, row.linkname = tarfile.SYMTYPE, "../../escape"
                tar.addfile(row)
            else:
                row.size = 3
                tar.addfile(row, io.BytesIO(b"elf"))
                if duplicate:
                    tar.addfile(row, io.BytesIO(b"elf"))
        return path

    def test_pins_and_no_clobber(self):
        archive, output = self.archive("valid.tar.gz"), self.root / "gh"
        pin = hashlib.sha256(archive.read_bytes()).hexdigest()
        with patch.object(stage, "ARCHIVE_SHA256", pin), patch.object(stage, "GH_SHA256", hashlib.sha256(b"elf").hexdigest()):
            stage.stage(archive, output)
            self.assertEqual(output.read_bytes(), b"elf")
            with self.assertRaises(FileExistsError):
                stage.stage(archive, output)
            self.assertEqual(output.read_bytes(), b"elf")
        with patch.object(stage, "ARCHIVE_SHA256", "0" * 64), self.assertRaises(ValueError):
            stage.stage(archive, self.root / "bad")
        self.assertFalse((self.root / "bad").exists())

    def test_duplicate_or_symlinked_member_is_rejected(self):
        for kind in ("duplicate", "symlink"):
            with self.subTest(kind=kind):
                archive = self.archive(kind + ".tar.gz", duplicate=kind == "duplicate", symlink=kind == "symlink")
                pin = hashlib.sha256(archive.read_bytes()).hexdigest()
                with patch.object(stage, "ARCHIVE_SHA256", pin), self.assertRaises(ValueError):
                    stage.stage(archive, self.root / (kind + "-out"))
                self.assertFalse((self.root / (kind + "-out")).exists())


if __name__ == "__main__":
    unittest.main()
