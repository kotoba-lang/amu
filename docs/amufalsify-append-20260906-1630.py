import io

path = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
with io.open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# line index 37 is the H-C2 row (line 38, 1-based)
idx = 37
row = lines[idx]
note = " | 2026-09-06 16:30 JST falsify tick: host busy (pre-run monitor load1 19.54; direct sysctl 23.56/23.72/18.38, up 1 day 9:13, threshold 7.5), no measurement attempted; NEXT は H-C2 のまま"
# H-C2 evidence cell is the last column; no trailing pipe; append at first '\n|' row boundary (i.e. end of this line)
if not row.endswith("\n"):
    row += "\n"
# append the note just before the final newline (last column, no closing pipe)
assert "H-C2" in row, "line 38 is not H-C2 row"
newrow = row[:-1] + note + "\n"
lines[idx] = newrow

with io.open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("OK appended. new len", len(newrow))