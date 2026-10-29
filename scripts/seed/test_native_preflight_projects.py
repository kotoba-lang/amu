"""Preflight process ordering/failure controls; no native qualification."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import native_preflight_projects as P


class PreflightProjectsTests(unittest.TestCase):
    def test_original_project_then_fs_argv_are_preserved(self):
        compiler = P.ROOT / "bin/amu-linux-x86_64"
        with tempfile.TemporaryDirectory() as directory, patch.object(P.subprocess, "run") as run:
            temporary = Path(directory)
            P.main(compiler, temporary)
            image = json.loads((P.ROOT / "native-product.json").read_text())["image"]["sha256"]
            self.assertEqual(run.call_args_list[0].args[0], [
                sys.executable, str(P.ROOT / "scripts/seed/check-x86-project-native.py"),
                "--compiler", str(compiler), "--output", str(temporary / "local-native-project")])
            self.assertEqual(run.call_args_list[1].args[0], [
                sys.executable, str(P.ROOT / "scripts/seed/check-x86-project-fs-native.py"),
                "--compiler", str(compiler), "--compiler-sha256", image,
                "--runner", str(temporary / "local-native-project/runner.elf"),
                "--output", str(temporary / "project-fs-candidate"), "--derive"])
            self.assertEqual(run.call_count, 2)
            self.assertTrue(all(call.kwargs == {"check": True} for call in run.call_args_list))

    def test_project_refusal_stops_its_dependent_fs_candidate(self):
        with patch.object(P.subprocess, "run", side_effect=subprocess.CalledProcessError(7, ["project"])) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                P.main(P.ROOT / "bin/amu-linux-x86_64", Path("/unused"))
            self.assertEqual(run.call_count, 1)

    def test_fs_refusal_is_not_a_successful_preflight(self):
        with patch.object(P.subprocess, "run", side_effect=[None, subprocess.CalledProcessError(9, ["fs"])]) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                P.main(P.ROOT / "bin/amu-linux-x86_64", Path("/unused"))
            self.assertEqual(run.call_count, 2)

    def test_preflight_plan_keeps_all_independent_controls(self):
        plan = json.loads((P.ROOT / "seed/native-preflight-plan.json").read_text())
        self.assertEqual(plan["schema"], "amu.native-gate-plan.v1")
        gates = plan["phases"]["preflight"]
        self.assertEqual([g["name"] for g in gates], ["local-project-fs", "early-kotoba", "b2-preflight"])
        self.assertEqual(gates[1]["argv"], ["python3", "scripts/seed/check-native-kotoba-early.py",
            "--compiler", "bin/amu-linux-x86_64", "--output", "@TEMP@/early-kotoba"])
        self.assertEqual(gates[2]["argv"], ["python3", "scripts/seed/check-b2-libc.py",
            "--compiler", "bin/amu-linux-x86_64", "--output", "@TEMP@/b2-libc-preflight"])


if __name__ == "__main__":
    unittest.main()
