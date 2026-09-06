#!/usr/bin/env python3
"""Append bench-tick entry 104 (host busy, no measurement) to docs/codegen-coscientist.md."""
import io

PATH = "docs/codegen-coscientist.md"
with io.open(PATH, "r", encoding="utf-8") as f:
    text = f.read()

entry = """- **104 (2026-09-05 05:30 JST, bench pass; host busy, no measurement)**:
  quiet gate checked for the J-B rerun: 05:30:50 JST load1 10.56 / 5min 6.78 /
  15min 6.57; 10 top-based CPU samples over ~10s read idle 18.40-60.72%
  (mean ~39%, sy 16.83-64.39%) -- load1 exceeded the 7.5 quiet limit and no
  sample reached the idle>=90% bar, so the idle>=9/10 criterion never
  qualified and `bench/runtime-comparison/jb_imod_control.c` was not run.
  (Foreground terminal again returned empty output this tick; probes were run
  via script files in background sessions, evidence /tmp/amubench_mon_20260905b.txt.)
  No new numbers; population unchanged (H-C2, H-D, H-B, H-Y1 open; J-B
  confirmed-diagnostic but unqualified, 11 consecutive positive windows,
  still awaiting the idle>=9/10 rerun; J-C blocked behind it).
  NEXT: J-B fully-quiet-host rerun (idle >=9/10) of
  `bench/runtime-comparison/jb_imod_control.c` for the perfgate-qualifiable
  number (entry 102 re-rank stands).

"""

marker = "## Standing honesty constraints"
idx = text.rfind(marker)
if idx == -1:
    raise SystemExit("marker not found")
text = text[:idx] + entry + text[idx:]

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(text)
print("appended entry 104")
