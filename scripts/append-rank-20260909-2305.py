import re, io
p = "docs/codegen-coscientist.md"
src = io.open(p, encoding="utf-8").read()

# 1. de-dup the repeated uncommitted amu-bench 22:07 blocks (keep the first)
marker = "**amu-bench tick (2026-09-09 22:07 JST, host busy; no measurement)**:"
first = src.find(marker)
assert first != -1
# end of the first block: it ends with "Population unchanged.\n"
blk_end = src.find("Population unchanged.\n", first)
assert blk_end != -1
blk_end += len("Population unchanged.\n")
count = src.count(marker)
if count > 1:
    # remove all subsequent occurrences of marker..block end
    out = []
    pos = 0
    while True:
        i = src.find(marker, pos)
        if i == -1:
            out.append(src[pos:])
            break
        out.append(src[pos:i])
        j = src.find("Population unchanged.\n", i)
        assert j != -1
        pos = j + len("Population unchanged.\n")
    src = "".join(out)
# strip leftover doubled blank lines just before the honesty section
src = re.sub(r"\n{3,}(## Standing honesty constraints)", r"\n\n\1", src)

# 2. append the rank tick entry before the standing honesty section
tick = """- **356 (2026-09-09 23:05 JST, amu-rank cron)**: host busy (load1 19.30 / 5m 19.92 / 15m 25.34 at 23:02, threshold 7.5) — measurement refused, rank-only pass. git fetch: origin/main advanced b631a7fe -> 9ee8020b (PR #912 `:schemas`-declaring module may be required; PR #910 loader granted-region; PR-linked compiler/loader scope, no codegen-ladder number). Local worktree: 8 duplicate uncommitted amu-bench 22:07 busy-refusal entries in this doc collapsed to 1 by this rank tick (content identical, no measured numbers lost — blocks contained only the load1 24.26 busy refusal); no new ADR (0345 remains newest on disk); no new sibling measured evidence since tick 355. No re-rank, no status transition, no new hypothesis — no new measured numbers exist. Population unchanged: H-Z3 top of the codegen ladder, H-C2/H-D/H-B/H-Y1 open, J-C folded behind J-B. NEXT unchanged: benjamin collections walk-loop hand-patch (imod helper inlining, J-B2/H-Z3) via perfgate on a quiet fleet node (qualifying nodes levi 0.04 / joseph 0.05 / benjamin 0.05 / judah 0.07); host busy since ~tick 258.

"""
anchor = "## Standing honesty constraints"
i = src.find(anchor)
assert i != -1
src = src[:i] + tick + src[i:]
io.open(p, "w", encoding="utf-8").write(src)
print("ok")
