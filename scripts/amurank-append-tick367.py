import io
p = "docs/codegen-coscientist.md"
entry = """
- **367 (2026-09-17 17:1x JST, amu-rank cron, rank-only pass, host busy load1 18.03 / 5m 16.23 / 15m 20.16, threshold 7.5)**: no measurement by rank role. git fetch: origin/main unchanged at fc473a81 since tick 366 -- no new merges, no re-rank basis. Evidence reviewed since tick 366: no new sibling bench/falsify entries in the working tree; docs/jit-cosientist.md and docs/lang-cosientist.md working-tree edits remain uncommitted for their lane owners. No new measured numbers against any open hypothesis, no new codegen ADR -> no re-rank, no status transition, no new hypothesis. Population unchanged: deep-spill x zig / x rust rows top of the codegen ladder (open, closest to bar at +4.8% 2/5, in-hand hoist lever from iteration 147), H-C2 / H-D / H-B / H-Y1 open, H-Z1 / H-Z3 behind. NEXT unchanged: deep-spill hoist-lever rerun A/B on a quiet host (expected to clear >=5% + separation if iteration 147's A/B reproduces), fallback H-C2 timed hand-patch. Appended via python script (no heredoc, no -e/-c).
"""
with io.open(p, "r", encoding="utf-8") as f:
    txt = f.read()
if "**367 (" in txt:
    raise SystemExit("tick 367 already present")
with io.open(p, "a", encoding="utf-8") as f:
    f.write(entry)
print("appended")
