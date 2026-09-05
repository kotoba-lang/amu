import io, re

P = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
with io.open(P, encoding="utf-8") as f:
    t = f.read()

entry = (" 2026-09-06 00:28 JST falsify tick: host busy "
         "(load1 8.54, load5 9.57, load15 13.31, up 17:11, 9 users, threshold 7.5; "
         "note: load falling 15m>5m>1m but policy is strict on load1), "
         "no measurement attempted; NEXT は H-C2 のまま")

# H-C2 row is the first table row starting "| H-C2 |"
m = re.search(r"^\| H-C2 \|", t, re.M)
assert m, "H-C2 row not found"
# find end of that row (end of line)
end = t.index("\n", m.start())
t = t[:end] + entry + t[end:]

with io.open(P, "w", encoding="utf-8") as f:
    f.write(t)
print("appended, file chars:", len(t))
