#!/usr/bin/env python3
"""Selection, hostile ZIP and native cached-object round-trip controls."""
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from bounded_cache_bundle import _extract_sealed, pack
from check_bounded_producer_attestation import exercise
from fetch_bounded_cache import _artifact_matches, _run_matches, _select_artifact, _unzip_exact, fetch_verified
from sealed_image import sealed_blob

SHA = "a" * 40
REPO = 1297097065


class FetchControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = Path(os.environ["AMU_BOUNDED_FIXTURE"]).resolve()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="fetch-test-", dir=self.fixture.parent)
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_requires_exact_successful_main_run_and_repository(self):
        run = dict(id=42, event="push", status="completed", conclusion="success", head_branch="main", head_sha=SHA,
                   path=".github/workflows/bounded-cache-producer.yml", repository={"id": REPO},
                   head_repository={"id": REPO})
        self.assertTrue(_run_matches(run, SHA))
        for field, value in [("event", "pull_request"), ("conclusion", "failure"), ("head_branch", "other"),
                             ("head_sha", "b" * 40), ("path", ".github/workflows/other.yml"),
                             ("repository", {"id": 1}), ("head_repository", {"id": 1}), ("id", True)]:
            with self.subTest(field=field):
                self.assertFalse(_run_matches(dict(run, **{field: value}), SHA))

    def test_requires_exact_artifact_and_run(self):
        run = dict(id=42, repository_id=REPO, head_repository_id=REPO, head_branch="main", head_sha=SHA)
        artifact = dict(id=3, name="experimental-bounded-kir-producer-" + SHA, expired=False,
                        size_in_bytes=1024, digest="sha256:" + "c" * 64, workflow_run=run)
        self.assertTrue(_artifact_matches(artifact, 42, SHA))
        for field, value in [("name", "other"), ("expired", True), ("size_in_bytes", 0),
                             ("digest", "self-reported"), ("id", True), ("workflow_run", dict(run, id=43)),
                             ("workflow_run", dict(run, head_sha="b" * 40)),
                             ("workflow_run", dict(run, repository_id=1))]:
            with self.subTest(field=field, value=value):
                self.assertFalse(_artifact_matches(dict(artifact, **{field: value}), 42, SHA))
        self.assertIsNone(_select_artifact([], 42, SHA))
        self.assertIsNone(_select_artifact([dict(artifact, expired=True)], 42, SHA))
        with self.assertRaises(ValueError):
            _select_artifact([artifact, artifact], 42, SHA)
        with self.assertRaises(ValueError):
            _select_artifact([dict(artifact, digest="forged")], 42, SHA)
        with self.assertRaises(ValueError):
            fetch_verified("main", "/nonexistent", "0" * 64, self.root / "out")

    def test_zip_round_trip_keeps_fresh_native_admission(self):
        bundle, archive, unpacked = self.root / "source.tar", self.root / "artifact.zip", self.root / "received.tar"
        pack(self.fixture / "producer.elf", self.fixture / "cache", bundle)
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(bundle, "bounded-cache.tar")
        _unzip_exact(archive, unpacked)
        with sealed_blob(unpacked) as (fd, _):
            image, objects, digest = _extract_sealed(fd, self.root / "bundle")
        exercise(image, objects, digest, self.root)

    def test_hostile_zip_is_never_extracted(self):
        for kind in ("traversal", "symlink", "extra"):
            with self.subTest(kind=kind):
                archive, output = self.root / (kind + ".zip"), self.root / (kind + ".tar")
                with zipfile.ZipFile(archive, "w") as z:
                    name = "../escape" if kind == "traversal" else "bounded-cache.tar"
                    entry = zipfile.ZipInfo(name)
                    if kind == "symlink":
                        entry.create_system, entry.external_attr = 3, 0o120777 << 16
                    z.writestr(entry, b"x")
                    if kind == "extra":
                        z.writestr("stdout", b"old result")
                with self.assertRaises(ValueError):
                    _unzip_exact(archive, output)
                self.assertFalse(output.exists())
                self.assertFalse((self.root / "escape").exists())


if __name__ == "__main__":
    unittest.main()
