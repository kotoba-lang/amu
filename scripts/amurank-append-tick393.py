import datetime, io, os

path = "docs/codegen-coscientist.md"
entry = ("- [rank tick 393, 2026-09-14 05:0x JST, amu-rank cron] host busy "
         "(load1 12.39 / 5m 12.07 / 15m 11.97 > gate 7.5, up 8d21h) -- measurement refused, "
         "rank-only pass. git fetch clean: origin/main 18ef21dd unchanged since tick 385; "
         "no new ADRs (0348 newest). Evidence reviewed since tick 392: one new sibling row "
         "(amu-bench busy-host 2026-09-14 04:21, load1 15.55, uncommitted in working tree); "
         "no new measured numbers. No re-rank, no status transition, no new hypothesis. "
         "Population unchanged: NEXT = H-C2 (quiet-host runtime-comparison vs Clang on `kernel`, "
         "instruction-order diff for the scheduling/front-end residue); fallback H-Z3 "
         "quiet-host hand-patch A/B. H-D/H-B/H-Y1/H-Z1 remain open.\n")

with io.open(path, "r", encoding="utf-8") as f:
    text = f.read()

marker = "## Standing honesty constraints"
idx = text.index(marker)
new_text = text[:idx] + entry + "\n" + text[idx:]
with io.open(path, "w", encoding="utf-8") as f:
    f.write(new_text)
print("appended", len(entry))
