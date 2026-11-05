#!/usr/bin/env python3
"""Runner capacity monitor and hosted fail-over for ADR 0406. Read-only unless --apply.

Needs a repository-scoped GH_TOKEN with Administration read (and write for --apply) in the environment.
Decision rule (pure function `decide`, unit-tested): fall back to hosted when a needed label has no online
runner, or when a queued self-hosted job has waited longer than --max-wait seconds.
"""
import argparse, json, subprocess, sys, time
from datetime import datetime, timezone

REPO = "kotoba-lang/amu"
NEEDED = {"selfhosted-arm": ["amu-linux-arm64", "amu-macos-arm64"],
          "selfhosted": ["amu-linux-arm64", "amu-macos-arm64", "amu-linux-x86_64"]}


def decide(profile, online_labels, queued_waits, max_wait=120):
    """Return (new_profile, reason). Never promotes back to self-hosted."""
    if profile not in NEEDED:
        return profile, "not self-hosted"
    missing = [l for l in NEEDED[profile] if l not in online_labels]
    if missing:
        return "hosted", f"no online runner for {', '.join(missing)}"
    slow = [w for w in queued_waits if w > max_wait]
    if slow:
        return "hosted", f"{len(slow)} self-hosted job(s) queued > {max_wait}s (max {max(slow):.0f}s)"
    return profile, "ok"


def gh(*args):
    return json.loads(subprocess.check_output(["gh", *args]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--max-wait", type=int, default=120)
    a = ap.parse_args()
    rows = gh("api", f"repos/{REPO}/actions/runners?per_page=100")["runners"]
    online = {l["name"] for r in rows if r["status"] == "online" for l in r["labels"]}
    var = subprocess.run(["gh", "variable", "get", "AMU_RUNNER_PROFILE", "-R", REPO],
                         capture_output=True, text=True).stdout.strip()
    waits, now = [], datetime.now(timezone.utc)
    for run in gh("api", f"repos/{REPO}/actions/runs?status=queued&per_page=50")["workflow_runs"]:
        for j in gh("api", f"repos/{REPO}/actions/runs/{run['id']}/jobs?per_page=100")["jobs"]:
            if j["status"] == "queued" and any(l.startswith("amu-") for l in j["labels"]):
                waits.append((now - datetime.fromisoformat(j["created_at"].replace("Z", "+00:00"))).total_seconds())
    new, why = decide(var, online, waits, a.max_wait)
    print(f"profile={var or '(unset)'} online={sorted(online)} queued_self_hosted={len(waits)} -> {new}: {why}")
    if new != var and a.apply:
        subprocess.check_call(["gh", "variable", "set", "AMU_RUNNER_PROFILE", "--body", new, "-R", REPO])
        print("variable set; re-run stuck jobs with: gh run rerun <id> --failed")
    elif new != var:
        print("dry-run: pass --apply to set the variable")


if __name__ == "__main__":
    main()
