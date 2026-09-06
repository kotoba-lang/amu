#!/usr/bin/env python3
"""Append falsify-tick entry 101 (host busy, no measurement) to docs/codegen-coscientist.md."""
import io, re

PATH = "docs/codegen-coscientist.md"
with io.open(PATH, "r", encoding="utf-8") as f:
    text = f.read()

entry = """- **101 (2026-09-05 04:41 JST, falsify pass; host busy, no measurement)**:
  04:41 JST load1 13.36 / 5min 8.91 / 15min 7.65, rising across the tick
  (load1 13.4-15.0, load5 9.2-9.8 over ~20 iostat samples); CPU idle
  oscillated 8-50% with sy 16-58% (no 9/10 idle window, no stable quiet
  stretch). load1 exceeded the 7.5 quiet limit on every sample, so per policy
  the quiet gate failed and no hand-patch or bench measurement was run.
  No new numbers, no re-rank basis: population unchanged (H-C2, H-D, H-B,
  H-Y1 open; J-B confirmed-diagnostic but unqualified, awaiting the
  idle>=9/10 rerun; J-C blocked behind it). NEXT: J-B fully-quiet-host rerun
  (idle >=9/10) of `bench/runtime-comparison/jb_imod_control.c` for the
  perfgate-qualifiable number (entry 100 re-rank stands).

"""

marker = "## Standing honesty constraints"
idx = text.rfind(marker)
if idx == -1:
    raise SystemExit("marker not found")
text = text[:idx] + entry + text[idx:]

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(text)
print("appended entry 101")
