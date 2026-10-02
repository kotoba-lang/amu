#!/usr/bin/env python3
"""Run bench/embench/run_native_qualification.py UNCHANGED, except for one lookup: the upstream commit.

BOOTSTRAP-TOOL (python3, the runner's own language; never part of the seed's process tree).

The runner records `git rev-parse HEAD` of an embench-iot checkout (--upstream) and uses the checkout for nothing
else: the 19 ports it compiles are the repo's own bench/embench/ports. This host has no embench-iot checkout, and
fetching one is a download this run does not make. So this shim answers that single `git rev-parse HEAD` call (the
one whose cwd is the --upstream argument) with the commit DECLARED by the 2026-09-29 run (REPORT-20260929.md), and the
answer itself says so, e.g. "09c2ed8c... (declared from REPORT-20260929.md; no local embench-iot checkout, not
re-verified)". Every other subprocess call (otool, the compiler, the runner) is passed through untouched.

Usage: embench_declared_upstream.py <runner.py> <runner args...>   (pass --upstream <any existing directory>)
"""
import runpy
import subprocess
import sys

DECLARED = ("09c2ed8c3b7008c95d08b038de4a3f6dc103ed70 (declared from REPORT-20260929.md; "
            "no local embench-iot checkout, not re-verified)")

runner = sys.argv[1]
argv = sys.argv[1:]
upstream = argv[argv.index("--upstream") + 1]
real_run = subprocess.run


def run(args, *a, **kw):
    if list(args)[:3] == ["git", "rev-parse", "HEAD"] and str(kw.get("cwd")) == upstream:
        return subprocess.CompletedProcess(args, 0, stdout=DECLARED + "\n", stderr="")
    return real_run(args, *a, **kw)


subprocess.run = run
sys.argv = argv
runpy.run_path(runner, run_name="__main__")
