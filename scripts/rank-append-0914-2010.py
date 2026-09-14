import datetime, io, os
p = "docs/codegen-coscientist.md"
s = open(p, encoding="utf-8").read()
line = "| 2026-09-14 20:0x JST rank tick 394 (amu-rank): host busy (load1 11.21, load5 11.79, load15 12.88 > gate 7.5, up 9d12h), no measurement attempted; rank-only pass. Evidence reviewed since tick 393: several sibling busy-host bench rows (2026-09-14 10:09/13:22/16:07, load1 14.30-23.47) and two amu-maint rows (PR #984 CI: route-refusal red gone, remaining Windows failure = #902 loader-identity bug) — no new measured numbers, no hypothesis-relevant evidence. No re-rank, no status transition, no new hypothesis. Population unchanged: NEXT = H-C2 (quiet-host runtime-comparison vs Clang on `kernel`, instruction-order diff for the scheduling/front-end residue); fallback H-Z3 quiet-host hand-patch A/B. H-D/H-B/H-Y1/H-Z1 remain open.\n"
anchor = "| 2026-09-13 23:03 JST rank tick 391 (amu-rank)"
i = s.rindex(anchor)
e = s.index("\n", i) + 1
s = s[:e] + line + s[e:]
open(p, "w", encoding="utf-8").write(s)
print("ok")
