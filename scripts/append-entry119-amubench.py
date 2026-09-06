#!/usr/bin/env python3
"""amu-bench iteration 119 append (host busy, no measurement). Idempotent."""
import io, os

REAL = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"

ENTRY = """
- **119 (2026-09-05 11:42 JST, bench pass; host busy, no measurement)**:
  bench tick. Host state at tick (pre-run script output in the tick
  payload; foreground terminal empty as usual, evidence collected via
  /tmp probe files): load1 22.47 / 5m 23.82 / 15m 23.53, up 4:25,
  12 users, 10 CPUs — load1 far above the 7.5 quiet limit and sustained
  across all three windows, so the quiet gate failed. The NEXT item (J-B
  fully-quiet-host rerun of `bench/runtime-comparison/jb_imod_control.c`,
  idle >=9/10) was not attempted and no bench or perfgate numbers were
  recorded. amu-falsify evidence checked: no new "要 quiet-host 測定"
  item pending. Population unchanged: H-C2, H-D, H-B, H-Y1 open;
  J-B confirmed-diagnostic (14 consecutive positive windows across 5)
  but unqualified, still awaiting the idle>=9/10 rerun; J-C blocked
  behind it. NEXT unchanged (entry 102 re-rank stands).
"""

log = []
with io.open(REAL, "r", encoding="utf-8") as f:
    text = f.read()
log.append("real doc size before: %d" % len(text.encode("utf-8")))
log.append("head intact: %s" % text.startswith("# Codegen co-scientist — tournament state"))
marker = "119 (2026-09-05 11:42 JST, bench pass; host busy, no measurement)"
if marker not in text:
    if not text.endswith("\n"):
        text += "\n"
    text += ENTRY
    with io.open(REAL, "w", encoding="utf-8") as f:
        f.write(text)
    log.append("entry 119 appended to real doc")
else:
    log.append("entry 119 already present in real doc; no change")

with io.open(REAL, "r", encoding="utf-8") as f:
    final = f.read()
log.append("real doc size after: %d" % len(final.encode("utf-8")))
log.append("head intact after: %s" % final.startswith("# Codegen co-scientist — tournament state"))

with io.open("/tmp/amu_bench_119_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(log) + "\n")
