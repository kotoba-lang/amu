#!/usr/bin/env python3
"""amu-falsify tick 2026-09-05 23:45 JST: host busy — append evidence only (H-C2)."""
import subprocess, re, time, os

REPO = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu"
DOC = os.path.join(REPO, "docs", "codegen-coscientist.md")
THRESHOLD = 7.5

def loadavg():
    a = open("/proc/loadavg").read().split() if os.path.exists("/proc/loadavg") else None
    # macOS
    out = subprocess.run(["sysctl", "-n", "vm.loadavg"], capture_output=True, text=True).stdout
    nums = re.findall(r"[\d.]+", out)
    return float(nums[0]), float(nums[1]), float(nums[2])

l1, l5, l15 = loadavg()
uptime = subprocess.run(["uptime"], capture_output=True, text=True).stdout.strip()

stamp = time.strftime("%Y-%m-%d %H:%M JST", time.localtime())
if l1 > THRESHOLD:
    entry = (f" | {stamp} falsify tick: host busy (load1 {l1:.2f}, load5 {l5:.2f}, "
             f"load15 {l15:.2f}, {uptime}, threshold {THRESHOLD}), no measurement attempted; "
             "NEXT は H-C2 のまま")
    s = open(DOC).read()
    old = "| open — generate from an instruction-order diff | pending;"
    assert s.count(old) == 1, "H-C2 anchor not found"
    open(DOC, "w").write(s.replace(old, entry + " | open — generate from an instruction-order diff | pending;"))
    print(f"appended: {entry}")
else:
    print(f"host quiet (load1 {l1:.2f}) — measurement would be allowed, but this run is busy-refusal only")
