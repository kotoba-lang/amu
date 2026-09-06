#!/usr/bin/env python3
"""Append bench-tick entry 129 (host busy, no measurement) to the real log."""
import io

PATH = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"

with io.open(PATH, "r", encoding="utf-8") as f:
    text = f.read()

entry = """- **129 (2026-09-05 18:09 JST, bench pass; host busy, no measurement)**:
  amu-bench tick. Host state at tick (`uptime`/`sysctl vm.loadavg`/`date` and
  `top -l 3 -s 10` via /tmp/bench_uptime.txt): load1 41.52 -> 35.61 -> 35.58
  -> 33.95, 5m 49.30 -> 45.43, 15m 38.99 -> 38.40, up 10:50, 16 users, 10
  CPUs; CPU idle 40.39% -> 42.45% -> 45.86% over three 10s-spaced top
  samples (idle>=90% count 0/3, no decay). Far above the 7.5 quiet limit,
  so the quiet gate failed and no bench/perfgate run was attempted; no
  numbers recorded. Evidence reviewed since entry 128 (iteration log): no
  new pending "\\u8981 quiet-host \\u6e2c\\u5b9a" item; NEXT unchanged.
  Population unchanged: H-C2, H-D, H-B, H-Y1 open; J-B confirmed-diagnostic
  but unqualified, still awaiting the idle>=9/10 rerun; J-C blocked behind
  it. NEXT unchanged: J-B fully-quiet-host rerun (idle >= 9/10) of
  `bench/runtime-comparison/jb_imod_control.c` for the perfgate-qualifiable
  number (entry 102 re-rank stands); H-C2 instruction-order-diff falsify
  plan queued behind it.

"""

marker = "## Standing honesty constraints"
idx = text.rfind(marker)
if idx == -1:
    raise SystemExit("marker not found")
text = text[:idx] + entry + text[idx:]

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(text)
print("appended entry 129")
