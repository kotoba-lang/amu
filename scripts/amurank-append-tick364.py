import io
p = "docs/codegen-coscientist.md"
s = io.open(p, encoding="utf-8").read()
entry = "\n- **364 (2026-09-17 05:1x JST, amu-rank cron, rank-only pass, host busy load1 14.48 / 5m 12.33 / 15m 13.01, threshold 7.5)**: no measurement by rank role. git fetch: origin/main advanced 583e9849 -> d85307b4 (jv merge only: a $PATH scope entry expands to the caller's PATH at loader start #1021 — loader scope, no bench numbers, no re-rank basis). Evidence reviewed since tick 363: sibling amu-bench 04:08 JST busy-refusal (load1 13.60) present uncommitted in the working tree, inserted at the top of the Iteration log rather than appended; text unchanged, committed this tick with the rank entry. No new measured codegen numbers, no new codegen ADR -> no re-rank, no status transition, no new hypothesis. Population unchanged: deep-spill x zig / x rust rows top of the codegen ladder (open, closest to bar at +4.8% 2/5, in-hand hoist lever from iteration 147), H-C2 / H-D / H-B / H-Y1 open, H-Z3 behind. NEXT: deep-spill hoist-lever rerun A/B on a quiet host (expected to clear >=5% + separation if iteration 147's A/B reproduces), fallback H-C2. Appended via python script (no heredoc, no -e/-c).\n"
marker = "docs/codegen-cosientist.md.bak114 remain untracked"
i = s.rfind("\n- **363")
assert i > 0, "tick 363 entry not found"
j = s.find("\n\n", s.find("\n", i))  # end of 363 entry (paragraph break)
# simpler: append at end of file (last non-empty line is the 363 entry)
if not s.endswith("\n"):
    s += "\n"
s += entry
io.open(p, "w", encoding="utf-8").write(s)
print("appended")
