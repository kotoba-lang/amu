#!/usr/bin/env python3
"""amu-falsify tick 2026-09-05 20:02 JST: append host-busy evidence to H-B row."""
import io

P = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
ANCHOR = "NEXT (J-B idle>=9/10 rerun, then H-Z3, then H-C2) not run, no numbers recorded"
APPEND = (
    " | 2026-09-05 20:02 JST falsify tick: host busy (load1 91.55, load5 65.61, "
    "load15 50.28, up 12:45, 15 users), no measurement attempted; "
    "NEXT (J-B idle>=9/10 rerun, then H-Z3, then H-C2) not run, no numbers recorded"
)

with io.open(P, "r", encoding="utf-8") as f:
    text = f.read()

# Anchor to the H-B row's LAST occurrence of the anchor string
# (previous tick's entry at end of H-B evidence, before the blank line + | H-E row).
marker = ANCHOR + "\n\n| H-E | call-crossing"
if marker not in text:
    raise SystemExit("anchor not found: H-B row tail before H-E")
idx = text.index(marker)
new_text = text[:idx] + ANCHOR + APPEND + text[idx + len(ANCHOR):]

with io.open(P, "w", encoding="utf-8") as f:
    f.write(new_text)
print("ok, appended; new size:", len(new_text))
