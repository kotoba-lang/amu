#!/usr/bin/env python3
import io

path = "docs/codegen-coscientist.md"
with io.open(path, "r", encoding="utf-8") as f:
    text = f.read()

note = " | 2026-09-06 15:30 JST falsify tick: host busy (load1 11.42, load5 14.00, load15 24.70, up 1 day 8:13, threshold 7.5), no measurement attempted; NEXT は H-C2 のまま"

# Append only once. We target the H-C2 row's evidence cell. Because the cell
# is huge and reused, do a guarded append on the row marker.
marker_start = "| H-C2 | the remaining ~4.4% vs Clang on `kernel` after H-C"
idx = text.find(marker_start)
if idx == -1:
    raise SystemExit("H-C2 row not found")

# Insert the note just before the newline that terminates the H-C2 row.
row_end = text.find("\n", idx)
line = text[idx:row_end]
if note.strip() in line:
    raise SystemExit("note already present")
line = line.rstrip()
if not line.endswith("|"):
    line += " |"
new_line = line + note

text = text[:idx] + new_line + text[row_end:]
with io.open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("appended")