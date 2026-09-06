import io, sys

path = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
anchor = "2026-09-05 19:27 JST bench tick: host busy (load1 22.58, load5 38.33, load15 44.19, up 12:10, 15 users), quiet limit 7.5 exceeded ~3.0x; no measurement attempted; NEXT は H-C2 のまま."
addition = " | 2026-09-05 19:37 JST falsify tick: host busy (load1 47.61, load5 33.14, load15 36.43, up 12:20, 15 users, 10 CPUs), quiet limit 7.5 exceeded ~6.3x; no measurement attempted; NEXT は H-C2 のまま."

with io.open(path, "r", encoding="utf-8") as f:
    text = f.read()

count = text.count(anchor)
if count != 1:
    sys.exit("anchor count = %d, abort" % count)

new_text = text.replace(anchor, anchor + addition, 1)
with io.open(path, "w", encoding="utf-8") as f:
    f.write(new_text)

print("appended, new size:", len(new_text.encode("utf-8")))
