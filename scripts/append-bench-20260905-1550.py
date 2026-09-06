#!/usr/bin/env python3
"""Append bench-tick entry 123 (host busy, no measurement) to docs/codegen-coscientist.md."""
import io

PATH = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
with io.open(PATH, "r", encoding="utf-8") as f:
    text = f.read()

entry = """- **123 (2026-09-05 15:50 JST, bench pass; host busy, no measurement)**:
  quiet gate checked for the J-B fully-quiet rerun (idle >= 9/10) with 10
  top-based CPU samples over ~13s starting 15:49:49 JST on main-2.local
  (up 8:32, 17 users, 10 CPUs): idle 48.82-62.74% (no sample near the 90%
  bar, idle>=9/10 count 0/10, sy 15.62-22.60%); load averages 15:48
  52.98/56.56/85.22 -> 15:49 50.45/55.63/83.89 -- heavily loaded throughout,
  so the quiet gate failed and `bench/runtime-comparison/jb_imod_control.c`
  was not run. (Foreground terminal returned empty output; evidence collected
  via /tmp probe script, /tmp/amubench_mon_20260905e.txt.) amu-falsify
  evidence checked via the iteration log: no new \"要 quiet-host 測定\" item
  pending. No new hypothesis-relevant landing observed since entry 122;
  population unchanged: H-C2, H-D, H-B, H-Y1 open; J-B confirmed-diagnostic
  but unqualified, still awaiting the idle>=9/10 rerun; J-C blocked behind
  it. NEXT unchanged: J-B fully-quiet-host rerun (idle >= 9/10) of
  `bench/runtime-comparison/jb_imod_control.c`.

"""

marker = "## Standing honesty constraints"
idx = text.rfind(marker)
if idx == -1:
    raise SystemExit("marker not found")
text = text[:idx] + entry + text[idx:]

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(text)
print("appended entry 123")
