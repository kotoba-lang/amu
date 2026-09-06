#!/usr/bin/env python3
"""amu-falsify 2026-09-05 21:16 JST: append busy-refusal evidence to docs/codegen-coscientist.md.
Written as a file because the cron runtime rejects heredocs and foreground
terminal returned empty output this tick (known shape, entries 96/99/104)."""
import io

DOC = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"

ENTRY = (
    "\n2026-09-05 21:16 JST (amu-falsify cron): host busy (load1 102.40 / 5m 106.72 / "
    "15m 76.47, up 13:59, 15 users, threshold 7.5) — timed measurement refused as "
    "instructed; no hand-patch, no bench, no perfgate run, no numbers. Foreground "
    "terminal again returned empty output (known shape, entries 96/99/104 etc.); doc "
    "read via read_file, this entry appended via script (no heredoc, per the "
    "entry-117 incident convention). NEXT unchanged: J-B fully-quiet-host rerun "
    "(idle>=9/10) of bench/runtime-comparison/jb_imod_control.c, then H-Z3 "
    "quiet-host hand-patch A/B, then H-C2. Population unchanged: J-B "
    "confirmed-diagnostic but unqualified, H-Z3 top of the codegen ladder, "
    "H-C2/H-D/H-B/H-Y1 open; J-C blocked behind J-B.\n"
)

with io.open(DOC, "r", encoding="utf-8") as f:
    body = f.read()

if "2026-09-05 21:16 JST (amu-falsify cron)" in body:
    print("ALREADY-APPENDED")
else:
    with io.open(DOC, "a", encoding="utf-8") as f:
        f.write(ENTRY)
    print("APPENDED", len(ENTRY))
