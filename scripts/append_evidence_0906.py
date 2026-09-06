import io
p = "docs/codegen-coscientist.md"
s = io.open(p, encoding="utf-8").read()
old = "2026-09-06 06:16 JST falsify tick: host busy (load1 20.12, load5 12.37, load15 10.04), no measurement attempted; NEXT は H-C2 のまま"
add = " | 2026-09-06 06:22 JST falsify tick: host busy (load1 106.82, load5 58.23, load15 30.59, threshold 7.5), no measurement attempted; NEXT は H-C2 のまま"
cnt = s.count(old)
if cnt != 1:
    print("MATCH_COUNT", cnt)
else:
    s = s.replace(old, old + add)
    io.open(p, "w", encoding="utf-8").write(s)
    print("APPENDED_OK")
