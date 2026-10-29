#!/usr/bin/env python3
"""Strict-bin reachability census over the committed run-log corpus (JUN-58).

ONE DESIGN SLICE's measurement basis (2026-10-24): the pair-level
analyzer's strict bins (the manual instrument's hand buckets,
analyze-oporder.py: slow > 80k, middle 40k..80k, fast <= 40k -- ABSOLUTE,
unchanged) at W = 1024. The question: is the strict fast bin (pair
baseline <= 40,000 ns) reachable at this W at all? This script reads
EVERY committed run-log.txt under docs/evidence/ (read-only; nothing in
the corpus is rewritten) and reports, per log and per (n, W) cell, the
pair-baseline floor and the strict-bin pair counts. NO hardware
measurement runs here -- every number is parsed from committed logs.

Usage: python3 strict-bin-reachability-20261024.py <docs/evidence-root>
"""
import re
import sys
from pathlib import Path

BUCKETS = (("fast", 0.0, 40000.0), ("middle", 40000.0, 80000.0),
           ("slow", 80000.0, float("inf")))

SAMPLE_RE = re.compile(r"sample op=(\w+) pair=(\d+) order=(\S) arm=(\w+) "
                       r"gpu_ns=([\d.]+)")


def parse_log(path):
    pairs = {}  # (run, op, pair) -> {arm: gpu_ns}
    n = workgroup = None
    run = 0
    for line in path.read_text().splitlines():
        if line.startswith("===== fresh-process run "):
            m = re.search(r"run (\d+)", line)
            run = int(m.group(1)) if m else run
        elif line.startswith("n="):
            m = re.match(r"n=(\d+)", line)
            if m:
                n = int(m.group(1))
        elif line.startswith("workgroup="):
            m = re.match(r"workgroup=(\d+)", line)
            if m:
                workgroup = int(m.group(1))
        else:
            m = SAMPLE_RE.match(line)
            if m:
                op, p, _o, arm, gpu = m.groups()
                pairs.setdefault((run, op, int(p)), {})[arm] = float(gpu)
    complete = {k: v for k, v in pairs.items() if len(v) == 2}
    incomplete = {k: v for k, v in pairs.items() if len(v) != 2}
    return n, workgroup, complete, incomplete


def bucket_of(b):
    for name, lo, hi in BUCKETS:
        if lo < b <= hi:
            return name
    return "none"  # b <= 0: impossible for a real gpu_ns; named if seen


def main():
    root = Path(sys.argv[1])
    rows = []
    for path in sorted(root.rglob("run-log.txt")):
        n, wg, complete, incomplete = parse_log(path)
        bases = [arms["baseline"] for arms in complete.values()]
        counts = {name: 0 for name, _lo, _hi in BUCKETS}
        for b in bases:
            counts[bucket_of(b)] += 1
        rows.append({
            "log": str(path.relative_to(root)),
            "n": n, "w": wg,
            "complete": len(complete), "incomplete": len(incomplete),
            "floor": min(bases) if bases else None,
            "counts": counts,
        })

    print("strict-bin reachability census over the committed run-log corpus")
    print("(pair-level analyzer's strict bins, the manual instrument's")
    print("absolute hand buckets, analyze-oporder.py, unchanged:")
    print("fast 0 < b <= 40000, middle 40000 < b <= 80000, slow b > 80000;")
    print("b = the pair's baseline gpu_ns. NO hardware measurement ran --")
    print("every number is parsed from committed run-log.txt files,")
    print("read-only.)")
    print()
    print("PER LOG")
    hdr = ("log", "n", "W", "complete pairs", "incomplete",
           "floor baseline ns", "fast", "middle", "slow")
    print("| " + " | ".join(hdr) + " |")
    print("|" + "---|" * len(hdr))
    for r in rows:
        c = r["counts"]
        print(f"| {r['log']} | {r['n']} | {r['w']} | {r['complete']} | "
              f"{r['incomplete']} | "
              f"{r['floor']:.0f} | {c['fast']} | {c['middle']} | {c['slow']} |")
    print()

    print("PER (n, W) CELL")
    hdr = ("n", "W", "logs", "complete pairs", "floor baseline ns",
           "fast-bin pairs", "floor minus the 40k boundary (ns)")
    print("| " + " | ".join(hdr) + " |")
    print("|" + "---|" * len(hdr))
    cells = {}
    for r in rows:
        cells.setdefault((r["n"], r["w"]), []).append(r)
    for (n, w), rs in sorted(cells.items(), key=lambda kv: (kv[0][0] or 0,
                                                            kv[0][1] or 0)):
        floor = min(r["floor"] for r in rs if r["floor"] is not None)
        fast = sum(r["counts"]["fast"] for r in rs)
        pairs = sum(r["complete"] for r in rs)
        print(f"| {n} | {w} | {len(rs)} | {pairs} | {floor:.0f} | {fast} | "
              f"{floor - 40000:+.0f} |")
    print()

    print("REACHABILITY VERDICTS (observation-level only; whether the")
    print("hardware can ever produce a pair baseline inside a bin is")
    print("UNMEASURED -- the harness reads no clock)")
    for (n, w), rs in sorted(cells.items(), key=lambda kv: (kv[0][0] or 0,
                                                            kv[0][1] or 0)):
        floor = min(r["floor"] for r in rs if r["floor"] is not None)
        fast = sum(r["counts"]["fast"] for r in rs)
        if fast > 0:
            verdict = f"REACHED ({fast} pairs in the committed corpus)"
        elif floor <= 40000:
            verdict = "EMPTY but INSIDE the observed floor's reach"
        else:
            verdict = (f"UNREACHED -- every committed pair baseline is "
                       f"above the boundary (floor {floor:.0f}, "
                       f"{floor - 40000:+.0f} ns)")
        print(f"  n={n} W={w}: fast bin {verdict}")


if __name__ == "__main__":
    main()
