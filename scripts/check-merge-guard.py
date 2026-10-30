#!/usr/bin/env python3
"""Positive and negative controls for scripts/merge-guard.py (JUN-263).

Builds throwaway repositories and requires the guard to find the amu#1339 pattern and stay
quiet on ordinary PRs:

  clean         a PR that adds a file                                   -> clean
  own-delete    a PR whose own commit deletes a file                    -> clean
  incident      the branch merges main, then `git revert -m 1` of that
                merge; merging it would delete main's new files         -> revert-of-main-merge
                (the revert is itself a non-merge commit that deletes
                them, so the deletion check counts them as the PR's own)
  bad-resolve   the branch merges main and drops main's new file inside
                the merge resolution                                    -> merge-side deletion
  mass          a PR deleting 600 lines in its own commit               -> mass deletion only,
                                                                           acknowledged when allowed
Each finding case also runs in fail mode, which must exit 1; warn mode must exit 0.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

GUARD = Path(__file__).resolve().parent / "merge-guard.py"
ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
           GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid", GIT_CONFIG_GLOBAL="/dev/null")


def sh(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, env=ENV, check=True, capture_output=True, text=True).stdout.strip()


def commit(repo, msg, files=(), delete=()):
    for name, text in files:
        (repo / name).write_text(text)
        sh(repo, "add", name)
    for name in delete:
        sh(repo, "rm", "-q", name)
    sh(repo, "commit", "-q", "-m", msg)
    return sh(repo, "rev-parse", "HEAD")


def repo_with_base(root):
    repo = Path(root)
    sh(repo, "init", "-q", "-b", "main")
    commit(repo, "base", [("a.txt", "a\n"), ("big.txt", "".join(f"line {i}\n" for i in range(600)))])
    return repo


def guard(repo, base, head, **env):
    r = subprocess.run([sys.executable, str(GUARD)], cwd=repo, capture_output=True, text=True,
                       env=dict(ENV, MERGE_GUARD_BASE=base, MERGE_GUARD_HEAD=head, **env))
    return r.returncode, r.stdout


def case(name, build, want, **env):
    with tempfile.TemporaryDirectory() as d:
        repo = repo_with_base(d)
        base, head = build(repo)
        code, text = guard(repo, base, head, **env)
        got = sorted(k for k, marker in [("deletion", "PR's own non-merge commits never deleted"),
                                         ("revert", "restores the pre-merge state"),
                                         ("mass", "lines against the base (informational")]
                     if marker in text and "WOULD-FAIL" in text.split(marker)[0].rsplit("\n", 1)[-1])
        assert code == 0 and got == sorted(want), (name, code, got, text)
        if want:
            fcode, _ = guard(repo, base, head, MERGE_GUARD_MODE="fail", **env)
            assert fcode == 1, (name, "fail mode must exit 1", fcode)
        print("PASS", name, got)


def clean(repo):
    sh(repo, "checkout", "-q", "-b", "pr")
    head = commit(repo, "add", [("b.txt", "b\n")])
    return sh(repo, "rev-parse", "main"), head


def own_delete(repo):
    sh(repo, "checkout", "-q", "-b", "pr")
    head = commit(repo, "drop a", delete=["a.txt"])
    return sh(repo, "rev-parse", "main"), head


def incident(repo):
    sh(repo, "checkout", "-q", "-b", "pr")
    commit(repo, "feature", [("feature.txt", "f\n")])
    sh(repo, "checkout", "-q", "main")
    commit(repo, "main work", [("m1.txt", "m1\n"), ("m2.txt", "m2\n")])
    sh(repo, "checkout", "-q", "pr")
    sh(repo, "merge", "-q", "--no-edit", "main")
    sh(repo, "revert", "--no-edit", "-m", "1", "HEAD")
    return sh(repo, "rev-parse", "main"), sh(repo, "rev-parse", "HEAD")


def bad_resolve(repo):
    sh(repo, "checkout", "-q", "-b", "pr")
    commit(repo, "feature", [("feature.txt", "f\n")])
    sh(repo, "checkout", "-q", "main")
    commit(repo, "main work", [("m1.txt", "m1\n")])
    sh(repo, "checkout", "-q", "pr")
    sh(repo, "merge", "-q", "--no-commit", "main")
    sh(repo, "rm", "-q", "-f", "m1.txt")
    sh(repo, "commit", "-q", "--no-edit")
    return sh(repo, "rev-parse", "main"), sh(repo, "rev-parse", "HEAD")


def mass(repo):
    sh(repo, "checkout", "-q", "-b", "pr")
    head = commit(repo, "trim big", [("big.txt", "")])
    return sh(repo, "rev-parse", "main"), head


case("clean", clean, [])
case("own-delete", own_delete, [])
case("incident", incident, ["revert"])
case("bad-resolve", bad_resolve, ["deletion"])
case("mass", mass, ["mass"])
case("mass-acknowledged", mass, [], MERGE_GUARD_ALLOW_MASS_DELETION="true")
print("PASS_MERGE_GUARD_CONTROLS")
