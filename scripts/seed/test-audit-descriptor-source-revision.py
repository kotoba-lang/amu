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

    def test_null_declared_revision_audits_the_descriptor_commit(self):
        descriptor = json.loads((self.root / "native-product.json").read_text())
        descriptor["sourceRevision"] = None
        (self.root / "native-product.json").write_text(json.dumps(descriptor))
        (self.root / "seed/00-test.kotoba").write_bytes(b"first\n")
        implicit = self.commit("regenerated descriptor")
        result = audit.audit(implicit, None)
        self.assertEqual(result["status"], "MATCH")
        self.assertTrue(result["sourceRevisionImplicit"])
        self.assertEqual(result["sourceRevisionTested"], implicit)
        (self.root / "seed/00-test.kotoba").write_bytes(b"third\n")
        stale = self.commit("source without regenerated descriptor")
        self.assertEqual(audit.audit(stale, None)["status"], "MISMATCH")

    def test_changed_source_does_not_match(self):
        result = audit.audit(self.good, self.changed)
        self.assertEqual(result["status"], "MISMATCH")
        self.assertFalse(result["comparedDeclaredSourceRevision"])
        self.assertNotEqual(result["expectedUnity"], result["actualUnity"])

    def test_replacement_refs_do_not_change_audited_commit_bytes(self):
        original = self.git("rev-parse", self.source + ":seed/00-test.kotoba")
        replacement = self.git("rev-parse", self.changed + ":seed/00-test.kotoba")
        self.git("replace", original, replacement)
        self.assertEqual(self.git("show", self.source + ":seed/00-test.kotoba"), "second")
        self.assertEqual(audit.audit(self.good, None)["status"], "MATCH")

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

    def test_partial_clone_missing_blob_is_refused_without_lazy_fetch(self):
        self.git("config", "uploadpack.allowFilter", "true")
        with tempfile.TemporaryDirectory(prefix="amu-source-audit-partial-") as parent:
            clone = Path(parent) / "checkout"
            subprocess.run(["git", "clone", "--quiet", "--filter=blob:none",
                            "--no-checkout", self.root.as_uri(), str(clone)],
                           check=True, capture_output=True)
            before = subprocess.run(["git", "--no-lazy-fetch", "-C", str(clone),
                                     "cat-file", "-e", self.good + ":native-product.json"],
                                    capture_output=True)
            self.assertNotEqual(before.returncode, 0, "fixture must omit the descriptor blob")
            audit.ROOT = clone
            with self.assertRaises(subprocess.CalledProcessError):
                audit.audit(self.good, None)
            after = subprocess.run(["git", "--no-lazy-fetch", "-C", str(clone),
                                    "cat-file", "-e", self.good + ":native-product.json"],
                                   capture_output=True)
            self.assertNotEqual(after.returncode, 0, "audit must not fetch the missing blob")

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
