#!/usr/bin/env python3
"""Input-hash gate for the native CI jobs (JUN-759). Scheduling only, no verdict.

A job asks this script two questions before its heavy steps:

* docs_only: does the pull request / merge-group entry change only inert files
  (documentation, other workflows)? Then the native verdict of its base applies
  unchanged and the job reports success without running its steps. The required
  check still runs and reports under its own name.
* key / restore_keys: the cache key for a marker or a derived-artifact cache,
  made of a content hash of the job's inputs (every tracked file except the
  inert ones) plus the runner arch and the tier. Pushes to main, the schedule
  and manual dispatch never skip: they run the full suite as the safety net and
  only write markers/caches. The caller saves a marker only after a job passed.

Two kinds:
  marker  key over the whole tree (minus inert files); a hit means this exact
          tree already passed this job on main/schedule (or earlier in the
          same ref), so the job may skip.
  derive  key over the derivation inputs only: the tree minus inert files minus
          the gate-only scripts (scripts/seed/check-*.py, test_*.py) that the
          derivation scripts do not reference. A hit restores the exact
          derived compiler artifacts instead of re-deriving them. Gate scripts
          that run on the restored artifacts are never cached.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request

VERSION = "v1"
# Files whose content no native job reads. docs/evidence is read by gates and is NOT inert; seed/README.md etc. are
# under seed/ and are NOT inert; top-level Markdown is read by no script.
INERT = (
    re.compile(r"^[^/]*\.md$"),
    re.compile(r"^LICENSE$"),
    re.compile(r"^docs/(?!evidence/).*\.md$"),
    re.compile(r"(^|/)\.DS_Store$"),
    re.compile(r"^\.github/dependabot\.yml$"),
    re.compile(r"^\.github/workflows/(?!selfhost-native\.yml$)[^/]+$"),
)
TIERS = ("pr", "main", "full")
SEED = "scripts/seed/"


def is_inert(path):
    return any(rule.search(path) for rule in INERT)


def tracked(root="."):
    raw = subprocess.check_output(["git", "-C", root, "ls-files", "-s", "-z"])
    rows = []
    for item in raw.split(b"\0"):
        if not item:
            continue
        meta, path = item.split(b"\t", 1)
        mode, blob, _stage = meta.decode().split()
        rows.append((mode, blob, path.decode()))
    return rows


def local_refs(text, files, stems, own):
    found = set()
    for match in re.finditer(r"[A-Za-z0-9_\-]+\.py", text):
        if match.group(0) in files and match.group(0) != own:
            found.add(match.group(0))
    for match in re.finditer(r"^\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_]*)", text, re.M):
        name = stems.get(match.group(1))
        if name and name != own:
            found.add(name)
    return found


def closure(roots, root="."):
    """The scripts/seed Python files transitively mentioned by name from the roots (a superset of the real imports)."""
    directory = os.path.join(root, SEED)
    files = {f for f in os.listdir(directory) if f.endswith(".py")}
    stems = {f[:-3]: f for f in files}
    seen, pending = set(), [r for r in roots if r]
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        if name not in files:
            raise SystemExit("unknown derivation root script: " + name)
        seen.add(name)
        with open(os.path.join(directory, name), encoding="utf-8", errors="replace") as stream:
            pending += sorted(local_refs(stream.read(), files, stems, name))
    return seen


def gate_only(path, keep):
    if not path.startswith(SEED) or "/" in path[len(SEED):]:
        return False
    name = path[len(SEED):]
    return (name.startswith("check-") or name.startswith("test_")) and name.endswith(".py") and name not in keep


def tree_hash(rows, kind, keep=frozenset()):
    digest = hashlib.sha256()
    digest.update((VERSION + "\n" + kind + "\n").encode())
    count = 0
    for mode, blob, path in sorted(rows, key=lambda r: r[2]):
        if is_inert(path) or (kind == "derive" and gate_only(path, keep)):
            continue
        digest.update(f"{mode} {blob} {path}\n".encode())
        count += 1
    return digest.hexdigest(), count


def tier_of(event):
    return {"pull_request": "pr", "merge_group": "pr", "push": "main"}.get(event, "full")


def accepted(tier):
    """A result from this tier or a stronger one may stand in for the requested tier."""
    return TIERS[TIERS.index(tier):] if tier != "pr" else TIERS


def safe(text):
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", text).strip("-")


def keys(kind, job, arch, tier, digest):
    base = f"amu-ci-{kind}-{VERSION}-{safe(job)}-{safe(arch)}"
    exact = f"{base}-{tier}-{digest}"
    others = [f"{base}-{t}-{digest}" for t in accepted(tier) if t != tier]
    return exact, others


def changed_files(repo, base, head, token, opener=urllib.request.urlopen):
    """Files changed by head relative to base, or None when unknown (then nothing is skipped)."""
    names = []
    for page in range(1, 4):
        url = f"https://api.github.com/repos/{repo}/compare/{base}...{head}?per_page=100&page={page}"
        request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                                       "Authorization": "Bearer " + token,
                                                       "X-GitHub-Api-Version": "2022-11-28"})
        try:
            with opener(request, timeout=30) as response:
                body = json.load(response)
        except Exception as error:  # an unknown answer never skips
            print("compare unavailable:", error, file=sys.stderr)
            return None
        files = body.get("files") or []
        for row in files:
            names.append(row["filename"])
            if row.get("previous_filename"):
                names.append(row["previous_filename"])
        if len(files) < 100:
            return names if body.get("total_commits", 1) > 0 else None
    return None


def docs_only(event, env, opener=urllib.request.urlopen):
    if event == "pull_request":
        base, head = env.get("PR_BASE_SHA"), env.get("PR_HEAD_SHA")
    elif event == "merge_group":
        base, head = env.get("MG_BASE_SHA"), env.get("MG_HEAD_SHA")
    else:
        return False
    if not (base and head and env.get("GITHUB_REPOSITORY") and env.get("GITHUB_TOKEN")):
        return False
    names = changed_files(env["GITHUB_REPOSITORY"], base, head, env["GITHUB_TOKEN"], opener)
    return bool(names) and all(is_inert(name) for name in names)


def emit(values, path):
    lines = "".join(f"{k}={v}\n" for k, v in values.items())
    sys.stdout.write(lines)
    if path:
        with open(path, "a", encoding="utf-8") as stream:
            stream.write(lines)


def main(argv=None, env=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", required=True)
    parser.add_argument("--kind", choices=("marker", "derive"), default="marker")
    parser.add_argument("--roots", default="", help="derive: comma separated scripts/seed/*.py that start the derivation")
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    env = os.environ if env is None else env
    event = env.get("GITHUB_EVENT_NAME", "")
    tier = tier_of(event)
    keep = frozenset(closure([r.strip() for r in args.roots.split(",")], args.root)) if args.kind == "derive" else frozenset()
    digest, count = tree_hash(tracked(args.root), args.kind, keep)
    arch = (env.get("RUNNER_OS", "Linux") + "-" + env.get("RUNNER_ARCH", "X64"))
    exact, others = keys(args.kind, args.job, arch, tier, digest)
    inert = docs_only(event, env)
    always = tier != "pr"
    path = env.get("GITHUB_OUTPUT")
    emit(dict(docs_only=str(inert).lower(), always_run=str(always).lower(), tier=tier, inputs=count, digest=digest,
              key=exact, restore="false" if (inert or always) else "true"), path)
    # restore-keys is multi-line: write it as a delimited block
    if path:
        with open(path, "a", encoding="utf-8") as stream:
            stream.write("restore_keys<<EOF_KEYS\n" + "\n".join(others) + "\nEOF_KEYS\n")
    print("restore_keys:", others)


if __name__ == "__main__":
    main()
