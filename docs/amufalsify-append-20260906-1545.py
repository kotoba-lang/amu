import io, sys

path = "docs/codegen-coscientist.md"
evidence = (" 2026-09-06 15:45 JST falsify tick: host busy (load1 9.10, load5 7.85, "
            "load15 13.88, up 1 day 8:28, 10 users, threshold 7.5) - timed measurement "
            "refused per quiet-gate rule; no hand-patch, no bench, no perfgate run, no "
            "numbers. H-C2 timed A/B (amu-mut vs clang kernel stream, static 61/61 "
            "confirmed per 03:55 entry, two prior polluted attempts 14:00-14:03 and "
            "~14:43) still requires a sustained quiet window held THROUGH all trials; "
            "NEXT unchanged: H-C2 timed A/B re-run (sustained-window protocol), then "
            "H-Z3 quiet-host hand-patch A/B.")

with io.open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# line index 37 = the H-C2 row (line 38, 1-based)
idx = 37
assert idx < len(lines), "H-C2 row index out of range"
line = lines[idx]
assert line.strip().startswith("| H-C2 |"), "expected H-C2 row, got: " + line[:40]

# append evidence before the trailing newline
lines[idx] = line.rstrip("\n") + evidence + "\n"

with io.open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("appended busy-refusal evidence to H-C2 row (line 38)")