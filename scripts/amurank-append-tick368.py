import io, sys

path = "docs/codegen-coscientist.md"
entry = """
- **368 (2026-09-17 20:0x JST, amu-rank cron, rank-only pass, host busy load1 16.70 / 5m 28.71 / 15m 39.90, threshold 7.5)**: no measurement by rank role. git fetch: origin/main unchanged at fc473a81 since tick 367 -- no new merges, no re-rank basis. Evidence reviewed since tick 367: no new sibling bench/falsify entries in the working tree (only the three lane-owned docs remain modified); docs/jit-cosientist.md and docs/lang-cosientist.md working-tree edits remain uncommitted for their lane owners. No new measured numbers against any open hypothesis, no new codegen ADR -> no re-rank, no status transition, no new hypothesis. Population unchanged: deep-spill x zig / x rust rows top of the codegen ladder (open, closest to bar at +4.8% 2/5, in-hand hoist lever from iteration 147), H-C2 / H-D / H-B / H-Y1 open, H-Z1 / H-Z3 behind. NEXT unchanged: deep-spill hoist-lever rerun A/B on a quiet host (expected to clear >=5% + separation if iteration 147's A/B reproduces), fallback H-C2 timed hand-patch. Appended via python script (no heredoc, no -e/-c).
"""

with io.open(path, "r", encoding="utf-8") as f:
    text = f.read()

if "368 (2026-09-17 20:0x JST" in text:
    print("ALREADY-APPENDED")
    sys.exit(0)

marker = "Appended via python script (no heredoc, no -e/-c)."
idx = text.rfind(marker)
if idx == -1:
    print("MARKER-NOT-FOUND")
    sys.exit(1)
end = idx + len(marker)
# entry goes at end of the Iteration log; append after the last committed rank entry
new_text = text[:end] + entry + text[end:]
with io.open(path, "w", encoding="utf-8") as f:
    f.write(new_text)
print("APPENDED")
