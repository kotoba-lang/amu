#!/usr/bin/env python3
"""Report which open PRs form a dependent stack and can be combined (JUN-818, measure 3).

Default (and `report`): read-only. Lists PR stacks (PR B is stacked on PR A when B's base branch is A's head
branch), whether each stack is mechanically combinable (every PR's head contains its base PR's head, so the
top PR already carries the whole stack), and which independent PRs touch the same files (pins in particular),
so they would conflict in the merge queue.

`combine TOP_PR [--push] [--open-pr]` is the only mutating command and runs only when invoked: it creates a
local branch `batch/pr-<TOP>` at the top PR's head and, with --push/--open-pr, pushes it and opens ONE new PR
against the stack root's base branch. It never closes, retargets, edits or merges any existing PR; the owner
of the stack closes the superseded PRs after the combined PR lands.
"""
import argparse
import json
import subprocess
import sys

FIELDS = "number,title,headRefName,baseRefName,headRefOid,files,mergeStateStatus,isDraft,author"
PIN_PREFIXES = ("bin/", "native-product.json", "seed/bootstrap/", "seed/cdci/", "seed/compiler-core.json",
                "seed/adoption-", "examples/foundation-starter/")


def sh(*cmd, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode:
        raise SystemExit(f"{' '.join(cmd)}: {r.stderr.strip()}")
    return r


def load(repo):
    return json.loads(sh("gh", "pr", "list", "--repo", repo, "--state", "open", "--limit", "200",
                         "--json", FIELDS).stdout)


def stacks(prs):
    """Chains bottom to top. A PR whose base branch is another open PR's head is stacked on it."""
    by_head = {p["headRefName"]: p for p in prs}
    child = {}
    for p in prs:
        parent = by_head.get(p["baseRefName"])
        if parent is not None and parent["number"] != p["number"]:
            child.setdefault(parent["number"], []).append(p)
    out = []
    for p in prs:
        if p["baseRefName"] in by_head:
            continue  # not a stack root
        chain, cur = [p], p
        while len(child.get(cur["number"], [])) == 1:
            cur = child[cur["number"]][0]
            chain.append(cur)
        branched = child.get(cur["number"], [])
        if len(chain) > 1 or branched:
            out.append((chain, branched))
    return out


def is_pin(path):
    return path.startswith(PIN_PREFIXES)


def file_set(p):
    return {f["path"] for f in p.get("files", [])}


def overlaps(prs, in_stack):
    rows = []
    free = [p for p in prs if p["number"] not in in_stack]
    for i, a in enumerate(free):
        for b in free[i + 1:]:
            common = file_set(a) & file_set(b)
            if common:
                pins = sorted(f for f in common if is_pin(f))
                rows.append((a["number"], b["number"], len(common), pins))
    return rows


def combinable(chain, git=sh, remote="origin"):
    """True when each PR's head contains the previous PR's head (needs the heads fetched)."""
    for lower, upper in zip(chain, chain[1:]):
        r = git("git", "merge-base", "--is-ancestor", lower["headRefOid"], upper["headRefOid"], check=False)
        if r.returncode:
            return False, f"#{upper['number']} does not contain the head of #{lower['number']} (needs a merge or rebase by its owner)"
    states = {p["mergeStateStatus"] for p in chain}
    if "DIRTY" in states:
        return False, "a PR in the stack has merge conflicts with its base"
    return True, "top PR head already contains every lower PR"


def report(prs, git=sh):
    lines = []
    in_stack = set()
    for chain, branched in stacks(prs):
        for p in chain:
            in_stack.add(p["number"])
        ok, why = combinable(chain, git)
        nums = " <- ".join(f"#{p['number']}" for p in chain)
        lines.append(f"stack {nums}  (root base: {chain[0]['baseRefName']})")
        lines.append(f"  combinable: {'yes' if ok else 'no'}: {why}")
        if branched:
            lines.append("  note: top PR has several children: " + ", ".join(f"#{p['number']}" for p in branched))
        drafts = [p["number"] for p in chain if p["isDraft"]]
        if drafts:
            lines.append("  drafts: " + ", ".join(f"#{n}" for n in drafts))
        pins = sorted({f for p in chain for f in file_set(p) if is_pin(f)})
        lines.append(f"  pin files touched: {len(pins)}")
    if not lines:
        lines.append("no stacked PRs")
    lines.append("")
    rows = overlaps(prs, in_stack)
    lines.append("independent PRs sharing files (queue conflict risk):")
    for a, b, n, pins in rows:
        lines.append(f"  #{a} x #{b}: {n} common files" + (f", {len(pins)} pin files" if pins else ""))
    if not rows:
        lines.append("  none")
    return "\n".join(lines)


def combine(prs, top, repo, push, open_pr):
    by_num = {p["number"]: p for p in prs}
    if top not in by_num:
        raise SystemExit(f"PR #{top} is not open")
    chain = None
    for c, _ in stacks(prs):
        if c[-1]["number"] == top:
            chain = c
    if chain is None:
        raise SystemExit(f"#{top} is not the top of a linear stack; run `report`")
    sh("git", "fetch", "origin", *[f"pull/{p['number']}/head" for p in chain])
    ok, why = combinable(chain)
    if not ok:
        raise SystemExit("not combinable: " + why)
    branch = f"batch/pr-{top}"
    sh("git", "branch", "-f", branch, chain[-1]["headRefOid"])
    print(f"created local branch {branch} at {chain[-1]['headRefOid'][:12]} covering " +
          ", ".join(f"#{p['number']}" for p in chain))
    if not (push or open_pr):
        print("not pushed (pass --push --open-pr to publish)")
        return
    sh("git", "push", "origin", f"{branch}:refs/heads/{branch}")
    if open_pr:
        base = chain[0]["baseRefName"]
        body = ("Combined stack " + ", ".join(f"#{p['number']}" for p in chain) +
                f" (head of #{top}). Original PRs are untouched; their owners close them after this lands.\n\n"
                "🤖 Generated with [Claude Code](https://claude.com/claude-code)")
        print(sh("gh", "pr", "create", "--repo", repo, "--base", base, "--head", branch,
                 "--title", f"batch: combine stack ending at #{top}", "--body", body).stdout.strip())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", default="kotoba-lang/amu")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("report")
    c = sub.add_parser("combine")
    c.add_argument("top", type=int)
    c.add_argument("--push", action="store_true")
    c.add_argument("--open-pr", action="store_true")
    args = ap.parse_args(argv)
    prs = load(args.repo)
    if args.cmd == "combine":
        combine(prs, args.top, args.repo, args.push, args.open_pr)
    else:
        sh("git", "fetch", "-q", "origin", *[f"pull/{p['number']}/head" for p in prs], check=False)
        print(report(prs))


if __name__ == "__main__":
    sys.exit(main())
