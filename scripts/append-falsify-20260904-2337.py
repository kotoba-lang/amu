#!/usr/bin/env python3
"""Append a host-busy evidence line to the H-C2 row in docs/codegen-coscientist.md."""
import io, sys

PATH = "docs/codegen-coscientist.md"
OLD = "| 2026-09-04 23:29 JST bench tick: host busy (load1 9.94, load5 16.42, load15 22.43, up 6 days, 11:28, 11 users), no measurement attempted; NEXT は H-C2 のまま"
NEW = OLD + " | 2026-09-04 23:37 JST falsify tick: host busy (load1 30.18, load5 25.68, load15 24.42, up 6 days, 11:35, 10 users), no measurement attempted; quiet limit 7.5 exceeded ~4.0x; NEXT は H-C2 のまま"

with io.open(PATH, encoding="utf-8") as f:
    text = f.read()
count = text.count(OLD)
if count != 1:
    sys.exit(f"anchor count={count}, expected 1")
with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(text.replace(OLD, NEW))
print("appended H-C2 host-busy evidence")
