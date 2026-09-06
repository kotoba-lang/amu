#!/usr/bin/env python3
"""Append bench-tick entry 128 (host busy, no measurement) to the real log."""
import io

PATH = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"

with io.open(PATH, "r", encoding="utf-8") as f:
    text = f.read()

entry = """- **128 (2026-09-05 17:56 JST, bench pass; host busy, no measurement)**:
  amu-bench tick. Host state at tick (`uptime`/`date`/`top -l 3 -s 10` via
  /tmp/bench_uptime.txt): load1 42.99/42.12/42.08, 5m 30.3-30.9, 15m 27.6-27.9,
  up 10:38, 17 users, 10 CPUs; CPU idle 43.46% -> 23.21% -> 4.70% over three
  10s-spaced top samples (idle>=90% count 0/3, no decay). Far above the 7.5
  quiet limit, so the quiet gate failed and no bench/perfgate run was
  attempted; no numbers recorded. Evidence reviewed since entry 127
  (iteration log): no new pending "要 quiet-host 測定" item; NEXT unchanged.
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
print("appended entry 128")
