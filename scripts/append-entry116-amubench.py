#!/usr/bin/env python3
"""Append amu-bench iteration-log entry 116 before '## Standing honesty constraints'."""
import io, sys

PATH = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
MARKER = "## Standing honesty constraints"
SENTINEL = "116 (2026-09-04 22:34 JST, amu-bench bench tick"
ENTRY = """- **116 (2026-09-04 22:34 JST, amu-bench bench tick; host busy by the
  busy-CPU criterion, no measurement)**: load1 5.52 — nominally below the
  7.5 proxy limit for the first time in this run — but the gate quantity
  itself, busy-CPU fraction, read 388% summed process CPU on 10 CPUs ~= 39%
  busy (up 6 days, 10:33, 14 users, macOS 26.4; load5 8.90, load15 10.20),
  far above the 3-5% quiet band perfgate's H-A gate uses. Per policy no
  bench, perfgate, or hand-patch measurement attempted, no numbers
  recorded. amu-falsify evidence checked: no new "要 quiet-host 測定" item
  pending. Population unchanged: H-C2, H-D, H-B, H-Y1 open (J-B awaiting a
  quiet host; J-C blocked behind J-B). NEXT: H-C2 (unchanged — highest
  expected qualified gain × probability; ~4.4% residual vs Clang on
  `kernel`, near-identical static shape, separable).

"""

with io.open(PATH, "r", encoding="utf-8") as f:
    text = f.read()

if SENTINEL in text:
    print("already present; no change")
    sys.exit(0)

idx = text.find(MARKER)
if idx < 0:
    print("marker not found; aborting without change")
    sys.exit(1)

new_text = text[:idx] + ENTRY + text[idx:]
with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(new_text)
print("inserted entry 116 at byte", idx)
