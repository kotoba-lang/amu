import io
p = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
s = io.open(p, encoding="utf-8").read()
marker = "2026-09-05 20:25 JST falsify tick"
i = s.find(marker)
assert i != -1
line = s.find("\n", i)
assert line != -1
evidence = (" | 2026-09-05 21:01 JST falsify tick: host busy (load1 36.16, load5 26.72, "
            "load15 27.42, up 13:44, 15 users, threshold 7.5), no measurement attempted; "
            "NEXT (J-B idle>=9/10 rerun, then H-Z3, then H-C2) not run, no numbers recorded")
s = s[:line] + evidence + s[line:]
io.open(p, "w", encoding="utf-8").write(s)
print("appended")
