#!/usr/bin/env python3
"""amu-bench 2026-09-05 22:02 JST: append busy-refusal evidence to docs/codegen-cosientist.md."""
import io

DOC = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-cosientist.md"

ENTRY = (
    "\n2026-09-05 22:02 JST (amu-bench cron, tick 123): host NOT quiet enough for the "
    "NEXT measurement — J-B rerun requires idle>=9/10 busy-CPU; measured "
    "sum_cpu_percent 278.8% on 10 CPUs (~28% busy, idle ~7/10), load1 6.24 (below "
    "the 7.5 proxy threshold) but load5 14.90 / load15 26.10 still decaying, "
    "up 14:44, 15 users. load-check via scripts/load-check-amubench.sh, evidence "
    "read from /tmp probe files (foreground terminal returns empty output — known "
    "shape). No bench/runtime-comparison, no perfgate run, no numbers recorded. "
    "NEXT unchanged: J-B fully-quiet-host rerun (idle>=9/10) of "
    "bench/runtime-comparison/jb_imod_control.c, then H-Z3 quiet-host hand-patch "
    "A/B, then H-C2. Population unchanged: J-B confirmed-diagnostic but "
    "unqualified, H-Z3 top of the codegen ladder, H-C2/H-D/H-B/H-Y1 open; J-C "
    "blocked behind J-B.\n"
)

with io.open(DOC, "r", encoding="utf-8") as f:
    body = f.read()

if "2026-09-05 22:02 JST (amu-bench cron, tick 123)" in body:
    print("ALREADY-APPENDED")
else:
    with io.open(DOC, "a", encoding="utf-8") as f:
        f.write(ENTRY)
    print("APPENDED", len(ENTRY))
