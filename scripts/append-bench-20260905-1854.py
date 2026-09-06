#!/usr/bin/env python3
"""Append bench-tick entry 131 (host busy, no measurement) to the real log."""
import io

PATH = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"

with io.open(PATH, "r", encoding="utf-8") as f:
    text = f.read()

entry = """- **131 (2026-09-05 18:54 JST, bench pass; host busy, no measurement)**:
  amu-bench tick. Host state at tick (`date`/`uptime` via
  /private/tmp/amubench_probe_1900.out): load1 43.97, 5m 45.80, 15m 54.32,
  up 11:37, 15 users. Far above the 7.5 quiet limit (consistent with entries
  129/130), so the quiet gate failed and no bench/perfgate run was
  attempted; no numbers recorded. Evidence reviewed: no new pending
  "要 quiet-host 測定" item since entry 130; NEXT unchanged. Population
  unchanged: H-C2, H-D, H-B, H-Y1 open; J-B confirmed-diagnostic but
  unqualified, still awaiting the idle>=9/10 rerun; J-C blocked behind it.
  NEXT unchanged: J-B fully-quiet-host rerun (idle >= 9/10) of
  `bench/runtime-comparison/jb_imod_control.c` for the perfgate-qualifiable
  number; H-C2 instruction-order-diff falsify plan queued behind it.

"""

marker = "## Standing honesty constraints"
idx = text.rfind(marker)
if idx == -1:
    raise SystemExit("marker not found")
text = text[:idx] + entry + text[idx:]

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(text)
print("appended entry 131")
