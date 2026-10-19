#!/usr/bin/env python3
"""Parse the tick-1716 n31/n24/n32 sweep logs and apply the chain's noise rule
(IQR <= 0.05 and floor share <= 1.2x the cell's IQR-clean minimum floor share).
Writes the full analysis to analyze-1716.txt next to itself; prints it too.
Line-oriented extraction (GAP/SPEEDUP/FLOORSHARE/SHAPE lines), no assumption
about the tab-separator spelling in the logs."""
import re, statistics, os

ev = os.path.dirname(os.path.abspath(__file__))
out_path = os.path.join(ev, "analyze-1716.txt")

def line_of(txt, key):
    for ln in txt.splitlines():
        if key in ln:
            return ln
    raise SystemExit(f"missing line {key!r}")

def num(pat, ln):
    m = re.search(pat, ln)
    if not m:
        raise SystemExit(f"missing {pat!r} in {ln!r}")
    return float(m.group(1))

cells = {}
for cyc in (1, 2, 3):
    for cell in ("n31", "n24", "n32"):
        p = os.path.join(ev, f"run-{cyc}-{cell}.log")
        txt = open(p).read()
        gap = num(r"ns/dispatch=(-?[\d.]+)", line_of(txt, "GAP"))
        iqr = num(r"iqr=([\d.]+)", line_of(txt, "SPEEDUP"))
        fs_line = line_of(txt, "FLOORSHARE")
        fs_b = num(r"floor/baseline=([\d.]+)", fs_line)
        fs_v = num(r"floor/variant=([\d.]+)", fs_line)
        load = num(r"load averages: ([\d.]+)", line_of(txt, "load averages"))
        shape = line_of(txt, "SHAPE").split("SHAPE")[-1].strip()
        verified = "verified=true" in txt
        cells.setdefault(cell, []).append(
            dict(cyc=cyc, gap=gap, iqr=iqr, fs_b=fs_b, fs_v=fs_v, load=load,
                 verified=verified, shape=shape))

lines = []
for cell, runs in cells.items():
    lines.append(f"== {cell}  {runs[0]['shape']}")
    for r in runs:
        lines.append(
            f"  run{r['cyc']}: gap={r['gap']:+.1f} ns/dispatch  speedup_iqr={r['iqr']:.4f}  "
            f"floor/baseline={r['fs_b']:.4f}  floor/variant={r['fs_v']:.4f}  "
            f"load1={r['load']}  verified={r['verified']}")
    iqr_clean = [r for r in runs if r['iqr'] <= 0.05]
    clean_min = min((r['fs_b'] for r in iqr_clean), default=None)
    surv = [r for r in iqr_clean if clean_min is not None and r['fs_b'] <= 1.2 * clean_min]
    lines.append(f"  IQR-clean runs: {[r['cyc'] for r in iqr_clean]}  "
                 f"clean_min_floor/baseline={clean_min and round(clean_min, 4)}")
    lines.append(f"  surviving runs: {[r['cyc'] for r in surv]}")
    if surv:
        est = statistics.mean(r['gap'] for r in surv)
        lines.append(f"  clean-run est (mean of survivors): {est:+.1f} ns/dispatch")
    gaps = [r['gap'] for r in runs]
    lines.append(f"  mean(3)={statistics.mean(gaps):+.1f}  "
                 f"all-signs={'/'.join('+' if g > 0 else '-' for g in gaps)}  "
                 f"spread={max(gaps) - min(gaps):.1f}")

open(out_path, "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
print("WROTE", out_path)
