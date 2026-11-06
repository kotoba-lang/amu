#!/usr/bin/env python3
"""Controls for pr_batch.py: stack detection and the refusal to combine a non-contained stack."""
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pr_batch as b  # noqa: E402


def pr(n, head, base, files=(), state="CLEAN", draft=False):
    return dict(number=n, title="t", headRefName=head, baseRefName=base, headRefOid=f"{n:040d}",
                files=[{"path": f} for f in files], mergeStateStatus=state, isDraft=draft, author={})


def git_ok(*a, check=True):
    return subprocess.CompletedProcess(a, 0, "", "")


def git_no(*a, check=True):
    return subprocess.CompletedProcess(a, 1, "", "")


class Batch(unittest.TestCase):
    prs = [pr(1, "a", "main"), pr(2, "b", "a"), pr(3, "c", "b"), pr(4, "x", "main", ["native-product.json"]),
           pr(5, "y", "main", ["native-product.json", "z"])]

    def test_stack_detected(self):
        s = b.stacks(self.prs)
        self.assertEqual([[p["number"] for p in c] for c, _ in s], [[1, 2, 3]])

    def test_combinable_when_contained(self):
        self.assertTrue(b.combinable(self.prs[:3], git_ok)[0])

    def test_not_combinable_when_not_contained(self):
        ok, why = b.combinable(self.prs[:3], git_no)
        self.assertFalse(ok)
        self.assertIn("#2", why)

    def test_dirty_blocks(self):
        chain = [pr(1, "a", "main"), pr(2, "b", "a", state="DIRTY")]
        self.assertFalse(b.combinable(chain, git_ok)[0])

    def test_overlap_reports_pins_and_skips_stack(self):
        rows = b.overlaps(self.prs, {1, 2, 3})
        self.assertEqual(rows, [(4, 5, 1, ["native-product.json"])])

    def test_report_text(self):
        txt = b.report(self.prs, git_ok)
        self.assertIn("#1 <- #2 <- #3", txt)
        self.assertIn("#4 x #5", txt)


if __name__ == "__main__":
    unittest.main()
