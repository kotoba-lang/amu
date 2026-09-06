#!/usr/bin/python3
import os, subprocess
REPO = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu"
OUT = "/private/tmp/amub_adr.txt"
lines = []
adr = os.path.join(REPO, "docs", "adr")
names = sorted(os.listdir(adr))
lines.extend(names[-15:])
for n in names:
    if n.startswith("0335") or n.startswith("0339"):
        lines.append("=== " + n + " ===")
        lines.append(open(os.path.join(adr, n)).read()[:3500])
open(OUT, "w").write("\n".join(lines) + "\n")
print("ok")
