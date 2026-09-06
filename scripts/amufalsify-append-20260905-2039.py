#!/usr/bin/env python3
"""amu-falsify tick 2026-09-05 20:39 JST: append host-busy evidence.

Anchor is the tail of the previous tick's entry (same pattern as the
20260905-2002 script): the previous host-busy line is now the longest
matching tail, so anchor on its ending text.
"""
import io

P = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
PREV_TAIL = (
    "load15 50.28, up 12:45, 15 users), no measurement attempted; "
    "NEXT (J-B idle>=9/10 rerun, then H-Z3, then H-C2) not run, no numbers recorded"
)
APPEND = (
    " | 2026-09-05 20:39 JST falsify tick: host busy (load1 28.26, load5 21.45, "
    "load15 23.21, up 13:22, 15 users), no measurement attempted; "
    "NEXT (J-B idle>=9/10 rerun, then H-Z3, then H-C2) not run, no numbers recorded"
)

with io.open(P, "r", encoding="utf-8") as f:
    text = f.read()

marker = PREV_TAIL + "\n\n| H-E"
if marker not in text:
    marker = PREV_TAIL
if marker not in text:
    raise SystemExit("anchor not found: previous host-busy tail")
idx = text.rindex(marker)
new_text = text[:idx] + marker + APPEND + text[idx + len(marker):]

with io.open(P, "w", encoding="utf-8") as f:
    f.write(new_text)
print("ok, appended; new size:", len(new_text))
