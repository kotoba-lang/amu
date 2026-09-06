#!/usr/bin/env python3
import io, sys

path = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
entry = " | 2026-09-06 16:49 JST falsify tick: host busy (load1 71.11, load5 42.41, load15 31.26, up 1 day 9:28, 13 users, threshold 7.5), no measurement attempted; NEXT は H-C2 のまま"

with io.open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

target_idx = None
for i, line in enumerate(lines):
    if line.startswith("| H-C2 |"):
        target_idx = i
        break

if target_idx is None:
    print("ERROR: H-C2 row not found", file=sys.stderr)
    sys.exit(2)

lines[target_idx] = lines[target_idx].rstrip("\n") + entry + "\n"

with io.open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("OK: appended host-busy evidence to H-C2 row line", target_idx + 1)