#!/usr/bin/env python3
"""amu-falsify 2026-09-05 18:48 JST: append one busy-refusal evidence line."""
from datetime import datetime
from pathlib import Path

DOC = Path(__file__).resolve().parents[1] / "docs" / "codegen-coscientist.md"
LINE = (
    "2026-09-05 18:48 JST (amu-falsify cron): host busy (load1 49.77 at pre-run / "
    "92.44 at rank tick 120, threshold 7.5) — timed measurement refused as "
    "instructed; no bench, no perfgate run, no numbers. NEXT unchanged "
    "(J-B fully-quiet-host rerun idle>=9/10 of bench/runtime-comparison/"
    "jb_imod_control.c, then H-Z3 quiet-host hand-patch A/B, then H-C2); "
    "H-C2/H-D/H-B/H-Y1 open, H-Z3 top of the codegen ladder. No hand-patch "
    "work started: all remaining falsify paths (H-Z3 A/B, H-C2 A/B) require a "
    "quiet host; no load-robust static work remains. Working tree left "
    "marker-free per tick 120's finding (origin/main conflict markers NOT "
    "inherited). No status transitions without numbers.\n"
)

text = DOC.read_text(encoding="utf-8")
if "18:48 JST (amu-falsify cron)" in text:
    print("already appended; skipping")
else:
    if not text.endswith("\n"):
        text += "\n"
    DOC.write_text(text + LINE, encoding="utf-8")
    print("appended at", datetime.now().isoformat())
