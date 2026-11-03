#!/usr/bin/env python3
"""Native round trip and hostile archive controls; no cached verdicts."""
import io
import os
import shutil
import tarfile
import tempfile
import unittest
from pathlib import Path

from bounded_cache_bundle import _extract_sealed, pack
from check_bounded_producer_attestation import exercise
from sealed_image import sealed_blob


class BundleControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = Path(os.environ["AMU_BOUNDED_FIXTURE"]).resolve()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="bounded-test-", dir=self.fixture.parent)
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_native_object_round_trip(self):
        bundle = self.root / "bundle.tar"
        pack(self.fixture / "producer.elf", self.fixture / "cache", bundle)
        with sealed_blob(bundle) as (fd, _):
            image, objects, image_digest = _extract_sealed(fd, self.root / "unpacked")
        exercise(image, objects, image_digest, self.root)

    def test_unexpected_cache_file_is_refused(self):
        cache = self.root / "cache"
        shutil.copytree(self.fixture / "cache", cache)
        cache.chmod(0o700)
        (cache / "stdout").write_text("old result")
        bundle = self.root / "bundle.tar"
        with self.assertRaises(ValueError):
            pack(self.fixture / "producer.elf", cache, bundle)
        self.assertFalse(bundle.exists())

    def test_hostile_archive_paths_and_links_are_refused_and_cleaned_up(self):
        for kind in ("traversal", "symlink", "duplicate", "verdict"):
            with self.subTest(kind=kind):
                bundle, out = self.root / (kind + ".tar"), self.root / (kind + "-out")
                with tarfile.open(bundle, "w") as tar:
                    image = tarfile.TarInfo("producer.elf")
                    image.size = 1
                    tar.addfile(image, io.BytesIO(b"x"))
                    name = {"traversal": "../escaped", "symlink": "objects/" + "a" * 64 + ".kdo",
                            "duplicate": "producer.elf", "verdict": "stdout"}[kind]
                    row = tarfile.TarInfo(name)
                    if kind == "symlink":
                        row.type, row.linkname = tarfile.SYMTYPE, "../../escaped"
                        tar.addfile(row)
                    else:
                        row.size = 1
                        tar.addfile(row, io.BytesIO(b"x"))
                with sealed_blob(bundle) as (fd, _), self.assertRaises(ValueError):
                    _extract_sealed(fd, out)
                self.assertFalse(out.exists())
                self.assertFalse((self.root / "escaped").exists())

    def test_insecure_or_symlinked_object_is_refused(self):
        for kind in ("permissions", "symlink"):
            with self.subTest(kind=kind):
                cache = self.root / (kind + "-cache")
                shutil.copytree(self.fixture / "cache", cache)
                cache.chmod(0o700)
                obj = next(cache.iterdir())
                if kind == "permissions":
                    obj.chmod(0o600)
                else:
                    obj.unlink()
                    obj.symlink_to(self.fixture / "producer.elf")
                bundle = self.root / (kind + ".tar")
                with self.assertRaises((ValueError, OSError)):
                    pack(self.fixture / "producer.elf", cache, bundle)
                self.assertFalse(bundle.exists())


if __name__ == "__main__":
    unittest.main()
