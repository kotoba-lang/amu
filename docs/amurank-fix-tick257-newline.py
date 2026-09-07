#!/usr/bin/env python3
path = "docs/codegen-coscientist.md"
with open(path, "r", encoding="utf-8") as f:
    s = f.read()
old = "then H-C2 ceiling-check A/B.2026-09-08"
new = "then H-C2 ceiling-check A/B.\n\n2026-09-08"
if old in s:
    s = s.replace(old, new, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(s)
    print("fixed")
else:
    print("anchor-not-found")