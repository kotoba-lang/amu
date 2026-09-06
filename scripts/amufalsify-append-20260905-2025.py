#!/usr/bin/env python3
"""amu-falsify busy tick 2026-09-05 20:25 JST: append one evidence line to the
H-B row of docs/codegen-coscientist.md (status text is amu-rank's property —
this only appends to the evidence cell). Idempotent: skips if already present.

Evidence source: pre-run monitor (amu_cowork_state.sh output), the sanctioned
single source for this tick:
  20:25  up 13:08, 15 users, load averages: 10.69 16.38 29.02
Threshold 7.5 -> measurement refused per policy.
"""
import io

PATH = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"

# Unique tail of the most recent tick line (20:11 JST bench tick, H-B row).
MARKER = (
    "load15 48.54, up 12:54, 15 users), no measurement attempted; "
    "NEXT (J-B idle>=9/10 rerun, then H-Z3, then H-C2) not run, no numbers recorded"
)
ADDITION = (
    " | 2026-09-05 20:25 JST falsify tick: host busy (load1 10.69, load5 16.38, "
    "load15 29.02, up 13:08, 15 users, threshold 7.5), no measurement attempted; "
    "NEXT (J-B idle>=9/10 rerun, then H-Z3, then H-C2) not run, no numbers recorded"
)

with io.open(PATH, "r", encoding="utf-8") as f:
    text = f.read()

if "2026-09-05 20:25 JST falsify tick" in text:
    print("SKIP: already present")
    raise SystemExit(0)

idx = text.find(MARKER)
if idx < 0:
    print("ERROR: marker not found; no change written")
    raise SystemExit(1)

end = idx + len(MARKER)
new_text = text[:end] + ADDITION + text[end:]
if len(new_text) != len(text) + len(ADDITION):
    print("ERROR: length sanity check failed; no change written")
    raise SystemExit(1)

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(new_text)
print("OK: appended", len(ADDITION), "chars after marker at offset", end)
