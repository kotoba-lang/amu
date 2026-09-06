#!/usr/bin/env python3
# Append host-busy refusal entry to H-C2 evidence cell (last table column, no trailing pipe).
# Convention: append at first '\n| ' row boundary without requiring closing '|'.
import datetime, io

P = "docs/codegen-coscientist.md"
entry = (" 2026-09-06 17:33 JST falsify tick: host busy (load1 153.84, load5 138.83, "
         "load15 116.85 at 17:33 pre-run, sysctl 153.84/138.83/116.85, up 1 day 10:16, "
         "13 users, threshold 7.5), no measurement attempted; NEXT は H-C2 のまま")

with io.open(P, "r", encoding="utf-8") as f:
    lines = f.readlines()

# H-C2 row is line index 37 (1-based 38)
idx = None
for i, ln in enumerate(lines):
    if ln.startswith("| H-C2 |"):
        idx = i
        break
if idx is None:
    raise SystemExit("H-C2 row not found")

row = lines[idx]
# row is a single markdown line; evidence is the last cell. Append before the final newline.
if row.endswith("\n"):
    row = row[:-1]
row += entry + "\n"
lines[idx] = row

with io.open(P, "w", encoding="utf-8") as f:
    f.writelines(lines)

# status log
with io.open("/tmp/amufalsify_1733.log", "w", encoding="utf-8") as f:
    f.write("appended to H-C2 row ok; new line length = %d\n" % len(row))