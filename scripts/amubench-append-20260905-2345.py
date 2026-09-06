#!/usr/bin/env python3
"""amu-bench tick 2026-09-05 23:45 JST: busy refusal, append evidence to H-B row."""
import io, sys

path = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
tick = (
    " | 2026-09-05 23:45 JST bench tick: host busy — load1 5.32 (23:38) -> 7.61 (23:42) "
    "-> 12.30 (23:44) RISING, not decaying; top -l2 CPU 26.5% user / 59.9% sys / 13.6% idle "
    "(~1.4/10 idle CPUs vs quiet gate idle >=9/10), kernel_task 200%, node 181%+57%, "
    "PhysMem 31G used / 236M unused / 16G compressed, active swap in/out — quiet window "
    "NOT sustained, no measurement attempted; NEXT (J-B idle>=9/10 rerun of "
    "jb_imod_control.c, then H-Z3, then H-C2) not run, no numbers recorded"
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
