#!/usr/bin/env python3
import io
P = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
t = io.open(P, encoding="utf-8").read()
needle = "2026-09-05 20:39 JST falsify tick: host busy (load1 28.26"
print("count:", t.count(needle))
i = t.find(needle)
print("ctx:", t[max(0, i-120):i+200].replace("\n", " ")[:320] if i >= 0 else "NOT FOUND")
