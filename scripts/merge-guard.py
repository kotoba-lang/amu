#!/usr/bin/env python3
"""merge-guard: report when a PR's merge into the base branch would destroy main-side work.

Written after the 2026-10-20 incident (amu#1339): a bot resolved conflicts with --theirs,
"recovered" with `git revert -m 1` of its own main merges, and the next merge deleted 408
main-side files (128,777 lines). See JUN-263. This is the Python port of the retired
scripts/merge-guard.mjs (amu#1439); git and Python only, no Node.

ADVISORY BY DEFAULT (owner decision, 2026-10-21): refactoring flows rewrite and delete large
trees and merge main repeatedly, and a blocking gate gets in their way. The default mode
prints findings and always exits 0; nothing here stops a merge. Set MERGE_GUARD_MODE=fail to
make the findings block instead.

Three findings:

1. Merge-side deletion. Every file the merge result deletes relative to the base should also
   be deleted by the PR's own non-merge commits. A deletion that only appears in the merge
   result is merge-resolution damage, not intent.
2. Revert-of-main-merge. A non-merge commit whose tree restores the pre-merge state of a merge
   that brought main into a diverged branch (`git revert -m 1` of such a merge) records the
   inverse of main's work as the branch's own change. Detected structurally, not by message:
   commit C is flagged when a main-merge R before it has parents [A, B] with B on the base
   history and A off it, and every path R touched holds A's blob at C. Reverting a merged PR
   (both parents on the base history) is the normal revert-PR route and is never flagged.
3. Mass deletion. More than MERGE_GUARD_MAX_DELETED_LINES (500) deleted lines in the merge
   result. In fail mode, intentional large deletions set MERGE_GUARD_ALLOW_MASS_DELETION=true.

Usage: MERGE_GUARD_BASE=<sha> MERGE_GUARD_HEAD=<sha> python3 scripts/merge-guard.py
(In CI the workflow passes the pull request's base and head SHAs.)
"""
import os
import re
import subprocess
import sys


def git(*args, check=True):
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise subprocess.CalledProcessError(r.returncode, args, r.stdout, r.stderr)
    return r


def out(*args):
    return git(*args).stdout.strip()


def lines(*args):
    text = out(*args)
    return [] if text == "" else text.split("\n")


def is_ancestor(a, d):
    return git("merge-base", "--is-ancestor", a, d, check=False).returncode == 0


def blob(rev, path):
    r = git("rev-parse", f"{rev}:{path}", check=False)
    return r.stdout.strip() if r.returncode == 0 else "(absent)"


def main():
    base, head = os.environ.get("MERGE_GUARD_BASE"), os.environ.get("MERGE_GUARD_HEAD")
    mode = "fail" if os.environ.get("MERGE_GUARD_MODE", "warn") == "fail" else "warn"
    max_deleted = int(os.environ.get("MERGE_GUARD_MAX_DELETED_LINES", "500"))
    allow_mass = os.environ.get("MERGE_GUARD_ALLOW_MASS_DELETION", "false") == "true"
    if not base or not head:
        print("merge-guard: MERGE_GUARD_BASE and MERGE_GUARD_HEAD are required", file=sys.stderr)
        return 2
    findings, warnings = [], []
    merge_base = out("merge-base", base, head)
    if is_ancestor(head, base):
        print(f"merge-guard: {head} is already contained in {base}; nothing to merge")
        return 0

    # git merge-tree --write-tree prints the merged tree OID first; it exits 1 on conflicts
    # but still prints a tree OID followed by the conflict information.
    r = git("merge-tree", "--write-tree", base, head, check=False)
    rows = r.stdout.split("\n")
    tree = rows[0].strip()
    conflicts = [l for l in rows[1:] if l.strip()]
    if not re.fullmatch(r"[0-9a-f]{40}", tree):
        findings.append(f"merge-tree could not compute a merge result for {base}..{head}: {r.stdout[:500]}{r.stderr[:500]}")
        tree = None
    elif r.returncode != 0:
        # A conflicted PR cannot merge anyway; GitHub reports it as dirty. A note, not a finding.
        warnings.append("the PR conflicts with the base branch; the deletion checks below cover "
                        f"the merge-tree result only ({' | '.join(conflicts[:10])})")

    if tree:
        merge_deleted = set(lines("diff", "--diff-filter=D", "--name-only", base, tree))
        own_deleted = set(lines("log", "--no-merges", "--diff-filter=D", "--name-only", "--format=", f"{base}..{head}"))
        undeleted = sorted(merge_deleted - own_deleted)
        if undeleted:
            findings.append(f"the merge deletes {len(undeleted)} file(s) that the PR's own non-merge commits never deleted "
                            f"(merge-resolution damage): {', '.join(undeleted[:20])}{', …' if len(undeleted) > 20 else ''}")

        # Merges in the PR's line that brought the base history into a diverged branch.
        main_merges = []
        for sha in lines("rev-list", "--merges", f"{base}..{head}"):
            parts = out("rev-list", "--parents", "-n", "1", sha).split(" ")
            if len(parts) == 3 and is_ancestor(parts[2], base) and not is_ancestor(parts[1], base):
                main_merges.append((sha, parts[1], lines("diff", "--name-only", parts[1], sha)))
        for c in lines("rev-list", "--no-merges", f"{base}..{head}"):
            if len(out("rev-list", "--parents", "-n", "1", c).split(" ")) != 2:
                continue
            for sha, a, paths in main_merges:
                # Only a commit after the merge can invert it, on every path the merge touched.
                if not paths or not is_ancestor(sha, c):
                    continue
                if all(blob(a, p) == blob(c, p) for p in paths):
                    findings.append(f"commit {c[:12]} restores the pre-merge state of main-merge {sha[:12]} "
                                    f"on all {len(paths)} path(s) it touched: a revert -m 1 of a main merge records the "
                                    "inverse of main's work as this branch's own change. Recover with git reset to a new "
                                    "branch from the pre-merge tip, or redo the merge with a faithful port.")
                    break
            if re.search(r"revert -m 1", out("log", "-1", "--format=%B", c), re.I):
                warnings.append(f'commit {c[:12]} explains a "revert -m 1" in its body; if it inverts a main merge '
                                "partially, the structural check above can miss it — review by hand")

        deleted_lines = 0
        for row in lines("diff", "--numstat", base, tree):
            d = row.split("\t")[1]
            if d != "-":
                deleted_lines += int(d)
        if deleted_lines > max_deleted:
            message = (f"the merge result deletes {deleted_lines} lines against the base (informational limit "
                       f"{max_deleted}). Large refactors do this on purpose; in fail mode set "
                       "MERGE_GUARD_ALLOW_MASS_DELETION=true in .github/workflows/merge-guard.yml to acknowledge.")
            (warnings.append(message + " (acknowledged)") if allow_mass else findings.append(message))

        print(f"merge-guard: base {base[:12]} head {head[:12]} merge-base {merge_base[:12]} merge-tree {tree[:12]} "
              f"deleted-files={len(merge_deleted)} own-deleted-files={len(own_deleted)} "
              f"deleted-lines={deleted_lines} main-merges={len(main_merges)} mode={mode}")

    for w in warnings:
        print(f"merge-guard note: {w}")
    for f in findings:
        print(f"merge-guard: {'FAIL' if mode == 'fail' else 'WOULD-FAIL'}: {f}")
    if findings and mode == "fail":
        return 1
    print(f"merge-guard: {len(findings)} finding(s) reported, not blocking (MERGE_GUARD_MODE=warn)"
          if findings else "merge-guard: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
