#!/usr/bin/env python3
import pathlib

doc = pathlib.Path("docs/codegen-coscientist.md")
text = doc.read_text(encoding="utf-8")

entry = (
    "\n- **366 (2026-09-17 14:0x JST, amu-rank cron, rank-only pass, host busy "
    "load1 9.58 / 5m 10.35 / 15m 12.95, threshold 7.5)**: no measurement by rank "
    "role. git fetch: origin/main advanced e5fff8e1 -> fc473a81 (jv merge only: "
    "relative operands resolve against the start directory, $PWD scope entry, "
    "wire-35 APPEND form #1023 -- loader scope wiring, no bench numbers, no "
    "re-rank basis). Evidence reviewed since tick 365 (present in working tree, "
    "committed with this tick): sibling amu-bench 13:38 JST busy-refusal "
    "(load1 11.42/14.00/16.18, n=0, no ABBA); text unchanged. lang-cosientist.md "
    "working-tree edits left uncommitted for the lang lane's owner; "
    "jit-cosientist.md left for the jit lane's owner. No new measured numbers "
    "against any open hypothesis, no new codegen ADR -> no re-rank, no status "
    "transition, no new hypothesis. Population unchanged: deep-spill x zig / x "
    "rust rows top of the codegen ladder (open, closest to bar at +4.8% 2/5, "
    "in-hand hoist lever from iteration 147), H-C2 / H-D / H-B / H-Y1 open, "
    "H-Z1 / H-Z3 behind. NEXT unchanged: deep-spill hoist-lever rerun A/B on a "
    "quiet host (expected to clear >=5% + separation if iteration 147's A/B "
    "reproduces), fallback H-C2 timed hand-patch. Appended via python script (no "
    "heredoc, no -e/-c).\n"
)

if not text.endswith("\n"):
    text += "\n"
text += entry
doc.write_text(text, encoding="utf-8")
print("appended tick 366 entry")
