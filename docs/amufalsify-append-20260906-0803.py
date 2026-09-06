#!/usr/bin/env python3
import io, re
p = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
ts = "2026-09-06 08:03 JST"
msg = "2026-09-06 08:03 JST falsify tick: host busy (load1 189.38, load5 143.17, load15 102.99, up 1 day, 15 users, threshold 7.5), no measurement attempted; NEXT (J-B idle>=9/10 rerun, then H-Z3, then H-C2) not run, no numbers recorded"
with io.open(p, encoding="utf-8") as f:
    lines = f.read().split("\n")
for i, line in enumerate(lines):
    if line.startswith("| H-C2 |"):
        lines[i] = line + " | " + msg
        break
else:
    raise SystemExit("H-C2 row not found")
with io.open(p, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("appended to H-C2 row")
