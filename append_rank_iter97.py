#!/usr/bin/env python3
"""amu-rank iteration 97: evidence-only append (host busy) + iteration log entry."""
import datetime, io

p = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
ts = "2026-09-04 13:49 JST"

with io.open(p, encoding="utf-8") as f:
    lines = f.read().splitlines()

# 1) H-C2 evidence-only append (single occurrence, avoiding duplicate ticks)
tick = ("2026-09-04 13:49 JST rank tick: host busy (load1 51.26, load5 54.62, "
        "load15 55.00, up 11 days, 5:36, 8 users, 10 CPUs), no measurement "
        "attempted; NEXT は H-C2 のまま")
for i, l in enumerate(lines):
    if l.startswith("| H-C2 |"):
        if not l.rstrip().endswith("のまま"):
            raise SystemExit("H-C2 row tail unexpected; refusing blind append")
        lines[i] = l.rstrip() + tick
        break
else:
    raise SystemExit("H-C2 row not found")

# 2) Iteration log entry 97 before "## Standing honesty constraints"
entry = """- **97 (2026-09-04 13:49 JST, rank pass; host busy, no measurement)**:
  load1 51.26 / 5min 54.62 / 15min 55.00 (up 11 days, 5:36, 8 users, 10
  CPUs) — ~6.8x above the 7.5 quiet limit; per policy no bench, perfgate,
  or hand-patch measurement attempted, no numbers recorded. git fetch
  reviewed: 4 commits on origin/main since HEAD's base, none carrying new
  measured evidence against any open hypothesis (perfgate bridge fix
  6fedc78b, merge d727ec94, rank-only 855b1fe9, ABI test reproduction
  a7e469f2). Top CPU consumers are interactive user processes (java ~121%,
  Chrome ~100%, kotoba-shell-host ~97%) — a user workload, not a fleet
  measurement window. No re-rank, no status transition, no new hypothesis
  — a re-rank without measured numbers would be fabrication. Population
  unchanged: H-C2, H-D, H-B, H-Y1 open (J-B awaiting a quiet host; J-C
  blocked behind J-B). NEXT: H-C2 (unchanged — highest expected qualified
  gain x probability; ~4.4% residual vs Clang on `kernel`,
  near-identical static shape, separable).
"""
try:
    idx = lines.index("## Standing honesty constraints")
except ValueError:
    raise SystemExit("section marker not found")
lines[idx:idx] = entry.splitlines()

with io.open(p, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("appended", ts)
