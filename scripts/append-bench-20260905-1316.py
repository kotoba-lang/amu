#!/usr/bin/env python3
"""Append bench-tick entry 122 (host busy, no measurement) to docs/codegen-coscientist.md."""
import io

PATH = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
with io.open(PATH, "r", encoding="utf-8") as f:
    text = f.read()

entry = """- **122 (2026-09-05 13:16 JST, bench pass; host busy, no measurement)**:
  quiet gate checked for the J-B rerun with 10 top-based CPU samples over
  ~14s starting 13:15:28 JST on main-2.local: idle 53.70-67.93% (no sample
  near the 90% bar, idle>=9/10 count 0/10, sy 14.94-21.95%); load averages
  moved 13:11 5.26/7.58/13.15 -> 13:15 16.97/12.10/13.70 (up 5:58, 12 users,
  10 CPUs) -- load1 was below 7.5 at the pre-run script's reading but rose
  ~3x within 4 minutes and idle never approached 9/10, so the quiet gate
  failed and `bench/runtime-comparison/jb_imod_control.c` (file present,
  82 lines) was not run. (Background `workdir` is ignored on this runtime:
  commands ran in /tmp/kotoba-fix; evidence collected via absolute-path
  probe scripts, /tmp/amubench_mon_20260905c.txt.) amu-falsify evidence
  checked via the iteration log: no new \"要 quiet-host 測定\" item pending.
  One new landing since entry 121: 4fdfb1bc (lang-cosientist iteration 8,
  some-> repair parity probe -- evidence only, no compiler change, no
  bearing on the codegen population; no re-rank). Population unchanged:
  H-C2, H-D, H-B, H-Y1 open; J-B confirmed-diagnostic (14 consecutive
  positive windows across 5) but unqualified, still awaiting the idle>=9/10
  rerun; J-C blocked behind it. NEXT unchanged (entry 102 re-rank stands):
  J-B fully-quiet-host rerun (idle >= 9/10) of
  `bench/runtime-comparison/jb_imod_control.c`; lever-2-only control
  (non-inlined mulh arm) follows it once a quiet host is available.

"""

marker = "## Standing honesty constraints"
idx = text.rfind(marker)
if idx == -1:
    raise SystemExit("marker not found")
text = text[:idx] + entry + text[idx:]

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(text)
print("appended entry 122")
