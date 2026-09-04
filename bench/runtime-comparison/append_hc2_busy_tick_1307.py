#!/usr/bin/env python3
"""Append one falsify-tick busy evidence entry to the H-C2 row's evidence
column in docs/codegen-coscientist.md. Evidence-only edit; no status change."""
import io, sys

DOC = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
ENTRY = ("2026-09-04 13:07 JST falsify tick: host busy "
         "(load1 49.79, load5 61.41, load15 63.30, up 11 days, 10 CPUs), "
         "no measurement attempted; NEXT は H-C2 のまま")

with io.open(DOC, "r", encoding="utf-8") as f:
    lines = f.read().split("\n")

hits = [i for i, ln in enumerate(lines) if ln.startswith("| H-C2 |")]
if len(hits) != 1:
    sys.exit("ERROR: expected exactly one H-C2 row, found %d" % len(hits))

idx = hits[0]
line = lines[idx]
if "2026-09-04 13:07 JST falsify tick" in line:
    sys.exit("SKIP: evidence entry already present (idempotent)")
if not line.rstrip().endswith("|"):
    sys.exit("ERROR: H-C2 row does not end with '|' — unexpected format")

new_line = line.rstrip() + " " + ENTRY
lines[idx] = new_line

with io.open(DOC, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("OK: appended evidence to H-C2 row (line %d)" % (idx + 1))
print("TAIL: ..." + new_line[-260:])
