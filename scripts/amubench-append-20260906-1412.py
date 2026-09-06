#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import io

DOC = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
MARKER = "## Standing honesty constraints"

ENTRY = (
    "2026-09-06 14:1x JST (amu-bench cron, tick 139): bench/perfgate pass, no measurement. "
    "Host severely busy: load1 89.30 / 5m 51.72 / 15m 28.73 (uptime probe via /private/tmp/"
    "amu_bench_probe1.py -> amu_bench_probe1.json, read back verified; threshold 7.5, ~11.9x "
    "over gate, rising trend 76->89). No quiet gate -> H-C2 timed A/B, H-D quiet-host rerun, "
    "and H-Z3 quiet-host A/B all unattemptable this tick. No bench, no perfgate run, no "
    "numbers recorded. Population unchanged: J-B confirmed-diagnostic unqualified (17 "
    "consecutive positive windows, ADR 0339), H-C2 statically confirmed 61/61 timed A/B "
    "pending, H-Z3 top of codegen ladder, H-D/H-B/H-Y1 open; J-C blocked behind J-B. "
    "NEXT: J-B fully-quiet-host rerun, then H-Z3 quiet-host hand-patch A/B, then H-C2 "
    "timed A/B.\n"
)

with io.open(DOC, "r", encoding="utf-8") as f:
    text = f.read()

idx = text.rfind(MARKER)
if idx < 0:
    raise SystemExit("marker not found: " + MARKER)

new_text = text[:idx] + ENTRY + "\n" + text[idx:]
with io.open(DOC, "w", encoding="utf-8") as f:
    f.write(new_text)

print("appended", len(ENTRY), "chars at offset", idx)
