#!/usr/bin/env python3
import io
P = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
t = io.open(P, encoding="utf-8").read()
i = t.find("2026-09-05 20:02 JST falsify tick")
print("found at", i)
print(repr(t[i-160:i+260]))
