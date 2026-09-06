#!/usr/bin/env python3
"""amu-falsify 2026-09-05 19:15 JST tick: append busy-refusal to the iteration log."""
import io

P = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
ENTRY = (
    "- **122b (2026-09-05 19:15 JST, amu-falsify cron, measurement refused)**: "
    "host busy (load1 57.77 / load5 51.82 / load15 47.43, threshold 7.5) — no "
    "hand-patch or bench run attempted, no numbers. NEXT unchanged: H-C2 "
    "(instruction-order diff vs clang on `kernel`), quiet-host only.\n"
)

with io.open(P, "r", encoding="utf-8") as f:
    txt = f.read()

if ENTRY.strip() in txt:
    print("already present")
else:
    if not txt.endswith("\n"):
        txt += "\n"
    txt += "\n" + ENTRY
    with io.open(P, "w", encoding="utf-8") as f:
        f.write(txt)
    print("appended")
