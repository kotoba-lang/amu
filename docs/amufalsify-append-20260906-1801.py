#!/usr/bin/env python3
# H-C2 evidence append: host busy, no measurement.
# Convention: evidence cell is LAST column (no trailing pipe); insert at first '\n| ' row boundary.
import sys, datetime
path = "docs/codegen-coscientist.md"
stamp = "2026-09-06 18:01 JST falsify tick: host busy (load1 81.42, load5 78.31, load15 79.62, up 1 day 10:43, 14 users, threshold 7.5), no measurement attempted; NEXT は H-C2 のまま"
with open(path) as f:
    txt = f.read()
row = next(l for l in txt.split("\n") if l.startswith("| H-C2 "))
assert row.rstrip().endswith("|") is False or True  # cell may end without pipe
# find the boundary after the H-C2 row (first '\n| ' following the last H-C2 row)
idx = txt.find("| H-C2 ")
assert idx != -1
# find the end of the H-C2 row = next line start "--" or "| H-"
tail_idx = txt.find("\n| H-", idx + 1)
if tail_idx == -1:
    # locate end of this row: next line that begins with '|' or '##'
    rest = txt[idx:]
    nl = rest.find("\n")
    tail_idx_full = idx + nl
else:
    tail_idx_full = tail_idx
new = txt[:tail_idx_full] + " | " + stamp + txt[tail_idx_full:]
with open(path, "w") as f:
    f.write(new)
print("appended to H-C2")