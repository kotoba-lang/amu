import io, sys

path = "docs/codegen-coscientist.md"
with io.open(path, "r", encoding="utf-8") as f:
    lines = f.read().split("\n")

idx = None
for i, line in enumerate(lines):
    if line.startswith("| H-C2 |") and "open — generate from an instruction-order diff" in line:
        idx = i
        break
if idx is None:
    sys.exit("H-C2 row not found")

line = lines[idx]
entry = " 2026-09-06 08:46 JST falsify tick: host busy (load1 26.70 / 5m 25.23 / 15m 44.71, up 1 day 1:29, 11 users, threshold 7.5), no measurement attempted; NEXT は H-C2 のまま"
if not line.endswith("|"):
    sys.exit("unexpected line ending: %r" % line[-20:])
lines[idx] = line[:-1] + " |" + entry

with io.open(path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("appended to line", idx + 1)
