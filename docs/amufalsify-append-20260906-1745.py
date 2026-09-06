#!/usr/bin/env python3
import io, sys, datetime

path = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
entry = "2026-09-06 17:45 JST falsify tick: host busy (load1 43.97, load5 64.83, load15 89.88, 15 users, threshold 7.5), no measurement attempted; NEXT は H-C2 のまま"

with io.open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

out = []
found = False
for ln in lines:
    if ln.startswith("| H-C2 |") and not found:
        # strip trailing newline, append the new evidence segment directly
        stripped = ln.rstrip("\n")
        stripped = stripped.rstrip()
        stripped = stripped + " | " + entry
        out.append(stripped + "\n")
        found = True
    else:
        out.append(ln)

if not found:
    with io.open("/tmp/amu_append_status.txt", "w", encoding="utf-8") as f:
        f.write("ERROR: H-C2 row not found\n")
    sys.exit(1)

with io.open(path, "w", encoding="utf-8") as f:
    f.writelines(out)

with io.open("/tmp/amu_append_status.txt", "w", encoding="utf-8") as f:
    f.write("OK appended\n")