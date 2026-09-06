#!/usr/bin/env python3
import io
P = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
OUT = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/probe_out.txt"
t = io.open(P, encoding="utf-8").read()
needle = "2026-09-05 20:39 JST falsify tick: host busy (load1 28.26"
n = t.count(needle)
i = t.find(needle)
ctx = t[max(0, i-150):i+220].replace("\n", " ") if i >= 0 else "NOT FOUND"
with io.open(OUT, "w", encoding="utf-8") as f:
    f.write("count=%d\nctx=%s\n" % (n, ctx))
