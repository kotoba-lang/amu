#!/usr/bin/env python3
"""Hermetic controls for the Git-tree source revision audit."""
import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("source_audit", HERE / "audit-descriptor-source-revision.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="amu-source-audit-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.old_root = audit.ROOT
        audit.ROOT = self.root
        self.addCleanup(setattr, audit, "ROOT", self.old_root)
        self.git("init", "--quiet")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        (self.root / "seed").mkdir()
        (self.root / "seed/00-test.kotoba").write_bytes(b"first\n")
        (self.root / "seed/FULL-MANIFEST").write_text("seed/00-test.kotoba\n")
        self.source = self.commit("source")
        descriptor = {"sourceRevision": self.source, "sourceManifest": "seed/FULL-MANIFEST",
                      "sourceModuleCount": 1,
                      "sourceUnity": {"bytes": 7, "sha256": hashlib.sha256(b"first\n\n").hexdigest()}}
        (self.root / "native-product.json").write_text(json.dumps(descriptor))
        self.good = self.commit("descriptor")
        (self.root / "seed/00-test.kotoba").write_bytes(b"second\n")
        self.changed = self.commit("changed source")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode().strip()

    def commit(self, message):
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", message)
        return self.git("rev-parse", "HEAD")

    def test_expected_source_matches_but_is_not_provenance(self):
        result = audit.audit(self.good, None)
        self.assertEqual(result["status"], "MATCH")
        self.assertTrue(result["comparedDeclaredSourceRevision"])
        self.assertFalse(result["compilerBuildProvenanceVerified"])
        self.assertFalse(result["publicReleaseQualified"])

    def test_matching_other_revision_does_not_claim_declared_revision_was_checked(self):
        result = audit.audit(self.good, self.good)
        self.assertEqual(result["status"], "MATCH")
        self.assertFalse(result["comparedDeclaredSourceRevision"])
        self.assertEqual(result["descriptorSourceRevision"], self.source)

    def test_changed_source_does_not_match(self):
        result = audit.audit(self.good, self.changed)
        self.assertEqual(result["status"], "MISMATCH")
        self.assertFalse(result["comparedDeclaredSourceRevision"])
        self.assertNotEqual(result["expectedUnity"], result["actualUnity"])

    def test_mutable_or_missing_revision_refused(self):
        with self.assertRaises(ValueError):
            audit.audit("HEAD", None)
        with self.assertRaises(subprocess.CalledProcessError):
            audit.audit(self.good, "0" * 40)

    def test_shallow_checkout_without_source_commit_is_refused(self):
        with tempfile.TemporaryDirectory(prefix="amu-source-audit-shallow-") as parent:
            clone = Path(parent) / "checkout"
            subprocess.run(["git", "clone", "--quiet", "--no-local", "--depth=1",
                            str(self.root), str(clone)], check=True, capture_output=True)
            audit.ROOT = clone
            with self.assertRaises(subprocess.CalledProcessError):
                audit.audit(self.changed, None)

    def test_duplicate_or_unsafe_manifest_refused(self):
        for text in ("seed/00-test.kotoba\nseed/00-test.kotoba\n", "seed/../secret.kotoba\n"):
            (self.root / "seed/FULL-MANIFEST").write_text(text)
            descriptor = json.loads((self.root / "native-product.json").read_text())
            descriptor["sourceModuleCount"] = len(text.splitlines())
            (self.root / "native-product.json").write_text(json.dumps(descriptor))
            rev = self.commit("invalid manifest")
            with self.assertRaises(ValueError):
                audit.audit(rev, None)


if __name__ == "__main__":
    unittest.main()
