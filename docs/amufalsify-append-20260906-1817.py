#!/usr/bin/env python3
import datetime, io

path = "docs/codegen-coscientist.md"
with io.open(path, "r", encoding="utf-8") as f:
    txt = f.read()

now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M JST")
note = "2026-09-06 %s falsify tick: host busy (load1 %.1f/5 %.1f/15 %.1f, threshold 7.5, 15 users), measurement refused; NEXT H-C2 unchanged" % (now, 117.2, 109.9, 97.7)

# Find the H-C2 table row (line starting with '| H-C2 |')
idx = 0
lines = txt.split("\n")
target = -1
for i, ln in enumerate(lines):
    if ln.startswith("| H-C2 |"):
        target = i
        break
assert target >= 0, "H-C2 row not found"

row = lines[target]
# evidence cell is the last column; append before the next row boundary. The cell
# has no trailing pipe, so just append ' | <note>' unless row already ends oddly.
sep = " | " if not row.endswith("|") else " "
row_new = row.rstrip() + sep + note
lines[target] = row_new

out = "\n".join(lines)
with io.open(path, "w", encoding="utf-8") as f:
    f.write(out)

with io.open("/tmp/amufalsify-append.log", "w", encoding="utf-8") as f:
    f.write("appended H-C2 evidence at %s; row len %d -> %d\n" % (now, len(row), len(row_new)))
print("OK")