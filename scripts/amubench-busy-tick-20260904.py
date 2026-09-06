#!/usr/bin/env python3
"""amu-bench busy tick: append evidence to H-C2 row in docs/codegen-coscientist.md."""
import datetime, io, sys

path = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
now = "2026-09-04 23:29 JST"
tick = f" | {now} bench tick: host busy (load1 9.94, load5 16.42, load15 22.43, up 6 days, 11:28, 11 users), no measurement attempted; NEXT は H-C2 のまま"

with io.open(path, encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if line.startswith("| H-C2 |"):
        lines[i] = line.rstrip("\n") + tick + "\n"
        break
else:
    sys.exit("H-C2 row not found")

with io.open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("appended to line", i + 1)
