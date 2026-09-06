#!/usr/bin/env python3
"""Append host-busy evidence for H-C2 to docs/codegen-coscientist.md (amu-bench cron)."""
import datetime, io, os

DOC = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
MARKER = "## Standing honesty constraints"

entry = (
    "| 2026-09-05 19:27 JST | amu-bench | H-C2 | measurement SKIPPED: host busy "
    "(load1 22.58, load5 38.33, load15 44.19 at 19:27 JST; policy threshold load1 > 7.5). "
    "No bench/perfgate run performed to avoid polluting evidence with busy-host noise. "
    "No new measurement. | host busy |"
)

with io.open(DOC, "r", encoding="utf-8") as f:
    text = f.read()

idx = text.rfind(MARKER)
if idx == -1:
    raise SystemExit("marker not found")

new_text = text[:idx] + entry + "\n" + text[idx:]
with io.open(DOC, "w", encoding="utf-8") as f:
    f.write(new_text)

print("appended; doc chars:", len(new_text))
