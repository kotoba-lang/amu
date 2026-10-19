#!/usr/bin/env python3
"""Parse the tick-1906 grid-E sweep logs (e24/e26/e27/e32 at lanes
2,156,544) and apply the chain's noise rule (IQR <= 0.05 and floor share
<= 1.2x the cell's IQR-clean minimum floor share). Writes the full
analysis to analyze-1906.txt next to itself; prints it too.
Line-oriented extraction (GAP/SPEEDUP/FLOORSHARE/SHAPE lines), no
assumption about the tab-separator spelling in the logs."""
import re, statistics, os

ev = os.path.dirname(os.path.abspath(__file__))
out_path = os.path.join(ev, "analyze-1906.txt")

CELLS = ["e24", "e26", "e27", "e32"]

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
    for cell in CELLS:
        p = os.path.join(ev, f"run-{cyc}-{cell}.log")
        txt = open(p).read()
        gap = num(r"ns/dispatch=(-?[\d.]+)", line_of(txt, "GAP"))
        iqr = num(r"iqr=([\d.]+)", line_of(txt, "SPEEDUP"))
        sp_med = num(r"median=([\d.]+)", line_of(txt, "SPEEDUP"))
        fs_line = line_of(txt, "FLOORSHARE")
        fs_b = num(r"floor/baseline=([\d.]+)", fs_line)
        fs_v = num(r"floor/variant=([\d.]+)", fs_line)
        load = num(r"load averages: ([\d.]+)", line_of(txt, "load averages"))
        shape = line_of(txt, "SHAPE").split("SHAPE")[-1].strip()
        verdict = line_of(txt, "SPEEDUP").split("vs-1.0=")[-1].strip()
        med = num(r"median=([\d.]+)", line_of(txt, "SPEEDUP"))
        smin = num(r"min=([\d.]+)", line_of(txt, "SPEEDUP"))
        smax = num(r"max=([\d.]+)", line_of(txt, "SPEEDUP"))
        verified = "verified=true" in txt
        cells.setdefault(cell, []).append(
            dict(cyc=cyc, gap=gap, sp_med=sp_med, iqr=iqr, fs_b=fs_b, fs_v=fs_v, load=load,
                 verified=verified, shape=shape, verdict=verdict,
                 med=med, smin=smin, smax=smax))

lines = []
for cell in CELLS:
    runs = cells[cell]
    lines.append(f"== {cell}  {runs[0]['shape']}")
    for r in runs:
        lines.append(
            f"  run{r['cyc']}: gap={r['gap']:+.1f} ns/dispatch  speedup median={r['med']:.4f} "
            f"iqr={r['iqr']:.4f} min={r['smin']:.4f} max={r['smax']:.4f}  "
            f"floor/baseline={r['fs_b']:.4f}  floor/variant={r['fs_v']:.4f}  "
            f"load1={r['load']}  verified={r['verified']}  vs-1.0={r['verdict']}")
    iqr_clean = [r for r in runs if r['verified'] and r['iqr'] <= 0.05]
    clean_min = min((r['fs_b'] for r in iqr_clean), default=None)
    surv = [r for r in iqr_clean if clean_min is not None and r['fs_b'] <= 1.2 * clean_min]
    lines.append(f"  IQR-clean runs: {[r['cyc'] for r in iqr_clean]}  "
                 f"clean_min_floor/baseline={clean_min and round(clean_min, 4)}")
    lines.append(f"  surviving runs: {[r['cyc'] for r in surv]}")
    if surv:
        est = statistics.mean(r['gap'] for r in surv)
        lines.append(f"  clean-run est (mean of survivors): {est:+.1f} ns/dispatch")
    gaps = [r['gap'] for r in runs]
    # Signs derive from the PAIRED per-round statistic (paired speedup
    # median: GAP>0 <=> baseline/variant < 1), not from the marginal gap
    # values, whose sign can contradict the paired rounds (review P1).
    paired_signs = '/'.join('+' if r['sp_med'] < 1 else '0' if r['sp_med'] == 1 else '-' for r in runs)
    lines.append(f"  mean(3, marginal)={statistics.mean(gaps):+.1f}  "
                 f"all-signs(paired)={paired_signs}  "
                 f"all-signs(marginal, superseded)={'/'.join('+' if g > 0 else '0' if g == 0 else '-' for g in gaps)}  "
                 f"spread(marginal)={max(gaps) - min(gaps):.1f}")
    resolved = [r['cyc'] for r in runs if r['verdict'] not in ("indistinguishable-at-this-noise",)]
    lines.append(f"  runs whose ratio stream does not straddle 1.0: {resolved}")

open(out_path, "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
print("WROTE", out_path)
