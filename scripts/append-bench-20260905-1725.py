#!/usr/bin/env python3
"""Append bench-tick entry 124 (host busy, no measurement) to the real log."""
import io

PATH = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"

with io.open(PATH, "r", encoding="utf-8") as f:
    text = f.read()

entry = """- **124 (2026-09-05 17:26 JST, bench pass; host busy, no measurement)**:
  quiet gate checked with 10 top-based CPU samples over ~30s (17:24:14-17:24:44
  JST on main-2.local, up 10:07, 22 users, 10 CPUs): idle 19.62-52.00% (no
  sample near the 90% bar, idle>=9/10 count 0/10, sy 11.96-27.54%); load
  averages 17:23 14.42/17.16/18.04 -> 17:24 14.99/16.51/17.70 -- heavily
  loaded throughout, so the quiet gate failed and no bench/perfgate run was
  attempted (NEXT target H-C2 kernel rerun deferred; J-B fully-quiet rerun
  also still deferred). Evidence file: /tmp/amubench_mon_20260905f.txt
  (foreground terminal returned empty output; collected via /tmp probe).
  amu-falsify evidence checked via the iteration log: no new pending
  quiet-host-request item. Population unchanged: H-C2, H-D, H-B, H-Y1 open;
  J-B confirmed-diagnostic but unqualified, awaiting idle>=9/10 rerun; J-C
  blocked behind it. NEXT unchanged: J-B fully-quiet-host rerun
  (idle >= 9/10) of `bench/runtime-comparison/jb_imod_control.c`, then H-C2.

"""

marker = "## Standing honesty constraints"
idx = text.rfind(marker)
if idx == -1:
    raise SystemExit("marker not found")
text = text[:idx] + entry + text[idx:]

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(text)
print("appended entry 124")
