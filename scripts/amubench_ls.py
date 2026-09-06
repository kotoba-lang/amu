#!/usr/bin/python3
import os, subprocess
REPO = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu"
OUT = "/private/tmp/amub_ls.txt"
lines = []
b = os.path.join(REPO, "bench", "runtime-comparison")
for n in sorted(os.listdir(b)):
    lines.append(n)
# docs/performance.md mention of jb
logp = os.path.join(REPO, "docs", "performance.md")
if os.path.exists(logp):
    t = open(logp).read()
    i = t.rfind("jb_imod")
    lines.append("perf.md last jb idx: %d" % i)
    if i >= 0:
        lines.append(t[max(0,i-800):i+800])
open(OUT, "w").write("\n".join(lines) + "\n")
print("ok")
