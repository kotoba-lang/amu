import io, datetime

path = "docs/codegen-coscientist.md"
with io.open(path, "r", encoding="utf-8") as f:
    text = f.read()

line = (
    "\n- [rank tick 392, 2026-09-14, amu-rank cron] host busy (load1 11.12 / 5m 10.57 / 15m 10.46 > gate 7.5) "
    "-- measurement refused, rank-only pass. git fetch clean: HEAD 3ee3bd40 (tick 391) == origin/main 18ef21dd's descendant; "
    "no new commits since tick 391, no new ADRs (0348 newest), no new measured numbers. No re-rank, no status transition. "
    "Population unchanged: NEXT = H-C2 (quiet-host runtime-comparison vs Clang on `kernel`, instruction-order diff for the "
    "scheduling/front-end residue); fallback H-Z3 quiet-host hand-patch A/B. H-D/H-B/H-Y1/H-Z1 remain open.\n"
)

marker = "## Standing honesty constraints"
idx = text.index(marker)
text = text[:idx] + line + "\n" + text[idx:]

with io.open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("appended tick 392 line")
