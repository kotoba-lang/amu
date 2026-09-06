#!/usr/bin/env python3
"""amu-falsify 2026-09-05 23:07 JST: append one busy-refusal evidence line."""
from datetime import datetime
from pathlib import Path

DOC = Path(__file__).resolve().parents[1] / "docs" / "codegen-coscientist.md"
LINE = (
    "2026-09-05 23:07 JST (amu-falsify cron): host busy — load1 dipped to 3.73 "
    "at 23:03 (from 7.47 at 22:48) but rose again during iostat observation "
    "(23:00-23:06 JST: load1 6.96->17.65, iostat idle 21-69% = 4-6 idle CPUs "
    "of 10, load5 9.2-10.7, up 15:46, 15 users, threshold 7.5) — no sustained "
    "quiet window, so the J-B fully-quiet-host rerun and the H-Z3 hand-patch "
    "A/B were NOT started (measurement not started per quiet-gate rule). "
    "No numbers recorded. Foreground terminal returned empty output (known "
    "shape, entries 96/99/104 etc.); load probes via background sleep + file "
    "redirect, doc read via read_file, this entry appended via script (no "
    "heredoc, per the entry-117 incident convention). NEXT unchanged: J-B "
    "fully-quiet-host rerun (idle>=9/10) of bench/runtime-comparison/"
    "jb_imod_control.c, then H-Z3 quiet-host hand-patch A/B, then H-C2. "
    "Population unchanged: J-B confirmed-diagnostic but unqualified, H-Z3 "
    "top of the codegen ladder, H-C2/H-D/H-B/H-Y1 open; J-C blocked behind "
    "J-B.\n"
)

text = DOC.read_text(encoding="utf-8")
if "23:07 JST (amu-falsify cron)" in text:
    print("already appended; skipping")
else:
    if not text.endswith("\n"):
        text += "\n"
    DOC.write_text(text + LINE, encoding="utf-8")
    print("appended at", datetime.now().isoformat())
