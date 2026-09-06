#!/usr/bin/env python3
"""amu-falsify busy-refusal evidence append (append-only, one line)."""
import io, os

DOC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "codegen-coscientist.md")
DOC = os.path.normpath(DOC)

line = (
    "\n2026-09-06 07:07 JST (amu-falsify cron): host busy (load1 95.94 / 5m 60.01 / "
    "15m 56.10 at 07:07, up 23:50, 11 users, threshold 7.5) — timed measurement refused "
    "per quiet-gate rule; monitor NEXT H-C2 timed A/B and all timed hypotheses "
    "(J-B rerun, H-Z3 hand-patch A/B) unattemptable this tick. No hand-patch, no bench, "
    "no perfgate run, no numbers. NEXT unchanged: J-B fully-quiet-host rerun "
    "(idle>=9/10, sustained-window; binary preflighted at /private/tmp/jb_imod_control_preflight), "
    "then H-Z3 quiet-host hand-patch A/B, then H-C2 timed A/B (static-confirmed 61/61). "
    "Population unchanged: J-B confirmed-diagnostic but unqualified, H-Z3 top of the codegen "
    "ladder, H-C2 statically confirmed but timed A/B pending, H-D/H-B/H-Y1 open; J-C blocked "
    "behind J-B. Load probes via redirect-to-file (foreground terminal empty-output shape, "
    "known); this entry appended via script (no heredoc, per the entry-117 convention).\n"
)

with io.open(DOC, "r", encoding="utf-8") as f:
    before = f.read()

if "2026-09-06 07:07 JST (amu-falsify cron)" in before:
    print("already-appended")
else:
    with io.open(DOC, "a", encoding="utf-8") as f:
        f.write(line)
    with io.open(DOC, "r", encoding="utf-8") as f:
        after = f.read()
    print("appended", len(before), "->", len(after))
