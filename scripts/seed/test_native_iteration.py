"""Observer/scheduler negative controls, not native compiler qualification."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from native_build_queue import build_slot, execute, run_plan
from native_process_profile import observe_controller

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "scripts/seed/native_build_queue.py"


class NativeIterationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_independent_wrappers_share_two_slots(self):
        events = self.root / "events.jsonl"
        program = ("import fcntl,json,time,sys; "
                   "f=open(sys.argv[1],'a'); "
                   "fcntl.flock(f,fcntl.LOCK_EX); f.write(json.dumps([time.monotonic(),1])+'\\n'); f.flush(); "
                   "fcntl.flock(f,fcntl.LOCK_UN); time.sleep(.35); "
                   "fcntl.flock(f,fcntl.LOCK_EX); f.write(json.dumps([time.monotonic(),-1])+'\\n'); f.flush()")
        processes = [subprocess.Popen([sys.executable, str(QUEUE), "--slot-dir", str(self.root / "slots"),
                                      "--", sys.executable, "-c", program, str(events)],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                     for _ in range(5)]
        for process in processes:
            self.assertEqual(process.wait(timeout=15), 0)
        active = peak = 0
        for _, delta in sorted(json.loads(line) for line in events.read_text().splitlines()):
            active += delta
            peak = max(peak, active)
            self.assertLessEqual(active, 2)
        self.assertEqual((peak, active), (2, 0))

    def test_capacity_mismatch_refuses(self):
        with build_slot(self.root / "slots", 2):
            with self.assertRaisesRegex(ValueError, "capacity mismatch"):
                with build_slot(self.root / "slots", 3):
                    self.fail("mismatched capacity admitted")

    def test_slot_remains_held_by_child_after_wrapper_kill(self):
        ready = self.root / "ready"
        wrapper = subprocess.Popen([sys.executable, str(QUEUE), "--capacity", "1", "--slot-dir", str(self.root / "slots"),
                                    "--", sys.executable, "-c",
                                    "import pathlib,sys,time; pathlib.Path(sys.argv[1]).touch(); time.sleep(.8)", str(ready)],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + 5
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(ready.exists())
        wrapper.kill()
        wrapper.wait()
        timing = execute([sys.executable, "-c", "pass"], directory=self.root / "slots", capacity=1)
        self.assertGreater(timing["queuedSeconds"], .3)

    def test_failure_does_not_skip_other_gates_or_hide_pipeline(self):
        manifest = self.root / "plan.json"
        marker = self.root / "other-ran"
        manifest.write_text(json.dumps(dict(schema="amu.native-gate-plan.v1", phases=dict(test=[
            dict(name="broken", argv=["bash", "-euo", "pipefail", "-c", "exit 7 | cat"]),
            dict(name="other", argv=[sys.executable, "-c", "import pathlib,sys; pathlib.Path(sys.argv[1]).touch()", str(marker)])]))))
        old = os.environ.get("RUNNER_TEMP")
        os.environ["RUNNER_TEMP"] = str(self.root)
        try:
            code = run_plan(manifest, "test", self.root / "logs", directory=self.root / "slots")
        finally:
            if old is None:
                os.environ.pop("RUNNER_TEMP")
            else:
                os.environ["RUNNER_TEMP"] = old
        self.assertEqual(code, 1)
        self.assertTrue(marker.exists())
        report = json.loads((self.root / "logs/schedule.json").read_text())
        self.assertEqual(sorted(row["exit"] for row in report["gates"]), [0, 7])

    def test_worker_queue_is_recorded_separately_from_slot_wait(self):
        manifest = self.root / "queue-plan.json"
        manifest.write_text(json.dumps(dict(schema="amu.native-gate-plan.v1", phases=dict(test=[
            dict(name=f"gate-{i}", argv=[sys.executable, "-c", "import time; time.sleep(.2)"])
            for i in range(5)]))))
        old = os.environ.get("RUNNER_TEMP")
        os.environ["RUNNER_TEMP"] = str(self.root)
        try:
            self.assertEqual(run_plan(manifest, "test", self.root / "logs", directory=self.root / "slots"), 0)
        finally:
            if old is None:
                os.environ.pop("RUNNER_TEMP")
            else:
                os.environ["RUNNER_TEMP"] = old
        rows = json.loads((self.root / "logs/schedule.json").read_text())["gates"]
        self.assertEqual(len(rows), 5)
        self.assertGreater(max(r["workerQueueSeconds"] for r in rows), .2)
        for row in rows:
            self.assertAlmostEqual(row["queuedSeconds"], row["workerQueueSeconds"] + row["slotQueueSeconds"])
            self.assertLess(row["startSeconds"], row["endSeconds"])

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux /proc observer")
    def test_observer_preserves_outputs_exit_and_accounts_children(self):
        # These are explicitly Python harness controls, not compiler artifacts.
        for name in ("amu-selfhost.elf", "kotoba-native.elf"):
            shutil.copy2(sys.executable, self.root / name)
        controller = self.root / "control.py"
        controller.write_text("""import subprocess,sys,time,stat,os
from pathlib import Path
p=Path(__file__).parent
assert stat.S_ISFIFO(os.fstat(1).st_mode) and stat.S_ISFIFO(os.fstat(2).st_mode)
spin='import time; end=time.monotonic()+.35\\nwhile time.monotonic()<end: pass'
time.sleep(.15)
subprocess.run([p/'amu-selfhost.elf','-c',spin],check=True)
time.sleep(.15)
subprocess.run([p/'kotoba-native.elf','-c',spin],check=True)
time.sleep(.15)
print('verdict bytes')
print('control stderr',file=sys.stderr)
raise SystemExit(7)
""")
        profile = self.root / "profile.json"
        result = observe_controller([sys.executable, controller], cwd=self.root, env=os.environ.copy(),
                                    timeout=10, output=profile)
        self.assertEqual(result.returncode, 7)
        self.assertEqual(result.stdout, b"verdict bytes\n")
        self.assertEqual(result.stderr, b"control stderr\n")
        data = json.loads(profile.read_text())
        self.assertEqual(data["status"], "COMPLETED")
        self.assertFalse(data["nativeVerdictAuthority"])
        self.assertEqual({row["role"] for row in data["children"]}, {"amu-rebuild", "kotoba-gate"})
        self.assertAlmostEqual(sum(row["seconds"] for row in data["phases"]), data["elapsedSeconds"], places=6)
        self.assertGreater(data["reapedChildrenCPUSeconds"], .15)
        self.assertGreaterEqual(data["controllerCPUSeconds"], 0)

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux /proc observer")
    def test_timeout_is_not_success_and_cleans_parent(self):
        profile = self.root / "timeout.json"
        with self.assertRaises(subprocess.TimeoutExpired):
            observe_controller([sys.executable, "-c", "import time;time.sleep(10)"], cwd=self.root,
                               env=os.environ.copy(), timeout=.1, output=profile)
        self.assertEqual(json.loads(profile.read_text())["status"], "TIMEOUT")


if __name__ == "__main__":
    unittest.main()
