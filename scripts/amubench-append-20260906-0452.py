#!/usr/bin/env python3
"""amu-bench tick 2026-09-06 04:52 JST: busy refusal, append evidence to H-B row."""
import io, sys

path = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
tick = (
    " | 2026-09-06 04:52 JST bench tick: host busy — load1 7.57 / load5 13.88 / load15 24.09 "
    "(DECAYING trend but load1 > 7.5 gate, quiet gate not met); no measurement attempted, "
    "no numbers recorded; NEXT unchanged (J-B idle>=9/10 rerun of jb_imod_control.c, "
    "then H-Z3, then H-C2)"
)

with io.open(path, encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if line.startswith("| H-B |"):
        lines[i] = line.rstrip("\n") + tick + "\n"
        break
else:
    sys.exit("H-B row not found")

with io.open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("appended to line", i + 1)
