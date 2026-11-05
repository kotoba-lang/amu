#!/usr/bin/env python3
"""Negative controls for scripts/ci/ci_gate.py (JUN-759): what may be skipped, what must change a key and which steps
must stop when the gate skips."""
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ci_gate as G  # noqa: E402


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def opener(files, total=1):
    def call(request, timeout=0):
        page = int(request.full_url.rsplit("page=", 1)[1])
        rows = [dict(filename=n) for n in files[(page - 1) * 100:page * 100]]
        return Response(json.dumps(dict(files=rows, total_commits=total)).encode())
    return call


class Inert(unittest.TestCase):
    def test_inert_paths(self):
        for path in ("README.md", "CHANGELOG.md", "docs/notes/a.md", "LICENSE", "bench/.DS_Store",
                     ".github/dependabot.yml", "scripts/ci/pr_batch.py", "scripts/ci/repin_allowlist.py",
                     ".github/workflows/post-merge-repin.yml"):
            self.assertTrue(G.is_inert(path), path)

    def test_everything_a_gate_can_read_is_not_inert(self):
        for path in ("docs/evidence/x/README.md", "docs/language-ladder.edn", "seed/README.md", "seed/00-core.kotoba",
                     "scripts/seed/check-io-read.py", "scripts/ci/ci_gate.py", "scripts/ci/new_tool.py", "scripts/ci/pr_batch.py.bak", "bin/amu-linux-x86_64",
                     "native-product.json", ".github/workflows/selfhost-native.yml", ".github/workflows/merge-guard.yml", ".github/actions/ci-gate/action.yml",
                     "examples/foundation-starter/MACOS-ARM64.md", "tools/c/sm70/README.md", "src/a.kotoba"):
            self.assertFalse(G.is_inert(path), path)


class Hashes(unittest.TestCase):
    rows = [("100644", "a" * 40, "README.md"), ("100644", "b" * 40, "seed/x.kotoba"),
            ("100644", "c" * 40, "scripts/seed/check-gate.py"), ("100644", "d" * 40, "scripts/seed/selfhost-bootstrap.py"),
            ("100644", "e" * 40, "scripts/seed/test_gate.py")]

    def hash(self, rows, kind="marker", keep=frozenset()):
        return G.tree_hash(rows, kind, keep)[0]

    def test_docs_do_not_change_either_key(self):
        changed = [("100644", "f" * 40, "README.md")] + self.rows[1:]
        for kind in ("marker", "derive"):
            self.assertEqual(self.hash(self.rows, kind), self.hash(changed, kind))

    def test_any_other_change_changes_the_marker(self):
        for index in range(1, len(self.rows)):
            changed = list(self.rows)
            changed[index] = (changed[index][0], "0" * 40, changed[index][2])
            self.assertNotEqual(self.hash(self.rows), self.hash(changed), self.rows[index][2])

    def test_gate_scripts_change_only_the_marker_unless_the_derivation_references_them(self):
        changed = list(self.rows)
        changed[2] = (changed[2][0], "0" * 40, changed[2][2])
        self.assertNotEqual(self.hash(self.rows), self.hash(changed))
        self.assertEqual(self.hash(self.rows, "derive"), self.hash(changed, "derive"))
        keep = frozenset({"check-gate.py"})
        self.assertNotEqual(self.hash(self.rows, "derive", keep), self.hash(changed, "derive", keep))

    def test_derivation_inputs_always_change_the_derive_key(self):
        for index in (1, 3):
            changed = list(self.rows)
            changed[index] = (changed[index][0], "0" * 40, changed[index][2])
            self.assertNotEqual(self.hash(self.rows, "derive"), self.hash(changed, "derive"))

    def test_kinds_and_mode_are_part_of_the_key(self):
        self.assertNotEqual(self.hash(self.rows, "marker"), self.hash(self.rows, "derive"))
        changed = [("100755", self.rows[1][1], self.rows[1][2])]
        self.assertNotEqual(self.hash(self.rows[1:2]), self.hash(changed))


class Keys(unittest.TestCase):
    def test_tiers(self):
        self.assertEqual([G.tier_of(e) for e in ("pull_request", "merge_group", "push", "schedule", "workflow_dispatch")],
                         ["pr", "pr", "main", "full", "full"])
        exact, others = G.keys("marker", "j (1)", "Linux-X64", "pr", "h")
        self.assertTrue(exact.endswith("-pr-h") and " " not in exact and "(" not in exact)
        self.assertEqual([o.rsplit("-", 2)[-2] for o in others], ["main", "full"])
        self.assertEqual([o.rsplit("-", 2)[-2] for o in G.keys("marker", "j", "a", "main", "h")[1]], ["full"])
        self.assertEqual(G.keys("marker", "j", "a", "full", "h")[1], [])

    def test_arch_is_part_of_the_key(self):
        self.assertNotEqual(G.keys("marker", "j", "Linux-ARM64", "pr", "h")[0], G.keys("marker", "j", "Linux-X64", "pr", "h")[0])


class DocsOnly(unittest.TestCase):
    env = dict(GITHUB_REPOSITORY="o/r", GITHUB_TOKEN="t", PR_BASE_SHA="b", PR_HEAD_SHA="h", MG_BASE_SHA="b", MG_HEAD_SHA="h")

    def check(self, event, files, total=1):
        return G.docs_only(event, self.env, opener(files, total))

    def test_only_inert_files_skip(self):
        for event in ("pull_request", "merge_group"):
            self.assertTrue(self.check(event, ["README.md", "docs/a.md"]))
            self.assertFalse(self.check(event, ["README.md", "seed/00-core.kotoba"]))
            self.assertFalse(self.check(event, ["README.md", "docs/evidence/a/README.md"]))
            self.assertFalse(self.check(event, []))

    def test_unknown_or_large_answers_never_skip(self):
        self.assertFalse(self.check("pull_request", ["README.md"] * 301))
        self.assertFalse(self.check("pull_request", ["README.md"], total=0))
        broken = dict(self.env)
        del broken["GITHUB_TOKEN"]
        self.assertFalse(G.docs_only("pull_request", broken, opener(["README.md"])))

        def boom(request, timeout=0):
            raise OSError("offline")
        self.assertFalse(G.docs_only("pull_request", self.env, boom))

    def test_push_schedule_and_dispatch_never_skip(self):
        for event in ("push", "schedule", "workflow_dispatch", ""):
            self.assertFalse(G.docs_only(event, self.env, opener(["README.md"])))

    def test_rename_out_of_a_real_path_is_not_docs_only(self):
        def rename(request, timeout=0):
            return Response(json.dumps(dict(files=[dict(filename="docs/a.md", previous_filename="seed/a.kotoba")], total_commits=1)).encode())
        self.assertFalse(G.docs_only("pull_request", self.env, rename))


class Closure(unittest.TestCase):
    def test_closure_follows_names_and_imports(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "scripts/seed"
            d.mkdir(parents=True)
            (d / "a.py").write_text("import helper\nx = 'check-b.py'\n")
            (d / "helper.py").write_text("")
            (d / "check-b.py").write_text("")
            (d / "check-unrelated.py").write_text("")
            self.assertEqual(G.closure(["a.py"], tmp), {"a.py", "helper.py", "check-b.py"})
            with self.assertRaises(SystemExit):
                G.closure(["missing.py"], tmp)

    def test_real_derivation_roots_resolve(self):
        root = Path(__file__).resolve().parents[2]
        keep = G.closure(["selfhost-bootstrap.py", "check-one-compiler.py", "check-complete-x86.py", "native_build_queue.py"], str(root))
        self.assertIn("selfhost-bootstrap.py", keep)
        self.assertIn("native_build_queue.py", keep)


class Git(unittest.TestCase):
    def test_tracked_and_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = lambda *a: subprocess.check_call(["git", "-C", tmp, *a], stdout=subprocess.DEVNULL)  # noqa: E731
            run("init", "-q")
            Path(tmp, "seed").mkdir()
            Path(tmp, "seed/a.kotoba").write_text("x")
            Path(tmp, "README.md").write_text("doc")
            run("add", ".")
            rows = G.tracked(tmp)
            self.assertEqual(sorted(r[2] for r in rows), ["README.md", "seed/a.kotoba"])
            out = Path(tmp, "out")
            env = dict(GITHUB_EVENT_NAME="push", GITHUB_OUTPUT=str(out), RUNNER_OS="Linux", RUNNER_ARCH="ARM64")
            G.main(["--job", "j", "--root", tmp], env)
            text = out.read_text()
            self.assertIn("always_run=true", text)
            self.assertIn("restore=false", text)
            self.assertIn("docs_only=false", text)
            self.assertIn("amu-ci-marker-v1-j-Linux-ARM64-main-", text)


GATE = "./.github/actions/ci-gate"
GUARD = "steps.gate.outputs.skip != 'true'"
# Reads only `needs` results, so it runs on a skip too: a skipped job must not hide a failed shard.
MAY_RUN_WHEN_SKIPPED = {("selfhost-native.yml", "qualify-x86_64",
                         "Require the shards and the runtime checks even when the gate skipped the steps (JUN-759)")}


def steps_by_job(text):
    """Job id to its steps' keys, read by line: the runners have no YAML module, and these workflows keep jobs at
    indent 2, `steps:` at 4, steps at 6 and step keys at 8. test_every_gate_is_seen fails if that stops holding."""
    jobs, job, steps = {}, None, None
    for line in text.split("\njobs:\n", 1)[1].splitlines():
        id_line = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
        if id_line:
            job, steps = id_line.group(1), None
        elif re.match(r"^    steps:\s*$", line):
            steps = jobs.setdefault(job, [])
        elif re.match(r"^    [^\s#]", line):
            steps = None
        elif steps is not None:
            if line.startswith("      - "):
                steps.append({})
                line = "        " + line[len("      - "):]
            key = re.match(r"^        ([a-z-]+):\s*(.*)$", line)
            if key:
                steps[-1].setdefault(key.group(1), key.group(2))
    return jobs


def gated_jobs(text):
    return [job for job, steps in steps_by_job(text).items() if any(s.get("uses") == GATE for s in steps)]


def unguarded(text):
    """(job, step) of each step after a job's gate that would still run when the gate skips."""
    found = []
    for job, steps in steps_by_job(text).items():
        uses = [s.get("uses") for s in steps]
        if GATE in uses:
            later = steps[uses.index(GATE) + 1:]
            found += [(job, s.get("name", s.get("uses"))) for s in later if GUARD not in s.get("if", "")]
    return found


class Guards(unittest.TestCase):
    head = ("on:\n  pull_request:\n    paths:\n      - 'seed/**'\njobs:\n  plain:\n    steps:\n      - name: no gate\n"
            "        run: a\n  gated:\n    needs:\n      - plain\n    steps:\n      - name: before\n        run: b\n"
            f"      - id: gate\n        uses: {GATE}\n        with:\n          job: gated\n")

    def test_guarded_steps_pass_in_every_form(self):
        for step in (f"      - name: s\n        if: {GUARD}\n        run: c\n",
                     f"      - name: s\n        if: always() && {GUARD} && (matrix.shard == 'core')\n        run: c\n",
                     f"      - if: success() && {GUARD}\n        uses: ./.github/actions/ci-save\n",
                     f"      - uses: actions/upload-artifact@x\n        if: {GUARD}\n        with:\n          name: n\n"):
            self.assertEqual(unguarded(self.head + step), [], step)

    def test_a_step_the_gate_would_not_stop_is_found(self):
        for condition in ("", "        if: matrix.target == 'x86_64'\n", "        if: always()\n",
                          "        if: steps.gate.outputs.hit != 'true'\n", "        if: steps.gate.outputs.skip == 'true'\n"):
            step = f"      - name: s\n{condition}        run: c\n"
            self.assertEqual(unguarded(self.head + step), [("gated", "s")], condition)

    def test_one_missing_guard_among_guarded_steps_is_found(self):
        steps = (f"      - name: a\n        if: {GUARD}\n        run: c\n      - name: b\n        run: |\n          d\n"
                 f"      - name: e\n        if: {GUARD}\n        run: f\n")
        self.assertEqual(unguarded(self.head + steps), [("gated", "b")])

    def test_only_steps_after_a_gate_count(self):
        self.assertEqual(unguarded(self.head), [])
        self.assertEqual(gated_jobs(self.head), ["gated"])
        text = self.head + "  later:\n    steps:\n      - name: other job\n        run: g\n"
        self.assertEqual(unguarded(text), [])

    def test_text_inside_a_run_block_is_not_a_step(self):
        step = f"      - name: s\n        if: {GUARD}\n        run: |\n          cat <<EOF\n          - name: x\n          EOF\n"
        self.assertEqual(unguarded(self.head + step), [])

    def test_job_keys_after_the_steps_end_them(self):
        step = f"      - name: s\n        if: {GUARD}\n        run: c\n    outputs:\n      - not-a-step: 1\n"
        self.assertEqual(unguarded(self.head + step), [])

    workflows = sorted((Path(__file__).resolve().parents[2] / ".github/workflows").glob("*.y*ml"))

    def test_every_gate_is_seen(self):
        total = 0
        for path in self.workflows:
            text = path.read_text()
            gates = len(re.findall(r"^\s+(?:- )?uses: " + re.escape(GATE) + r"\s*$", text, re.M))
            if gates:
                self.assertEqual(len(gated_jobs(text)), gates, path.name)
            total += gates
        self.assertGreater(total, 0)

    def test_every_later_step_stops_when_the_gate_skips(self):
        found = {(path.name, *row) for path in self.workflows if GATE in path.read_text()
                 for row in unguarded(path.read_text())}
        self.assertEqual(found, MAY_RUN_WHEN_SKIPPED)


if __name__ == "__main__":
    unittest.main()
