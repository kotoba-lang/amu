#!/usr/bin/env python3
"""Regime-conditioned analysis of the op-order cell (JUN-58, 2026-10-24).

Reads w1024-sum-last/run-log.txt and reports, per operator and per GPU clock
level (bucketed by the pair's baseline gpu_ns), the median within-pair
variant/baseline gpu-ns ratio. The question the cell exists to answer: the
resweep w1024 cell's regime caveat -- the paired ratio's ~1.5% term at the
fast clock level (1.167-1.175 fast against 1.183-1.186 slow at :max/:min,
where :sum ran first and stayed slow) -- was confounded with the operator's
position in the dispatch order. This cell runs :sum LAST (op-order
max,min,sum) so the last block is sampled at whatever regime the session
holds; does the ratio follow the clock level, or the block's position?

Same instrument as docs/evidence/gpu-subgroup-reduce-m1max-oporder-20261023/
analyze-oporder.py (the W = 32 cell), unchanged buckets, so the two cells'
tables read the same.

Usage: python3 analyze-oporder.py <run-log.txt>
"""
import re
import statistics
import sys

BUCKETS = [("slow", 80000, float("inf")),
           ("middle", 40000, 80000),
           ("fast", 0.0, 40000)]


def main():
    path = sys.argv[1]
    pairs = {}  # (run, op, pair) -> {arm: gpu_ns}
    run = 0
    for line in open(path):
        if line.startswith("===== fresh-process run "):
            m = re.search(r"run (\d+)", line)
            run = int(m.group(1)) if m else run
            continue
        m = re.match(r"sample op=(\w+) pair=(\d+) order=(\S) arm=(\w+) "
                     r"gpu_ns=([\d.]+)", line)
        if m:
            op, p, _o, arm, gpu = m.groups()
            pairs.setdefault((run, op, int(p)), {})[arm] = float(gpu)

    print("level buckets by the pair's baseline gpu_ns: "
          "slow > 80k, middle 40k..80k, fast <= 40k")
    print()
    hdr = ("op", "level", "pairs", "baseline ns (min..max)",
           "median pair ratio", "per-pair ratios")
    print("| " + " | ".join(hdr) + " |")
    print("|" + "---|" * len(hdr))
    for op in ("sum", "max", "min"):
        for name, lo, hi in BUCKETS:
            ratios, bases = [], []
            for (r, o, p), arms in sorted(pairs.items()):
                if o != op or len(arms) != 2:
                    continue
                b = arms["baseline"]
                if lo < b <= hi:
                    bases.append(b)
                    ratios.append(arms["variant"] / b)
            if not ratios:
                print(f"| {op} | {name} | 0 | - | - | - |")
                continue
            print(f"| {op} | {name} | {len(ratios)} | "
                  f"{min(bases):.0f}..{max(bases):.0f} | "
                  f"{statistics.median(ratios):.3f} | "
                  f"{', '.join(f'{r:.3f}' for r in ratios)} |")


if __name__ == "__main__":
    main()
