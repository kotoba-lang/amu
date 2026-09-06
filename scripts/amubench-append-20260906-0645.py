#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import io

DOC = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
MARKER = "## Standing honesty constraints"

ENTRY = (
    "2026-09-06 06:4x JST (amu-bench cron, tick 138): bench/perfgate pass, no measurement. "
    "Host severely busy: load1 56.73 / 5m 62.97 / 15m 62.59 (uptime probe via /tmp/amubench-load.txt, "
    "read back verified; threshold 7.5, ~7.5x over gate, flat-high trend). No quiet gate, no sustained "
    "quiet window -> J-B idle>=9/10 sustained-window rerun, H-Z3 quiet-host hand-patch A/B, and H-C2 "
    "timed A/B all unattemptable this tick. No bench, no perfgate run, no numbers recorded. "
    "Evidence reviewed: no new sibling quiet-host measurements since tick 137; no new codegen ADR "
    "(0338 remains newest measured landing, diagnostic-only). Population unchanged: J-B "
    "confirmed-diagnostic unqualified (binary staged at /private/tmp/jb_imod_control_preflight), "
    "H-Z3 top of codegen ladder, H-C2 statically confirmed 61/61 timed A/B pending, H-D/H-B/H-Y1 open; "
    "J-C blocked behind J-B. NEXT: J-B fully-quiet-host rerun (idle>=9/10, sustained-window protocol), "
    "then H-Z3 quiet-host hand-patch A/B, then H-C2 timed A/B.\n"
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
