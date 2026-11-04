#!/usr/bin/env python3
"""Negative controls for repin_allowlist.py (ADR 0404)."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import repin_allowlist as r  # noqa: E402


class Allowlist(unittest.TestCase):
    def test_pins_allowed(self):
        self.assertEqual(r.check(["native-product.json", "seed/cdci/policy.json", "seed/adoption-x.json"]), [])

    def test_source_path_rejected(self):
        self.assertEqual(r.check(["seed/12-foo.kotoba"]), ["seed/12-foo.kotoba"])
        self.assertEqual(r.check([".github/workflows/x.yml"]), [".github/workflows/x.yml"])

    def test_seed79_semantic_edit_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            run = lambda *a: subprocess.run(["git", "-C", d, *a], check=True, capture_output=True)
            run("init", "-q")
            run("config", "user.email", "t@t")
            run("config", "user.name", "t")
            f = Path(d) / "seed/79-native-cdci.kotoba"
            f.parent.mkdir(parents=True)
            h = "0" * 64
            f.write_text(f'(a)\n(string=? role "x") "{h}"\n')
            run("add", "-A")
            run("commit", "-qm", "i")
            f.write_text(f'(a)\n(string=? role "x") "{"1" * 64}"\n')
            self.assertEqual(r.check(["seed/79-native-cdci.kotoba"], d), [])
            f.write_text(f'(b)\n(string=? role "x") "{"1" * 64}"\n')
            self.assertEqual(len(r.check(["seed/79-native-cdci.kotoba"], d)), 1)


if __name__ == "__main__":
    unittest.main()
